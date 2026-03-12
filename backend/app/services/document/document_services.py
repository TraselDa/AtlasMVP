import logging
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import UploadFile

from app.mongodb.mongodb import mongodb_manager
from app.services.minio.minio_service import minio_service
from app.services.vector.vector_service import vector_service
from app.services.document.document_type_service import DocumentTypeService
from app.services.config.config_service import ConfigService
from app.core_engine.ocr_engine.ocr_adapter import OCRAdapter
from app.core_engine.normalization.document_normalizer import DocumentNormalizer
from app.core_engine.execution.engine import ExecutionEngine
from app.core_engine.execution.config_resolver import ConfigResolver
from app.utils.slug_utils import slug_service
from app.schemas.document import (
    DocumentDBSchema,
    DocumentResponse,
    PaginatedDocumentsResponse,
    VectorSearchResult,
    VectorSearchResponse,
    ProcessResult,
    BatchProcessResponse,
    DocumentDeleteResponse,
    DocumentStatsResponse
)
from app.settings.exceptions import NotFoundException, ValidationException, ProcessingException
from app.settings.config import settings
logger = logging.getLogger(__name__)

class DocumentService:
    _executor = ThreadPoolExecutor(max_workers=10)
    
    @staticmethod
    def _format_db_response(document_data: Dict[str, Any]) -> DocumentDBSchema:
        """Convertit les données MongoDB en DocumentDBSchema"""
        if not document_data:
            return None
        
        # Convertir ObjectId en string pour le champ id si présent
        if "_id" in document_data:
            #document_data["id"] = str(document_data["_id"])
            del document_data["_id"]
        
        return DocumentDBSchema(**document_data)
    
    @staticmethod
    def _determine_source_type(filename: str, file_content: bytes) -> str:
        """Détermine le type de source du document selon la logique exacte de l'OCRAdapter"""
        try:
            # Utiliser OCRAdapter pour déterminer le source_type exact
            ocr_adapter = OCRAdapter(engine="tesseract")
            raw_data = ocr_adapter.extract_raw(file_content, engine="tesseract")
            return raw_data.get("source_type", "unknown")
        except Exception as e:
            logger.error(f"Erreur détermination source_type: {e}")
            
            # Fallback basé sur l'extension
            ext = "." + filename.split('.')[-1].lower() if '.' in filename else ''
            
            if ext in [".png", ".jpg", ".jpeg"]:
                return "image"
            elif ext == ".pdf":
                # Sans analyse du contenu, on ne peut pas savoir si c'est natif ou scanné
                return "pdf_scanned"
            elif ext == ".docx":
                return "docx"
            else:
                return "unknown"
    
    @staticmethod
    async def _build_document_chunks(
    raw_text: str | None,
    normalized_data: Dict[str, Any],
    max_chars: int = 1200,
    overlap: int = 150
) -> List[Dict[str, Any]]:
        """
        Génère des chunks textuels génériques optimisés pour les embeddings LLM.
        - Aucun enrichissement métier
        - Tolérant aux structures OCR hétérogènes
        """
        loop = asyncio.get_event_loop()

        def _extract_text(line: Any) -> str | None:
            """
            Normalise une ligne OCR en texte brut.
            """
            if isinstance(line, str):
                return line

            if isinstance(line, dict):
                return (
                    line.get("text")
                    or line.get("value")
                    or line.get("content")
                )

            return None

        def _safe_raw_lines(text: Any) -> list[str]:
            if isinstance(text, str):
                return text.splitlines()
            return []

        def _build():
            chunks: list[dict] = []
            buffer = ""
            page = 1

            lines = normalized_data.get("lines") or []
            source = "normalized_lines" if lines else "raw_text"
            iterable = lines if lines else _safe_raw_lines(raw_text)

            for raw_line in iterable:
                text = _extract_text(raw_line)
                if not text:
                    continue

                text = text.strip()
                if not text:
                    continue

                # Si on dépasse la taille max → flush
                if len(buffer) + len(text) > max_chars:
                    chunks.append({
                        "content": buffer.strip(),
                        "page": page,
                        "source": source
                    })

                    # overlap propre (par mots, pas par caractères)
                    if overlap:
                        words = buffer.split()
                        buffer = " ".join(words[-overlap // 5:])  # ~5 chars/mot
                    else:
                        buffer = ""

                buffer += text + " "

                # Heuristique pagination légère
                if text.lower().startswith("page"):
                    page += 1

            if buffer.strip():
                chunks.append({
                    "content": buffer.strip(),
                    "page": page,
                    "source": source
                })

            return chunks

        return await loop.run_in_executor(None, _build)
    
    @staticmethod
    async def _build_vector_documents(
    *,
    doc_slug: str,
    document_type_slug: str,
    filename: str,
    minio_path: str,
    batch_id: str,
    chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Construit les documents vectoriels à partir des chunks.
        Le contenu est STRICTEMENT le texte OCR.
        """
        vector_docs = []
        
        for idx, chunk in enumerate(chunks):
            vector_docs.append({
                "slug": f"{doc_slug}_chunk_{idx}",
                "content": chunk["content"],
                "metadata": {
                    "document_slug": doc_slug,
                    "document_type_slug": document_type_slug,
                    "document_name": filename,
                    "page": chunk.get("page"),
                    "chunk_index": idx,
                    "source": chunk.get("source"),
                    "batch_id": batch_id,
                    "minio_path": minio_path
                }
            })

        return vector_docs
    
    @staticmethod
    async def _prepare_vector_content(extracted_data: Dict[str, Any]) -> str:
        """Prépare le contenu pour la vectorisation de manière asynchrone"""
        try:
            loop = asyncio.get_event_loop()
            
            def prepare_content():
                content_parts = []
                
                for key, value in extracted_data.items():
                    if isinstance(value, str) and value.strip():
                        content_parts.append(f"{key}: {value}")
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, str) and sub_value.strip():
                                content_parts.append(f"{sub_key}: {sub_value}")
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                content_parts.append(f"{key}: {item}")
                            elif isinstance(item, dict):
                                for sub_key, sub_item in item.items():
                                    if isinstance(sub_item, str) and sub_item.strip():
                                        content_parts.append(f"{sub_key}: {sub_item}")
                
                return " ".join(content_parts)
            
            return await loop.run_in_executor(DocumentService._executor, prepare_content)
            
        except Exception as e:
            logger.error(f"Erreur préparation contenu vectoriel: {e}")
            return ""
    
    @staticmethod
    async def _ensure_collection_exists(document_type_slug: str, fields_schema: Optional[Dict] = None):
        """S'assure que la collection MongoDB existe"""
        try:
            collection_name = f"{document_type_slug}_data"
            db = mongodb_manager.get_database()
            
            collections = await db.list_collection_names()
            if collection_name not in collections:
                await mongodb_manager.create_collection(collection_name, fields_schema)
                logger.info(f"Collection MongoDB créée: {collection_name}")
        except Exception as e:
            logger.warning(f"Impossible de créer la collection {collection_name}: {e}")
    
    @staticmethod
    async def _process_single_document(
        file_data: Dict[str, Any],
        document_type_slug: str,
        doc_type_response,
        batch_id: str
    ) -> ProcessResult:
        """Traite un seul document de manière asynchrone"""
        try:
            file = file_data["file"]
            file_content = file_data["content"]
            filename = file.filename
            
            logger.info(f"[Batch {batch_id}] Traitement du document: {filename}")
            
            # 1. Upload vers MinIO
            file_ext = filename.split('.')[-1] if '.' in filename else 'bin'
            minio_path = f"data/{document_type_slug}/{uuid.uuid4()}.{file_ext}"
            # Si file_content est déjà des bytes, le convertir en BytesIO
            

            await minio_service.upload_file(
                minio_path,
                file_content,
                content_type=file.content_type
            )
            
            # 2. Déterminer le type de source selon la nouvelle logique
            source_type = DocumentService._determine_source_type(filename, file_content)
            #source_type = 'pdf_native'
            logger.info(f"[Batch {batch_id}] Traitement du document: {filename} - source_type déterminé: {source_type}") 
            # 3. Récupérer la configuration depuis MinIO
            config_data = await ConfigService.get_config_by_type(document_type_slug, source_type)
            
            # 4. Traitement OCR et extraction (exécuté dans un thread)
            
            """def process_ocr():
                # Créer OCRAdapter avec la configuration
                ocr_adapter = OCRAdapter(engine="tesseract", config_data=config_data)
                normalizer = DocumentNormalizer()
                
                # Utiliser extract_raw pour obtenir le raw_text
                logger.info(f"[Batch {batch_id}] Traitement du document: {filename} - raw extraction") 
                raw_data = ocr_adapter.extract_raw(file_content, engine="tesseract")
                normalized_data = normalizer.normalize(raw_data)
                
                #resolver = ConfigResolver({source_type: config_data})
                #mapping_config = resolver.resolve(normalized_data)
                engine = ExecutionEngine(mapping_config=config_data)
                extracted_data = engine.execute(normalized_data)
                
                return extracted_data"""
            def process_ocr():
                ocr_adapter = OCRAdapter(engine="tesseract", config_data=config_data)
                normalizer = DocumentNormalizer()

                raw_text = ocr_adapter.extract_raw(file_content, engine="tesseract")
                normalized_data = normalizer.normalize(raw_text)

                engine = ExecutionEngine(mapping_config=config_data)
                extracted_data = engine.execute(normalized_data)

                return raw_text, normalized_data, extracted_data
            loop = asyncio.get_event_loop()
            #extracted_data = await loop.run_in_executor(DocumentService._executor, process_ocr)
            raw_text, normalized_data, extracted_data = await loop.run_in_executor(DocumentService._executor, process_ocr)
            logger.info(f" Traitement du document: {filename} - normalized_data déterminé: {normalized_data}") 
            # 5. Générer le slug
            collection_name = f"{document_type_slug}_data"
            doc_slug = await slug_service.generate_slug_from_multiple_fields(
                fields=[filename, document_type_slug, str(uuid.uuid4())[:8]],
                collection_name=collection_name
            )
            
            # 6. Préparer le contenu vectoriel
            #vector_content = await DocumentService._prepare_vector_content(extracted_data)
            # 1. Chunking générique async
            chunks = await DocumentService._build_document_chunks(
                raw_text=raw_text,
                normalized_data=normalized_data
            )

            # 2. Construction des documents vectoriels
            vector_docs = await DocumentService._build_vector_documents(
                doc_slug=doc_slug,
                document_type_slug=document_type_slug,
                filename=filename,
                minio_path=minio_path,
                batch_id=batch_id,
                chunks=chunks
            )

            """# 3. Vectorisation
            vector_ids = await vector_service.add_documents(
                document_type_slug,
                vector_docs
            )"""
            #vector_content = await DocumentService._prepare_vector_content(raw_text)
            # 7. Stocker dans MongoDB
            await DocumentService._ensure_collection_exists(
                document_type_slug,
                getattr(doc_type_response, 'fields_schema', None)
                #doc_type_response.fields_schema
            )
            
            document_db = DocumentDBSchema(
                slug=doc_slug,
                document_type_slug=document_type_slug,
                document_name=filename,
                minio_path=minio_path,
                extracted_data=extracted_data,
                processing_date=datetime.utcnow(),
                source_type=source_type,
                metadata={
                    "source_type": source_type,
                    "size": len(file_content),
                    "content_type": file.content_type,
                    "original_filename": filename,
                    "batch_id": batch_id,
                    #"vector_content_length": len(vector_content),
                    #"vector_content_length": len(vector_content),
                    "file_extension": filename.split('.')[-1].lower() if '.' in filename else '',
                    "config_used": f"{document_type_slug}/{source_type}_config.json"
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await mongodb_manager.insert_document(
                collection_name,
                document_db.model_dump(by_alias=True, exclude={"id"})
            )
            
            # 8. Vectorisation
            """vector_doc = {
                "slug": doc_slug,
                "content": vector_content,
                "metadata": {
                    "document_type_slug": document_type_slug,
                    "document_name": filename,
                    "minio_path": minio_path,
                    "source_type": source_type,
                    "processing_date": document_db.processing_date.isoformat(),
                    "batch_id": batch_id,
                    "config_type": source_type
                }
            }"""
            
            #vector_ids = await vector_service.add_documents(document_type_slug, [vector_doc])
            vector_ids = await vector_service.add_documents(document_type_slug, vector_docs)
            
            # 9. Mettre à jour avec les IDs vectoriels
            await mongodb_manager.update_document(
                collection_name,
                {"slug": doc_slug},
                {"vectorized": True, "vector_ids": vector_ids}
            )
            
            logger.info(f"[Batch {batch_id}] Document traité avec succès: {filename} -> {doc_slug}")
            
            return ProcessResult(
                filename=filename,
                status="success",
                document_slug=doc_slug,
                minio_path=minio_path,
                source_type=source_type
            )
            
        except Exception as e:
            logger.error(f"[Batch {batch_id}] Erreur traitement document {filename}: {e}")
            return ProcessResult(
                filename=filename,
                status="error",
                error=str(e)
            )
    
    @staticmethod
    async def process_document_batch(
        document_type_slug: str,
        files: List[UploadFile]
    ) -> BatchProcessResponse:
        """Traite un batch de documents de manière simultanée"""
        try:
            # Vérifier le type de document
            doc_type_response = await DocumentTypeService.get_document_type(document_type_slug)
            
            # Vérifier que les configurations existent pour les types de source possibles
            source_types = ["pdf_scanned", "pdf_native", "image", "docx"]
            for source_type in source_types:
                try:
                    config_path = f"config/{document_type_slug}/configs/{source_type}_config.json"
                    exists = await minio_service.object_exists(config_path)
                    if exists:
                        logger.info(f"Configuration trouvée pour {source_type}: {config_path}")
                    else:
                        logger.warning(f"Configuration manquante pour {source_type}")
                except Exception as e:
                    logger.warning(f"Erreur vérification config {source_type}: {e}")
            
            # Générer un ID de batch
            batch_id = str(uuid.uuid4())[:8]
            logger.info(f"Début du batch {batch_id} pour {document_type_slug} avec {len(files)} documents")
            
            # Lire tous les fichiers en mémoire
            batch_tasks = []
            for file in files:
                file_content = await file.read()
                batch_tasks.append({
                    "file": file,
                    "content": file_content,
                    "filename": file.filename
                })
            
            # Traiter les documents par groupes de 5 en parallèle
            batch_size = 5
            all_results = []
            successful_files = 0
            failed_files = 0
            
            for i in range(0, len(batch_tasks), batch_size):
                current_batch = batch_tasks[i:i + batch_size]
                
                # Créer les tâches de traitement
                process_tasks = [
                    DocumentService._process_single_document(
                        file_data, document_type_slug, doc_type_response, batch_id
                    )
                    for file_data in current_batch
                ]
                
                # Exécuter le batch en parallèle
                batch_results = await asyncio.gather(*process_tasks, return_exceptions=True)
                
                # Traiter les résultats
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        error_result = ProcessResult(
                            filename=current_batch[j]["filename"],
                            status="error",
                            error=str(result)
                        )
                        all_results.append(error_result)
                        failed_files += 1
                        logger.error(f"[Batch {batch_id}] Exception non gérée: {result}")
                    else:
                        all_results.append(result)
                        if result.status == "success":
                            successful_files += 1
                        else:
                            failed_files += 1
                
                logger.info(f"[Batch {batch_id}] Traité {min(i + batch_size, len(batch_tasks))}/{len(batch_tasks)} documents")
            
            # Statistiques par type de source
            source_type_stats = {}
            for result in all_results:
                if result.status == "success" and hasattr(result, 'source_type'):
                    source_type = result.source_type
                    source_type_stats[source_type] = source_type_stats.get(source_type, 0) + 1
            
            logger.info(f"Batch {batch_id} terminé: {successful_files} succès, {failed_files} échecs")
            logger.info(f"Statistiques par source_type: {source_type_stats}")
            
            return BatchProcessResponse(
                total_files=len(files),
                processed_files=len(files),
                successful_files=successful_files,
                failed_files=failed_files,
                results=all_results,
                batch_id=batch_id,
                source_type_stats=source_type_stats
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement batch: {e}")
            raise ProcessingException(f"Erreur lors du traitement du batch: {e}")
    
    @staticmethod
    async def get_documents(
        document_type_slug: str,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedDocumentsResponse:
        """Récupère les documents avec pagination"""
        try:
            collection_name = f"{document_type_slug}_data"
            
            # Compter le total
            total = await mongodb_manager.count(collection_name, {
                "is_active": True,
                "document_type_slug": document_type_slug
            })
            
            # Récupérer les documents
            documents_data = await mongodb_manager.find(
                collection_name,
                {
                    "is_active": True,
                    "document_type_slug": document_type_slug
                },
                skip=skip,
                limit=limit,
                sort=[("processing_date", -1)]
            )
            logger.info(f"Récupérés {len(documents_data)} documents pour {document_type_slug} (skip={skip}, limit={limit})")
            # Convertir en DocumentResponse
            items = []
            for doc_data in documents_data:
                doc_db = DocumentService._format_db_response(doc_data)
                if doc_db:
                    items.append(DocumentResponse.from_db(doc_db))
            
            # Extraire les champs des données extraites
            fields = []
            if items:
                field_set = set()
                for item in items:
                    if hasattr(item, 'extracted_data') and item.extracted_data:
                        field_set.update(item.extracted_data.keys())
                fields = [{"name": field} for field in field_set]
            
            return PaginatedDocumentsResponse(
                items=items,
                total=total,
                skip=skip,
                limit=limit,
                fields=fields
            )
            
        except Exception as e:
            logger.error(f"Erreur récupération documents: {e}")
            raise
    
    @staticmethod
    async def filter_documents(
        document_type_slug: str,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedDocumentsResponse:
        """Filtre les documents"""
        try:
            collection_name = f"{document_type_slug}_data"
            
            # Construire la requête MongoDB
            query = {
                "is_active": True,
                "document_type_slug": document_type_slug
            }
            
            # Ajouter les filtres sur extracted_data
            for key, value in filters.items():
                if key.startswith("metadata."):
                    # Filtrer sur les métadonnées
                    metadata_key = key.replace("metadata.", "")
                    query[f"metadata.{metadata_key}"] = value
                else:
                    # Filtrer sur extracted_data
                    if isinstance(value, dict):
                        for op, val in value.items():
                            if op == "$eq":
                                query[f"extracted_data.{key}"] = val
                            elif op == "$regex":
                                query[f"extracted_data.{key}"] = {"$regex": val, "$options": "i"}
                            elif op == "$gt":
                                query[f"extracted_data.{key}"] = {"$gt": val}
                            elif op == "$lt":
                                query[f"extracted_data.{key}"] = {"$lt": val}
                            elif op == "$in":
                                query[f"extracted_data.{key}"] = {"$in": val}
                            elif op == "$nin":
                                query[f"extracted_data.{key}"] = {"$nin": val}
                    else:
                        query[f"extracted_data.{key}"] = value
            
            # Compter le total
            total = await mongodb_manager.count(collection_name, query)
            
            # Récupérer les documents
            documents_data = await mongodb_manager.find(
                collection_name,
                query,
                skip=skip,
                limit=limit,
                sort=[("processing_date", -1)]
            )
            
            # Convertir en DocumentResponse
            items = []
            for doc_data in documents_data:
                doc_db = DocumentService._format_db_response(doc_data)
                if doc_db:
                    items.append(DocumentResponse.from_db(doc_db))
            
            # Extraire les champs des données extraites
            fields = []
            if items:
                field_set = set()
                for item in items:
                    if hasattr(item, 'extracted_data') and item.extracted_data:
                        field_set.update(item.extracted_data.keys())
                fields = [{"name": field} for field in field_set]
            
            return PaginatedDocumentsResponse(
                items=items,
                total=total,
                skip=skip,
                limit=limit,
                fields=fields
            )
            
        except Exception as e:
            logger.error(f"Erreur filtrage documents: {e}")
            raise
    
    """@staticmethod
    async def vector_search(
        query: str,
        document_type_slug: str,
        top_k: int = 10,
        include_content: bool = True
    ) -> VectorSearchResponse:
        try:
            # Rechercher dans le store vectoriel
            vector_results = await vector_service.search(
                document_type_slug,
                query,
                top_k
            )
            
            # Récupérer les documents complets depuis MongoDB
            collection_name = f"{document_type_slug}_data"
            search_results = []
            
            for vec_result in vector_results:
                docs_data = await mongodb_manager.find(
                    collection_name,
                    {
                        "slug": vec_result["slug"],
                        "document_type_slug": document_type_slug,
                        "is_active": True
                    },
                    limit=1
                )
                
                if docs_data:
                    doc_db = DocumentService._format_db_response(docs_data[0])
                    doc_response = DocumentResponse.from_db(doc_db)
                    
                    search_results.append(VectorSearchResult(
                        document=doc_response,
                        score=vec_result.get("score", 0.0),
                        vector_content=vec_result.get("content") if include_content else None
                    ))
            
            return VectorSearchResponse(
                results=search_results,
                query=query,
                document_type_slug=document_type_slug,
                total_matches=len(search_results)
            )
            
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle: {e}")
            raise"""
    @staticmethod
    async def vector_search(
        query: str,
        document_type_slug: str,
        top_k: int = 10,
        include_content: bool = True
    ) -> VectorSearchResponse:
        try:
            vector_results = await vector_service.search(
                document_type_slug,
                query,
                top_k
            )

            collection_name = f"{document_type_slug}_data"
            search_results = []
            seen_docs = set()  # éviter doublons (plusieurs chunks d’un même doc)

            for vec_result in vector_results:
                metadata = vec_result.get("metadata", {})
                doc_slug = metadata.get("document_slug")

                if not doc_slug or doc_slug in seen_docs:
                    continue

                seen_docs.add(doc_slug)

                docs_data = await mongodb_manager.find(
                    collection_name,
                    {
                        "slug": doc_slug,
                        "document_type_slug": document_type_slug,
                        "is_active": True
                    },
                    limit=1
                )

                if not docs_data:
                    continue

                doc_db = DocumentService._format_db_response(docs_data[0])
                doc_response = DocumentResponse.from_db(doc_db)

                search_results.append(VectorSearchResult(
                    document=doc_response,
                    score=vec_result.get("score", 0.0),
                    vector_content=vec_result.get("content") if include_content else None
                ))

            return VectorSearchResponse(
                results=search_results,
                query=query,
                document_type_slug=document_type_slug,
                total_matches=len(search_results)
            )

        except Exception as e:
            logger.error(f"Erreur recherche vectorielle: {e}")
            raise
    
    @staticmethod
    async def ask_documents(
        query: str,
        document_type_slug: str,
        filters: Optional[Dict[str, Any]] = None,
        use_llm: bool = True  # <--- NOUVEAU PARAMÈTRE
    ) -> Dict[str, Any]:
        """
        Effectue une recherche hybride.
        - Si use_llm=True : Tente une réponse générée par IA.
        - Si use_llm=False ou Erreur LLM : Retourne les résultats de la recherche sémantique brute.
        """
        
        # 1. Recherche Vectorielle (Socle commun)
        # On récupère les chunks (morceaux de texte) les plus proches de la question
        try:
            vector_results = await vector_service.search(
                document_type_slug,
                query,
                top_k=10, # On prend large pour le contexte LLM
                filters=filters
            )
        except Exception as e:
            logger.error(f"Erreur Vector Service: {e}")
            return {"answer": "Erreur lors de l'interrogation de la base de données.", "sources": []}

        if not vector_results:
            return {
                "answer": "Je n'ai trouvé aucun document correspondant à votre recherche.",
                "sources": [],
                "mode": "no_results"
            }

        # Préparation des sources (noms de fichiers uniques) pour l'affichage final
        sources = list({res["metadata"].get("document_name", "Inconnu") for res in vector_results})

        # --- FONCTION INTERNE POUR LE MODE "SANS LLM" ---
        def format_fallback_response(results):
            """Crée une réponse lisible sans IA à partir des meilleurs chunks"""
            # On prend les 3 meilleurs résultats pour ne pas noyer l'utilisateur
            top_3 = results[:3]
            formatted_text = "Voici les éléments les plus pertinents trouvés dans vos documents :\n\n"
            
            for i, res in enumerate(top_3, 1):
                doc_name = res["metadata"].get("document_name", "Document")
                # On nettoie un peu le contenu (retrait des sauts de ligne excessifs)
                content = res["content"].strip().replace("\n", " ")[:300] + "..."
                formatted_text += f"**{i}. {doc_name}** :\n\"{content}\"\n\n"
            
            return formatted_text

        # 2. Branche "Sans LLM" explicite
        if not use_llm:
            return {
                "answer": format_fallback_response(vector_results),
                "sources": sources,
                "vector_results": vector_results,
                "mode": "search_only"
            }

        # 3. Branche "Avec LLM" (RAG)
        try:
            # Préparation du contexte (texte brut uniquement)
            context_chunks = [res["content"] for res in vector_results]

            payload = {
                "query": query,
                "context_chunks": context_chunks,
                "system_instruction": (
                    "Tu es un assistant documentaire précis. "
                    "Réponds à la question en te basant EXCLUSIVEMENT sur le contexte fourni ci-dessous. "
                    "Cite le nom du document si disponible dans le texte. "
                    "Si l'information n'est pas dans le contexte, dis-le clairement."
                )
            }

            import httpx
            # Timeout court pour la connexion (2s), long pour la génération (60s)
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=2.0)) as client:
                response = await client.post(
                    f"{settings.LLM_API_URL}/chat/rag",
                    json=payload,
                    headers={"X-API-Key": settings.LLM_API_KEY}
                )
                response.raise_for_status()
                llm_analysis = response.json()

            return {
                "answer": llm_analysis["answer"],
                "sources": sources,
                "vector_results": vector_results,
                "mode": "llm_rag"
            }

        except Exception as e:
            # 4. FALLBACK : Si le LLM plante (timeout, api down, etc.), on renvoie le mode recherche
            logger.warning(f"⚠️ Échec appel LLM ({str(e)}), bascule en mode recherche simple.")
            
            return {
                "answer": format_fallback_response(vector_results) + "\n\n*(Note: Analyse IA indisponible, affichage des extraits bruts)*",
                "sources": sources,
                "vector_results": vector_results,
                "mode": "fallback_search",
                "error": str(e)
            }
        
    @staticmethod
    async def get_document_by_slug(
        document_type_slug: str,
        document_slug: str
    ) -> DocumentResponse:
        """Récupère un document par son slug"""
        try:
            collection_name = f"{document_type_slug}_data"
            
            documents_data = await mongodb_manager.find(
                collection_name,
                {
                    "slug": document_slug,
                    "document_type_slug": document_type_slug,
                    "is_active": True
                },
                limit=1
            )
            
            if not documents_data:
                raise NotFoundException(f"Document '{document_slug}' non trouvé")
            
            doc_db = DocumentService._format_db_response(documents_data[0])
            return DocumentResponse.from_db(doc_db)
            
        except Exception as e:
            logger.error(f"Erreur récupération document {document_slug}: {e}")
            raise
    
    @staticmethod
    async def delete_document(
        document_type_slug: str,
        document_slug: str
    ) -> DocumentDeleteResponse:
        """Supprime un document (soft delete)"""
        try:
            # Récupérer le document
            document_response = await DocumentService.get_document_by_slug(
                document_type_slug,
                document_slug
            )
            
            collection_name = f"{document_type_slug}_data"
            
            # Soft delete dans MongoDB
            result = await mongodb_manager.update_document(
                collection_name,
                {"slug": document_slug},
                {
                    "is_active": False,
                    "is_marked_for_deletion": True,
                    "updated_at": datetime.utcnow()
                }
            )
            
            if result == 0:
                return DocumentDeleteResponse(
                    status="error",
                    message=f"Impossible de supprimer le document {document_slug}"
                )
            
            # Soft delete dans MinIO
            await minio_service.soft_delete_object(document_response.minio_path)
            
            # Supprimer du store vectoriel
            if hasattr(document_response, 'vector_ids') and document_response.vector_ids:
                await vector_service.delete_documents(document_type_slug, [document_slug])
            
            logger.info(f"Document supprimé: {document_slug}")
            return DocumentDeleteResponse(
                status="success",
                message=f"Document '{document_slug}' supprimé avec succès",
                deleted_slug=document_slug
            )
            
        except Exception as e:
            logger.error(f"Erreur suppression document {document_slug}: {e}")
            raise
    
    @staticmethod
    async def get_document_stats(document_type_slug: str) -> DocumentStatsResponse:
        """Récupère les statistiques des documents"""
        try:
            collection_name = f"{document_type_slug}_data"
            collection = mongodb_manager.get_collection(collection_name)
            
            # Statistiques de base
            total_docs = await collection.count_documents({})
            active_docs = await collection.count_documents({"is_active": True})
            vectorized_docs = await collection.count_documents({"vectorized": True})
            
            # Par type de source
            pipeline_by_source = [
                {"$group": {"_id": "$source_type", "count": {"$sum": 1}}}
            ]
            
            by_source_type = {}
            async for result in collection.aggregate(pipeline_by_source):
                by_source_type[result["_id"]] = result["count"]
            
            # Par mois (12 derniers mois)
            from datetime import datetime, timedelta
            twelve_months_ago = datetime.utcnow() - timedelta(days=365)
            
            pipeline_by_month = [
                {
                    "$match": {
                        "processing_date": {"$gte": twelve_months_ago}
                    }
                },
                {
                    "$project": {
                        "year_month": {
                            "$dateToString": {
                                "format": "%Y-%m",
                                "date": "$processing_date"
                            }
                        }
                    }
                },
                {"$group": {"_id": "$year_month", "count": {"$sum": 1}}},
                {"$sort": {"_id": -1}},
                {"$limit": 12}
            ]
            
            by_month = {}
            async for result in collection.aggregate(pipeline_by_month):
                by_month[result["_id"]] = result["count"]
            
            # Récupérer un échantillon pour l'analyse des champs
            sample_docs = await collection.find({}).limit(5).to_list(length=5)
            
            field_summary = []
            if sample_docs:
                field_samples = {}
                for doc in sample_docs:
                    extracted_data = doc.get("extracted_data", {})
                    for field, value in extracted_data.items():
                        if field not in field_samples:
                            field_samples[field] = []
                        if len(field_samples[field]) < 3:
                            field_samples[field].append(value)
                
                for field, samples in field_samples.items():
                    field_type = "unknown"
                    if samples:
                        field_type = type(samples[0]).__name__
                    
                    field_summary.append({
                        "field_name": field,
                        "field_type": field_type,
                        "sample_values": samples,
                        "count": len(samples)
                    })
            
            return {
                "total_documents": total_docs,
                "processed_documents": active_docs,
                "vectorized_documents": vectorized_docs,
                "by_source_type": by_source_type,
                "by_month": by_month,
                "field_summary": field_summary
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération statistiques documents: {e}")
            raise
    
    @staticmethod
    async def cleanup_deleted_documents(document_type_slug: str) -> int:
        """Nettoie les documents marqués pour suppression"""
        try:
            collection_name = f"{document_type_slug}_data"
            collection = mongodb_manager.get_collection(collection_name)
            
            # Trouver les documents marqués pour suppression
            deleted_docs = await collection.find({
                "is_marked_for_deletion": True,
                "is_active": False
            }).to_list(length=None)
            
            deleted_count = 0
            
            for doc in deleted_docs:
                try:
                    doc_slug = doc["slug"]
                    
                    # Supprimer de MinIO
                    minio_path = doc.get("minio_path")
                    if minio_path:
                        await minio_service.hard_delete_object(minio_path)
                    
                    # Supprimer du store vectoriel
                    vector_ids = doc.get("vector_ids", [])
                    if vector_ids:
                        await vector_service.delete_documents(document_type_slug, [doc_slug])
                    
                    # Supprimer de MongoDB
                    await collection.delete_one({"slug": doc_slug})
                    
                    deleted_count += 1
                    logger.info(f"Document nettoyé: {doc_slug}")
                    
                except Exception as e:
                    logger.error(f"Erreur nettoyage document {doc.get('slug')}: {e}")
                    continue
            
            logger.info(f"{deleted_count} documents nettoyés pour {document_type_slug}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Erreur nettoyage documents: {e}")
            return 0