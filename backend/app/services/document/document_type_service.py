import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.mongodb.mongodb import mongodb_manager
from app.services.minio.minio_service import minio_service
from app.services.vector.vector_service import vector_service
from app.utils.slug_utils import slug_service
from app.schemas.document_type import (
    DocumentTypeCreateRequest,
    DocumentTypeUpdateRequest,
    DocumentTypeDBSchema,
    DocumentTypeResponse,
    DocumentTypeListResponse,
    DocumentTypeDeleteResponse,
    DocumentTypeStatus
)
from app.settings.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)

class DocumentTypeService:
    COLLECTION_NAME = "document_types"
    
    @staticmethod
    def get_collection():
        return mongodb_manager.get_collection(DocumentTypeService.COLLECTION_NAME)
    
    @staticmethod
    def _format_db_response(document_type_data: Dict[str, Any]) -> DocumentTypeDBSchema:
        if not document_type_data:
            return None
        
        if "_id" in document_type_data:
            del document_type_data["_id"]
            #document_type_data["id"] = str(document_type_data["_id"])

        
        return DocumentTypeDBSchema(**document_type_data)
    
    @staticmethod
    async def _create_minio_structure(document_type_slug: str) -> bool:
        try:
            folders = [
                f"config/{document_type_slug}/init/",
                f"config/{document_type_slug}/normalized_init/",
                f"config/{document_type_slug}/configs/",
                f"data/{document_type_slug}/"
            ]
            
            for folder in folders:
                await minio_service.upload_file(
                    folder,
                    b"",
                    content_type="application/x-directory"
                )
            
            logger.info(f"Structure MinIO créée pour {document_type_slug}")
            return True
        except Exception as e:
            logger.error(f"Erreur création structure MinIO {document_type_slug}: {e}")
            return False
    
    @staticmethod
    async def _move_to_deleted_folder(document_type_slug: str) -> bool:
        try:
            prefixes = [
                f"config/{document_type_slug}/",
                f"data/{document_type_slug}/"
            ]
            
            for prefix in prefixes:
                await minio_service.soft_delete_prefix(prefix)
            
            logger.info(f"Fichiers déplacés vers deleted pour {document_type_slug}")
            return True
        except Exception as e:
            logger.error(f"Erreur déplacement fichiers {document_type_slug}: {e}")
            return False
    
    @staticmethod
    async def _restore_from_deleted_folder(document_type_slug: str) -> bool:
        try:
            prefixes = [
                f"config/{document_type_slug}/",
                f"data/{document_type_slug}/"
            ]
            
            for prefix in prefixes:
                await minio_service.restore_prefix(prefix)
            
            logger.info(f"Fichiers restaurés pour {document_type_slug}")
            return True
        except Exception as e:
            logger.error(f"Erreur restauration fichiers {document_type_slug}: {e}")
            return False
    
    @staticmethod
    async def _permanently_delete_folder(document_type_slug: str) -> bool:
        try:
            prefixes = [
                f"config/{document_type_slug}/",
                f"data/{document_type_slug}/"
            ]
            
            for prefix in prefixes:
                await minio_service.hard_delete_prefix(prefix)
            
            logger.info(f"Fichiers supprimés définitivement pour {document_type_slug}")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression fichiers {document_type_slug}: {e}")
            return False
    
    @staticmethod
    async def create_document_type(request: DocumentTypeCreateRequest) -> DocumentTypeResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            existing = await collection.find_one({"name": request.name})
            if existing:
                raise ValidationException(f"Un type de document avec le nom '{request.name}' existe déjà")
            
            slug = await slug_service.generate_unique_slug(
                base_text=request.name,
                collection_name=DocumentTypeService.COLLECTION_NAME
            )
            
            await DocumentTypeService._create_minio_structure(slug)
            
            vector_service.create_collection(slug)
            
            document_type_db = DocumentTypeDBSchema(
                slug=slug,
                name=request.name,
                description=request.description,
                created_by=request.created_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await collection.insert_one(document_type_db.model_dump(by_alias=True, exclude={"id"}))
            
            created_data = await collection.find_one({"_id": result.inserted_id})
            created_db = DocumentTypeService._format_db_response(created_data)
            
            logger.info(f"Type de document créé: {slug}")
            return DocumentTypeResponse.from_db(created_db)
            
        except Exception as e:
            logger.error(f"Erreur création type document: {e}")
            raise
    
    @staticmethod
    async def get_document_type(slug: str) -> DocumentTypeResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            document_type_data = await collection.find_one({
                "slug": slug,
                "is_active": True,
                "is_marked_for_deletion": False
            })
            
            if not document_type_data:
                raise NotFoundException(f"Type de document '{slug}' non trouvé")
            
            document_type_db = DocumentTypeService._format_db_response(document_type_data)
            return DocumentTypeResponse.from_db(document_type_db)
            
        except Exception as e:
            logger.error(f"Erreur récupération type document {slug}: {e}")
            raise
    
    @staticmethod
    async def get_all_document_types(skip: int = 0, limit: int = 100) -> DocumentTypeListResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            total = await collection.count_documents({
                "is_active": True,
                "is_marked_for_deletion": False
            })
            
            cursor = collection.find({
                "is_active": True,
                "is_marked_for_deletion": False
            }).skip(skip).limit(limit)
            
            items = []
            async for doc_data in cursor:
                doc_db = DocumentTypeService._format_db_response(doc_data)
                items.append(DocumentTypeResponse.from_db(doc_db))
            
            return DocumentTypeListResponse(
                items=items,
                total=total,
                skip=skip,
                limit=limit
            )
            
        except Exception as e:
            logger.error(f"Erreur récupération types documents: {e}")
            raise
    
    @staticmethod
    async def update_document_type(slug: str, request: DocumentTypeUpdateRequest) -> DocumentTypeResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            existing_data = await collection.find_one({
                "slug": slug,
                "is_active": True,
                "is_marked_for_deletion": False
            })
            
            if not existing_data:
                raise NotFoundException(f"Type de document '{slug}' non trouvé")
            if isinstance(request, dict):
                request = DocumentTypeUpdateRequest(**request)
            
            #update_dict = request.model_dump(exclude_unset=True)
            update_dict = request.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"slug": slug},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                logger.warning(f"Aucune modification pour {slug}")
            
            updated_data = await collection.find_one({"slug": slug})
            updated_db = DocumentTypeService._format_db_response(updated_data)
            
            logger.info(f"Type de document mis à jour: {slug}")
            return DocumentTypeResponse.from_db(updated_db)
            
        except Exception as e:
            logger.error(f"Erreur mise à jour type document {slug}: {e}")
            raise
    
    @staticmethod
    async def soft_delete_document_type(slug: str) -> DocumentTypeDeleteResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            existing = await collection.find_one({
                "slug": slug,
                "is_active": True,
                "is_marked_for_deletion": False
            })
            
            if not existing:
                raise NotFoundException(f"Type de document '{slug}' non trouvé")
            
            deletion_date = datetime.utcnow()
            scheduled_deletion_date = deletion_date + timedelta(days=30)
            
            result = await collection.update_one(
                {"slug": slug},
                {"$set": {
                    "is_marked_for_deletion": True,
                    "deletion_date": deletion_date,
                    "scheduled_deletion_date": scheduled_deletion_date,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count == 0:
                return DocumentTypeDeleteResponse(
                    status="error",
                    message=f"Impossible de marquer le type de document {slug} pour suppression"
                )
            
            await DocumentTypeService._move_to_deleted_folder(slug)
            
            logger.info(f"Type de document marqué pour suppression: {slug}")
            return DocumentTypeDeleteResponse(
                status="success",
                message=f"Type de document '{slug}' marqué pour suppression. Suppression définitive le {scheduled_deletion_date.isoformat()}",
                deleted_slug=slug
            )
            
        except Exception as e:
            logger.error(f"Erreur suppression type document {slug}: {e}")
            raise
    
    @staticmethod
    async def restore_document_type(slug: str) -> DocumentTypeDeleteResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            existing = await collection.find_one({
                "slug": slug,
                "is_marked_for_deletion": True
            })
            
            if not existing:
                raise NotFoundException(f"Type de document '{slug}' non trouvé ou non marqué pour suppression")
            
            result = await collection.update_one(
                {"slug": slug},
                {"$set": {
                    "is_marked_for_deletion": False,
                    "deletion_date": None,
                    "scheduled_deletion_date": None,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count == 0:
                return DocumentTypeDeleteResponse(
                    status="error",
                    message=f"Impossible de restaurer le type de document {slug}"
                )
            
            await DocumentTypeService._restore_from_deleted_folder(slug)
            
            logger.info(f"Type de document restauré: {slug}")
            return DocumentTypeDeleteResponse(
                status="success",
                message=f"Type de document '{slug}' restauré avec succès",
                deleted_slug=slug
            )
            
        except Exception as e:
            logger.error(f"Erreur restauration type document {slug}: {e}")
            raise
    
    @staticmethod
    async def hard_delete_document_type(slug: str) -> DocumentTypeDeleteResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            existing = await collection.find_one({
                "slug": slug,
                #"is_marked_for_deletion": True
            })
            
            if not existing:
                raise NotFoundException(f"Type de document '{slug}' doit être marqué pour suppression avant suppression définitive")
            
            result = await collection.delete_one({"slug": slug})
            
            if result.deleted_count == 0:
                return DocumentTypeDeleteResponse(
                    status="error",
                    message=f"Impossible de supprimer le type de document {slug}"
                )
            
            data_collection_name = f"{slug}_data"
            await mongodb_manager.delete_collection(data_collection_name)
            
            vector_service.delete_collection(slug)
            
            await DocumentTypeService._permanently_delete_folder(slug)
            
            logger.info(f"Type de document supprimé définitivement: {slug}")
            return DocumentTypeDeleteResponse(
                status="success",
                message=f"Type de document '{slug}' supprimé définitivement",
                deleted_slug=slug
            )
            
        except Exception as e:
            logger.error(f"Erreur suppression définitive type document {slug}: {e}")
            raise
    
    @staticmethod
    async def get_document_type_stats(slug: str) -> Dict[str, Any]:
        try:
            collection = DocumentTypeService.get_collection()
            
            doc_type = await collection.find_one({"slug": slug})
            if not doc_type:
                raise NotFoundException(f"Type de document '{slug}' non trouvé")
            
            data_collection = mongodb_manager.get_collection(f"{slug}_data")
            
            total_docs = await data_collection.count_documents({})
            active_docs = await data_collection.count_documents({"is_active": True})
            
            by_source_type = {}
            if total_docs > 0:
                pipeline = [
                    {"$group": {"_id": "$source_type", "count": {"$sum": 1}}}
                ]
                async for result in data_collection.aggregate(pipeline):
                    by_source_type[result["_id"]] = result["count"]
            
            return {
                "total_documents": total_docs,
                "active_documents": active_docs,
                "by_source_type": by_source_type,
                "config_paths": doc_type.get("config_paths", {}),
                "status": doc_type.get("status", "configuring"),
                "last_updated": doc_type.get("updated_at", doc_type.get("created_at"))
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération statistiques type document {slug}: {e}")
            raise
    
    @staticmethod
    async def cleanup_expired_document_types() -> int:
        try:
            collection = DocumentTypeService.get_collection()
            
            expired = await collection.find({
                "is_marked_for_deletion": True,
                "scheduled_deletion_date": {"$lte": datetime.utcnow()}
            }).to_list(length=None)
            
            deleted_count = 0
            for doc_type in expired:
                try:
                    await DocumentTypeService.hard_delete_document_type(doc_type["slug"])
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Erreur suppression type document {doc_type['slug']}: {e}")
                    continue
            
            logger.info(f"{deleted_count} types de documents supprimés définitivement")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Erreur nettoyage types documents: {e}")
            return 0
    
    @staticmethod
    async def search_document_types(query: str, skip: int = 0, limit: int = 20) -> DocumentTypeListResponse:
        try:
            collection = DocumentTypeService.get_collection()
            
            search_filter = {
                "is_active": True,
                "is_marked_for_deletion": False,
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}},
                    {"slug": {"$regex": query, "$options": "i"}}
                ]
            }
            
            total = await collection.count_documents(search_filter)
            
            cursor = collection.find(search_filter).skip(skip).limit(limit)
            
            items = []
            async for doc_data in cursor:
                doc_db = DocumentTypeService._format_db_response(doc_data)
                items.append(DocumentTypeResponse.from_db(doc_db))
            
            return DocumentTypeListResponse(
                items=items,
                total=total,
                skip=skip,
                limit=limit
            )
            
        except Exception as e:
            logger.error(f"Erreur recherche types documents: {e}")
            raise