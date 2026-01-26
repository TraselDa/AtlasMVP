import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import UploadFile

from app.services.minio.minio_service import minio_service
from app.services.document.document_type_service import DocumentTypeService
from app.core_engine.ocr_engine.ocr_adapter import OCRAdapter
from app.core_engine.normalization.document_normalizer import DocumentNormalizer
from app.mongodb.mongodb import mongodb_manager
from app.utils.slug_utils import slug_service

logger = logging.getLogger(__name__)

class ConfigService:
    
    @staticmethod
    async def upload_initial_document(
        document_type_slug: str,
        file: UploadFile
    ) -> Dict[str, Any]:
        """Upload un document initial pour configuration"""
        try:
            # Vérifier que le type de document existe
            await DocumentTypeService.get_document_type(document_type_slug)
            
            # Upload vers MinIO
            file_content = await file.read()
            minio_path = f"config/{document_type_slug}/init/{file.filename}"
            
            await minio_service.upload_file(
                minio_path,
                file_content,
                content_type=file.content_type
            )
            
            return {
                "filename": file.filename,
                "minio_path": minio_path,
                "document_type_slug": document_type_slug,
                "size": len(file_content),
                "upload_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur upload document initial: {e}")
            raise
    
    @staticmethod
    async def get_initial_documents(document_type_slug: str) -> List[Dict[str, Any]]:
        """Récupère les documents initiaux"""
        try:
            prefix = f"config/{document_type_slug}/init/"
            files = await minio_service.list_objects_with_prefix(prefix)
            
            documents = []
            for file_path in files:
                # Pour simplifier, on ne récupère pas la taille
                documents.append({
                    "name": file_path.split('/')[-1],
                    "minio_path": file_path,
                    "content_type": "application/octet-stream"
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur récupération documents initiaux: {e}")
            raise
    
    @staticmethod
    async def build_initial_config(document_type_slug: str) -> Dict[str, Any]:
        """Construit la configuration initiale"""
        try:
            # Récupérer les documents initiaux
            documents = await ConfigService.get_initial_documents(document_type_slug)
            
            if not documents:
                raise ValueError(f"Aucun document initial trouvé pour {document_type_slug}")
            
            ocr_adapter = OCRAdapter(engine="tesseract")
            normalizer = DocumentNormalizer()
            
            results = []
            
            for doc in documents:
                try:
                    # Télécharger le document
                    file_content = await minio_service.read_file(doc["minio_path"])
                    
                    # Traitement OCR
                    raw_data = ocr_adapter.extract_raw(file_content, engine="tesseract")
                    normalized_data = normalizer.normalize(raw_data)
                    
                    # Sauvegarder les données normalisées
                    normalized_path = f"config/{document_type_slug}/normalized_init/{doc['name']}_normalized.json"
                    
                    await minio_service.upload_file(
                        normalized_path,
                        json.dumps(normalized_data, ensure_ascii=False, indent=2).encode('utf-8'),
                        content_type="application/json"
                    )
                    
                    results.append({
                        "file": doc["name"],
                        "normalized_path": normalized_path,
                        "lines": len(normalized_data.get("lines", [])),
                        "status": "success"
                    })
                    
                except Exception as e:
                    logger.error(f"Erreur traitement {doc['name']}: {e}")
                    results.append({
                        "file": doc["name"],
                        "status": "error",
                        "error": str(e)
                    })
            
            return {
                "status": "ok",
                "document_type_slug": document_type_slug,
                "files_processed": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Erreur construction config initiale: {e}")
            raise
    
    @staticmethod
    async def get_normalized_init(document_type_slug: str) -> List[Dict[str, Any]]:
        """Récupère les documents normalisés initiaux"""
        try:
            prefix = f"config/{document_type_slug}/normalized_init/"
            files = await minio_service.list_objects_with_prefix(prefix)
            
            normalized_files = []
            for file_path in files:
                try:
                    file_content = await minio_service.read_file(file_path)
                    normalized_data = json.loads(file_content.decode('utf-8'))
                    
                    normalized_files.append({
                        "file_path": file_path,
                        "file_name": file_path.split('/')[-1],
                        "line_count": len(normalized_data.get("lines", [])),
                        "normalized_lines": normalized_data.get("lines", [])[:5]
                    })
                except Exception as e:
                    logger.warning(f"Impossible de lire {file_path}: {e}")
            
            return normalized_files
            
        except Exception as e:
            logger.error(f"Erreur récupération fichiers normalisés: {e}")
            raise
    
    @staticmethod
    async def upload_config(
        document_type_slug: str,
        config_type: str,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upload une configuration"""
        try:
            # Vérifier que le type de document existe
            doc_type = await DocumentTypeService.get_document_type(document_type_slug)
            
            # Upload la config vers MinIO
            config_path = f"config/{document_type_slug}/configs/{config_type}_config.json"
            config_json = json.dumps(config_data, ensure_ascii=False, indent=2)
            
            await minio_service.upload_file(
                config_path,
                config_json.encode('utf-8'),
                content_type="application/json"
            )
            
            # Mettre à jour le type de document
            #config_paths = doc_type.get("config_paths", {})
            config_paths = getattr(doc_type, 'config_paths', {})
            config_paths[config_type] = config_path
            
            await DocumentTypeService.update_document_type(
                document_type_slug,
                {"config_paths": config_paths, "updated_at": datetime.utcnow()}
            )
            
            # Créer le schéma de champs si c'est la première config
            #if not doc_type.get("fields_schema"):
            if not getattr(doc_type, 'fields_schema', None):    
                fields_schema = ConfigService._create_fields_schema(config_data)
                if fields_schema:
                    await DocumentTypeService.update_document_type(
                        document_type_slug,
                        {"fields_schema": fields_schema}
                    )
                    
                    # Créer la collection MongoDB
                    
                    collection_name = f"{document_type_slug}_data"
                    try:
                        await mongodb_manager.create_collection(collection_name, fields_schema)
                    except Exception as e:
                        logger.warning(f"Impossible de créer la collection: {e}")
            
            return {
                "status": "success",
                "document_type_slug": document_type_slug,
                "config_type": config_type,
                "config_path": config_path
            }
            
        except Exception as e:
            logger.error(f"Erreur upload config: {e}")
            raise
    
    @staticmethod
    def _create_fields_schema(config_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crée un schéma MongoDB à partir de la config"""
        try:
            fields = {}
            
            if "mapping" in config_data:
                for field_name, field_config in config_data["mapping"].items():
                    if isinstance(field_config, dict):
                        fields[f"extracted_data.{field_name}"] = {
                            "bsonType": "string"
                        }
            
            if fields:
                return {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "properties": fields
                    }
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Impossible de créer le schéma: {e}")
            return None
    
    @staticmethod
    async def get_config_by_type(
        document_type_slug: str,
        config_type: str
    ) -> Dict[str, Any]:
        """Récupère une configuration par type"""
        try:
            # Récupérer le type de document pour obtenir le chemin
            doc_type = await DocumentTypeService.get_document_type(document_type_slug)
            
            #config_path = doc_type.get("config_paths", {}).get(config_type)
            config_path = (getattr(doc_type, 'config_paths', {}) or {}).get(config_type)
            if not config_path:
                # Essayer de trouver une config par défaut
                for source_type in ["pdf_scanned", "pdf_native", "image", "docx"]:
                    #config_path = doc_type.get("config_paths", {}).get(source_type)
                    config_path = (getattr(doc_type, 'config_paths', {}) or {}).get(source_type)
                    if config_path:
                        break
            
            if not config_path:
                raise ValueError(f"Aucune config trouvée pour {config_type} dans {document_type_slug}")
            
            # Télécharger la config
            config_content = await minio_service.read_file(config_path)
            config_data = json.loads(config_content.decode('utf-8'))
            
            return config_data
            
        except Exception as e:
            logger.error(f"Erreur récupération config: {e}")
            raise
    
    @staticmethod
    async def delete_config(
        document_type_slug: str,
        config_type: str
    ) -> bool:
        """Supprime une configuration"""
        try:
            # Récupérer le type de document
            doc_type = await DocumentTypeService.get_document_type(document_type_slug)
            
            config_path = (getattr(doc_type, 'config_paths', {}) or {}).get(config_type)
            if not config_path:
                raise ValueError(f"Config {config_type} non trouvée pour {document_type_slug}")
            
            # Supprimer de MinIO
            await minio_service.delete_file(config_path)
            
            # Mettre à jour le type de document
            #config_paths = doc_type.get("config_paths", {})
            config_paths = getattr(doc_type, 'config_paths', {})
            if config_type in config_paths:
                del config_paths[config_type]
                
                await DocumentTypeService.update_document_type(
                    document_type_slug,
                    {"config_paths": config_paths, "updated_at": datetime.utcnow()}
                )
            
            logger.info(f"Config supprimée: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression config: {e}")
            raise