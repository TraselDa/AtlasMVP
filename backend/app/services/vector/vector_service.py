import logging
import os
import asyncio
from typing import List, Dict, Any, Optional, Union
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from chromadb.errors import ChromaError
from concurrent.futures import ThreadPoolExecutor
from app.settings.config import settings
from app.settings.exceptions import VectorException, NotFoundException
from chromadb import Client

logger = logging.getLogger(__name__)

class VectorService:
    _instance = None
    _client = None
    _model = None
    _executor = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = VectorService()
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
        
        # Initialiser le modèle d'embedding
        self._initialize_model()
        
        # Initialiser le thread pool pour les opérations CPU intensives
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def _initialize_client(self):
        try:
            chroma_url = getattr(settings, "CHROMADB_URL", None)

            if chroma_url:
                logger.info(f"Connexion à ChromaDB serveur (v2): {chroma_url}")

                host = chroma_url.replace("http://", "").replace("https://", "").split(":")[0]
                port = int(chroma_url.split(":")[-1])

                self._client = chromadb.HttpClient(
                    host=host,
                    port=port,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )

                # Test réel
                self._client.list_collections()

            else:
                # =========================
                # MODE LOCAL PERSISTANT
                # =========================
                persist_dir = getattr(settings, "CHROMADB_PERSIST_DIR", "./chromadb")
                os.makedirs(persist_dir, exist_ok=True)

                logger.info(f"Utilisation de ChromaDB local persistant: {persist_dir}")

                self._client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )

                self._client.list_collections()

            logger.info("✅ Connexion à ChromaDB établie")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation ChromaDB: {e}")

            logger.warning("⚠️ Fallback vers ChromaDB en mémoire")
            self._client = chromadb.Client(
                Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
    def _initialize_model(self):
        """Initialise le modèle d'embedding"""
        try:
            self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✅ Modèle d'embedding chargé")
        except Exception as e:
            logger.error(f"❌ Erreur chargement modèle embedding: {e}")
            raise VectorException(f"Impossible de charger le modèle d'embedding: {e}")
    
    async def _run_in_thread(self, func, *args, **kwargs):
        """Exécute une fonction bloquante dans un thread séparé"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))
        except Exception as e:
            logger.error(f"Erreur dans le thread: {e}")
            raise
    
    def _get_or_create_collection_sync(self, collection_slug: str):
        """Récupère ou crée une collection (version synchrone pour thread)"""
        try:
            return self._client.get_collection(name=collection_slug)
        except ChromaError:
            # La collection n'existe pas, on la crée
            return self._client.create_collection(
                name=collection_slug,
                metadata={
                    "document_type_slug": collection_slug,
                    "created_at": self._get_current_timestamp()
                }
            )
    
    def _collection_exists_sync(self, collection_slug: str) -> bool:
        """Vérifie si une collection existe (version synchrone)"""
        try:
            self._client.get_collection(collection_slug)
            return True
        except ChromaError:
            return False
    
    def _create_collection_sync(self, collection_slug: str) -> bool:
        """Crée une collection (version synchrone)"""
        try:
            if self._collection_exists_sync(collection_slug):
                logger.warning(f"Collection {collection_slug} existe déjà")
                return True
            
            self._client.create_collection(
                name=collection_slug,
                metadata={
                    "document_type_slug": collection_slug,
                    "created_at": self._get_current_timestamp()
                }
            )
            logger.info(f"✅ Collection vectorielle créée: {collection_slug}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur création collection {collection_slug}: {e}")
            return False
    
    def _delete_collection_sync(self, collection_slug: str) -> bool:
        """Supprime une collection (version synchrone)"""
        try:
            self._client.delete_collection(name=collection_slug)
            logger.info(f"✅ Collection vectorielle supprimée: {collection_slug}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur suppression collection {collection_slug}: {e}")
            return False
    
    def _embed_text_sync(self, text: str) -> List[float]:
        """Génère des embeddings pour un texte (version synchrone)"""
        try:
            if not text or not text.strip():
                return [0.0] * 384
            
            return self._model.encode(text).tolist()
        except Exception as e:
            logger.error(f"❌ Erreur génération embedding: {e}")
            return [0.0] * 384  # Fallback: vecteur nul
    
    def _embed_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """Génère des embeddings pour un batch de textes (version synchrone)"""
        try:
            # Filtrer les textes vides
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                return [[0.0] * 384 for _ in texts]
            
            embeddings = self._model.encode(valid_texts).tolist()
            
            # Reconstruire la liste complète avec des vecteurs nuls pour les textes vides
            result = []
            text_idx = 0
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[text_idx])
                    text_idx += 1
                else:
                    result.append([0.0] * 384)
            
            return result
        except Exception as e:
            logger.error(f"❌ Erreur génération batch embedding: {e}")
            return [[0.0] * 384 for _ in texts]
    
    """def _add_documents_sync(self, collection_slug: str, documents: List[Dict[str, Any]]) -> List[str]:
        try:
            collection = self._get_or_create_collection_sync(collection_slug)
            
            ids = [doc["slug"] for doc in documents]
            contents = [doc.get("content", "") for doc in documents]
            
            # Générer les embeddings
            embeddings = self._embed_batch_sync(contents)
            
            # Préparer les métadonnées
            metadatas = []
            for doc in documents:
                metadata = doc.get("metadata", {}).copy()
                metadata["document_slug"] = doc["slug"]
                metadata["document_type_slug"] = doc["metadata"].get("document_type_slug", collection_slug)
                metadata["added_at"] = self._get_current_timestamp()
                metadatas.append(metadata)
            
            # Ajouter les documents
            collection.add(
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ {len(documents)} documents ajoutés à {collection_slug}")
            return ids
        except Exception as e:
            logger.error(f"❌ Erreur ajout documents à {collection_slug}: {e}")
            raise VectorException(f"Erreur lors de l'ajout des documents: {e}")"""
    def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100
) -> List[str]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap

        return chunks
    
    """def _add_documents_sync(
    self,
    collection_slug: str,
    documents: List[Dict[str, Any]]
) -> List[str]:
        try:
            collection = self._get_or_create_collection_sync(collection_slug)

            all_ids = []
            all_contents = []
            all_metadatas = []

            for doc in documents:
                doc_slug = doc["slug"]
                content = doc.get("content", "")

                chunks = VectorService.chunk_text(content)

                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{doc_slug}::chunk::{idx}"

                    metadata = doc.get("metadata", {}).copy()
                    metadata.update({
                        "document_slug": doc_slug,
                        "document_type_slug": metadata.get(
                            "document_type_slug",
                            collection_slug
                        ),
                        "chunk_index": idx,
                        "added_at": self._get_current_timestamp()
                    })

                    all_ids.append(chunk_id)
                    all_contents.append(chunk)
                    all_metadatas.append(metadata)

            embeddings = self._embed_batch_sync(all_contents)

            collection.add(
                ids=all_ids,
                documents=all_contents,
                metadatas=all_metadatas,
                embeddings=embeddings
            )

            logger.info(
                f"✅ {len(all_ids)} chunks ajoutés à {collection_slug}"
            )

            return all_ids

        except Exception as e:
            logger.error(f"❌ Erreur ajout documents: {e}")
            raise VectorException(str(e))"""
    
    """def _search_sync(
        self,
        collection_slug: str,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            if not self._collection_exists_sync(collection_slug):
                logger.warning(f"Collection {collection_slug} n'existe pas")
                return []
            
            collection = self._client.get_collection(collection_slug)
            query_embedding = self._embed_text_sync(query)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters
            )
            
            # Formater les résultats
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    
                    formatted_results.append({
                        'slug': results['ids'][0][i],
                        'content': doc,
                        'metadata': metadata,
                        'score': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"❌ Erreur recherche dans {collection_slug}: {e}")
            return []"""
    
    """def _search_sync(
        self,
        collection_slug: str,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            if not self._collection_exists_sync(collection_slug):
                logger.warning(f"Collection {collection_slug} n'existe pas")
                return []

            collection = self._client.get_collection(collection_slug)
            query_embedding = self._embed_text_sync(query)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters
            )

            formatted_results = []

            if not results or not results.get("documents") or not results["documents"][0]:
                return []

            for i, doc in enumerate(results["documents"][0]):
                metadata = (
                    results["metadatas"][0][i]
                    if results.get("metadatas") and results["metadatas"][0]
                    else {}
                )

                formatted_results.append({
                    "chunk_id": results["ids"][0][i],
                    "document_slug": metadata.get("document_slug"),
                    "content": doc,
                    "metadata": metadata,
                    "score": (
                        results["distances"][0][i]
                        if results.get("distances") and results["distances"][0]
                        else 0.0
                    )
                })

            return formatted_results

        except Exception as e:
            logger.error(f"❌ Erreur recherche dans {collection_slug}: {e}")
            return []
    """
    
    # ---------------------------------------------------------
    # MODIFICATION 1 : Suppression du re-chunking inutile
    # On fait confiance au DocumentService qui a déjà fait le découpage intelligent
    # ---------------------------------------------------------
    def _add_documents_sync(
        self,
        collection_slug: str,
        documents: List[Dict[str, Any]] # Attend une liste de chunks déjà préparés
    ) -> List[str]:
        try:
            collection = self._get_or_create_collection_sync(collection_slug)

            ids = []
            contents = []
            metadatas = []
            embeddings = []

            # Préparation des batchs
            for doc in documents:
                # On génère un ID unique s'il n'est pas fourni
                # doc["slug"] ici devrait être l'ID unique du chunk (ex: doc_slug_chunk_0)
                ids.append(doc["slug"]) 
                contents.append(doc["content"])
                
                # S'assurer que les metadata sont plates (pas de dict imbriqués) pour Chroma
                meta = doc.get("metadata", {}).copy()
                meta["added_at"] = self._get_current_timestamp()
                metadatas.append(meta)

            # Génération des embeddings en une fois (plus rapide)
            embeddings = self._embed_batch_sync(contents)

            collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
                embeddings=embeddings
            )

            logger.info(f"✅ {len(ids)} chunks ajoutés à {collection_slug}")
            return ids

        except Exception as e:
            logger.error(f"❌ Erreur ajout documents: {e}")
            raise VectorException(str(e))

    # ---------------------------------------------------------
    # MODIFICATION 2 : Recherche optimisée pour le RAG
    # ---------------------------------------------------------
    def _search_sync(
        self,
        collection_slug: str,
        query: str,
        top_k: int = 5, # 5 à 10 chunks suffisent généralement pour le contexte
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            if not self._collection_exists_sync(collection_slug):
                return []

            collection = self._client.get_collection(collection_slug)
            query_embedding = self._embed_text_sync(query)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters # Permet de filtrer par "mois" ou "type" avant la recherche sémantique
            )

            formatted_results = []
            
            # Sécurité si pas de résultats
            if not results or not results.get("ids") or len(results["ids"][0]) == 0:
                return []

            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i], # CRUCIAL pour le LLM
                    "metadata": results["metadatas"][0][i],
                    "score": results["distances"][0][i] if results.get("distances") else 0.0
                })

            return formatted_results

        except Exception as e:
            logger.error(f"❌ Erreur recherche dans {collection_slug}: {e}")
            return []
    
    def _delete_documents_sync(self, collection_slug: str, document_slugs: List[str]) -> bool:
        """Supprime des documents du store vectoriel (version synchrone)"""
        try:
            if not self._collection_exists_sync(collection_slug):
                logger.warning(f"Collection {collection_slug} n'existe pas")
                return True
            
            collection = self._client.get_collection(collection_slug)
            collection.delete(ids=document_slugs)
            
            logger.info(f"✅ {len(document_slugs)} documents supprimés de {collection_slug}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur suppression documents de {collection_slug}: {e}")
            return False
    
    def _get_collection_info_sync(self, collection_slug: str) -> Dict[str, Any]:
        """Récupère les informations d'une collection (version synchrone)"""
        try:
            if not self._collection_exists_sync(collection_slug):
                return {"exists": False, "slug": collection_slug}
            
            collection = self._client.get_collection(collection_slug)
            count = collection.count()
            
            return {
                "exists": True,
                "slug": collection_slug,
                "count": count,
                "metadata": collection.metadata,
                "created_at": collection.metadata.get("created_at") if collection.metadata else None
            }
        except Exception as e:
            logger.error(f"❌ Erreur récupération infos collection {collection_slug}: {e}")
            return {"exists": False, "slug": collection_slug, "error": str(e)}
    
    def _get_current_timestamp(self) -> str:
        """Retourne le timestamp actuel formaté"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    # ========== MÉTHODES ASYNCHRONES PUBLIQUES ==========
    
    async def collection_exists(self, collection_slug: str) -> bool:
        """Vérifie si une collection existe"""
        return await self._run_in_thread(self._collection_exists_sync, collection_slug)
    
    async def create_collection(self, collection_slug: str) -> bool:
        """Crée une nouvelle collection vectorielle"""
        return await self._run_in_thread(self._create_collection_sync, collection_slug)
    
    async def delete_collection(self, collection_slug: str) -> bool:
        """Supprime une collection vectorielle"""
        return await self._run_in_thread(self._delete_collection_sync, collection_slug)
    
    async def embed_text(self, text: str) -> List[float]:
        """Génère des embeddings pour un texte"""
        return await self._run_in_thread(self._embed_text_sync, text)
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Génère des embeddings pour un batch de textes"""
        return await self._run_in_thread(self._embed_batch_sync, texts)
    
    async def add_documents(self, collection_slug: str, documents: List[Dict[str, Any]]) -> List[str]:
        """Ajoute des documents au store vectoriel"""
        return await self._run_in_thread(self._add_documents_sync, collection_slug, documents)
    
    async def search(
        self,
        collection_slug: str,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Recherche des documents similaires"""
        return await self._run_in_thread(self._search_sync, collection_slug, query, top_k, filters)
    
    async def delete_documents(self, collection_slug: str, document_slugs: List[str]) -> bool:
        """Supprime des documents du store vectoriel"""
        return await self._run_in_thread(self._delete_documents_sync, collection_slug, document_slugs)
    
    async def get_collection_info(self, collection_slug: str) -> Dict[str, Any]:
        """Récupère les informations d'une collection"""
        return await self._run_in_thread(self._get_collection_info_sync, collection_slug)
    
    async def update_document(self, collection_slug: str, document_slug: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Met à jour un document dans le store vectoriel"""
        try:
            # Supprimer l'ancien document
            await self.delete_documents(collection_slug, [document_slug])
            
            # Ajouter le nouveau document
            document = {
                "slug": document_slug,
                "content": content,
                "metadata": metadata
            }
            
            await self.add_documents(collection_slug, [document])
            logger.info(f"✅ Document {document_slug} mis à jour dans {collection_slug}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour document {document_slug}: {e}")
            return False
    
    async def batch_operations(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exécute plusieurs opérations vectorielles en batch"""
        results = []
        
        for op in operations:
            try:
                op_type = op.get("type")
                
                if op_type == "add":
                    result = await self.add_documents(
                        op["collection_slug"],
                        op["documents"]
                    )
                    results.append({"type": op_type, "success": True, "result": result})
                
                elif op_type == "delete":
                    result = await self.delete_documents(
                        op["collection_slug"],
                        op["document_slugs"]
                    )
                    results.append({"type": op_type, "success": True, "result": result})
                
                elif op_type == "search":
                    result = await self.search(
                        op["collection_slug"],
                        op["query"],
                        op.get("top_k", 10),
                        op.get("filters")
                    )
                    results.append({"type": op_type, "success": True, "result": result})
                
                else:
                    results.append({
                        "type": op_type,
                        "success": False,
                        "error": f"Type d'opération inconnu: {op_type}"
                    })
                    
            except Exception as e:
                logger.error(f"❌ Erreur opération {op.get('type')}: {e}")
                results.append({
                    "type": op.get("type"),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def cleanup_collection(self, collection_slug: str, max_age_days: int = 30) -> int:
        """Nettoie les documents anciens d'une collection"""
        try:
            if not await self.collection_exists(collection_slug):
                return 0
            
            from datetime import datetime, timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
            
            # Rechercher les documents anciens
            collection = await self._run_in_thread(self._client.get_collection, collection_slug)
            
            # Note: ChromaDB ne supporte pas directement la suppression par date
            # Il faudrait implémenter cette logique différemment
            logger.warning(f"Cleanup par date non implémenté pour {collection_slug}")
            return 0
            
        except Exception as e:
            logger.error(f"❌ Erreur cleanup collection {collection_slug}: {e}")
            return 0

# Singleton instance
vector_service = VectorService.get_instance()