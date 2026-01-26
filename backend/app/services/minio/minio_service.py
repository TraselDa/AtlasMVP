from minio import Minio
from minio.error import S3Error
from minio.error import S3Error
from app.settings.config import settings
#from minio.commonconfig import VersioningConfig
from minio.versioningconfig import VersioningConfig
import logging
from pathlib import Path
logger = logging.getLogger(__name__)

class MinioService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MinioService()
        return cls._instance
    
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME or "atlas"
        
         # Assurer que le bucket principal existe
        self.ensure_bucket_exists()
        self.enable_versioning()  # Nouveau: activer le versioning
    
    def ensure_bucket_exists(self):
        """Vérifie que le bucket existe, sinon le crée"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' créé avec succès")
            else:
                logger.info(f"Bucket '{self.bucket_name}' existe déjà")
        except S3Error as e:
            logger.error(f"Erreur lors de la vérification/création du bucket: {e}")
            raise


    def enable_versioning(self):
        """Active le versioning sur le bucket"""
        try:
            config = VersioningConfig("Enabled")  # Chaîne "Enabled" au lieu de constante
            self.client.set_bucket_versioning(self.bucket_name, config)
            logger.info(f"Versioning activé sur le bucket '{self.bucket_name}'")
        except S3Error as e:
            logger.error(f"Erreur activation versioning: {e}")
    
    def check_versioning_status(self):
        """Vérifie l'état du versioning"""
        try:
            config = self.client.get_bucket_versioning(self.bucket_name)
            status = config.status if hasattr(config, 'status') else 'Unknown'
            logger.info(f"Statut versioning bucket '{self.bucket_name}': {status}")
            return status == "Enabled"
        except S3Error as e:
            logger.error(f"Erreur vérification versioning: {e}")
            return False 
    
    
    async def upload_file(self, object_name: str, file_data, content_type: str = "application/octet-stream"):
        """Upload un fichier vers MinIO"""
        try:
            # Si file_data est déjà des bytes, le convertir en BytesIO
            if isinstance(file_data, bytes):
                import io
                file_data = io.BytesIO(file_data)
            
            # Obtenir la longueur
            if hasattr(file_data, 'getbuffer'):
                length = len(file_data.getbuffer())
            elif hasattr(file_data, 'tell') and hasattr(file_data, 'seek'):
                current_pos = file_data.tell()
                file_data.seek(0, 2)  # Aller à la fin
                length = file_data.tell()
                file_data.seek(current_pos)  # Retourner à la position initiale
            else:
                length = -1  # Longueur inconnue
            
            # Upload
            result = self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                length,
                content_type=content_type
            )
            return result
        except S3Error as e:
            logger.error(f"Erreur lors de l'upload: {e}")
            raise
    
    async def download_file(self, object_name: str):
        """Télécharge un fichier depuis MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response.data, response.headers
        except S3Error as e:
            logger.error(f"Erreur lors du téléchargement: {e}")
            raise
    
    async def read_file(self, object_name: str) -> bytes:
        """Lit un fichier MinIO et retourne son contenu en mémoire"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Erreur lecture MinIO: {e}")
            raise

    async def get_file_url(self, object_name: str):
        """Génère l'URL d'accès au fichier"""
        if settings.MINIO_PUBLIC_ACCESS:
            return f"{settings.MINIO_PUBLIC_URL}/{self.bucket_name}/{object_name}"
        else:
            return f"/{self.bucket_name}/{object_name}"  # Pour proxy via FastAPI
    
    async def delete_file(self, object_name: str):
        """Supprime un fichier de MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
        except S3Error as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            raise

    async def soft_delete_object(self, object_name: str):
        """Crée un DeleteMarker (soft delete)"""
        try:
            # Dans un bucket avec versioning, cela crée un DeleteMarker
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"DeleteMarker créé pour: {object_name}")
        except S3Error as e:
            logger.error(f"Erreur soft delete {object_name}: {e}")
            raise

    async def restore_object(self, object_name: str):
        
        """Restauration: supprime le DeleteMarker pour rendre l'objet à nouveau visible."""
        try:
            # 1. Lister TOUTES les versions de TOUS les objets (avec préfixe)
            objects = self.client.list_objects(
                self.bucket_name, 
                prefix=object_name,
                include_version=True
            )
            
            delete_marker_version_id = None
            
            # 2. Chercher le delete marker
            for obj in objects:
                if obj.object_name == object_name and obj.is_delete_marker:
                    delete_marker_version_id = obj.version_id
                    break
            
            if not delete_marker_version_id:
                logger.warning(f"Aucun DeleteMarker trouvé pour {object_name}. L'objet n'est peut-être pas supprimé.")
                return False

            # 3. Supprimer le DeleteMarker spécifique
            self.client.remove_object(
                self.bucket_name,
                object_name,
                version_id=delete_marker_version_id
            )
            logger.info(f"DeleteMarker supprimé, objet restauré: {object_name}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la restauration de {object_name}: {e}")
            # Fallback: Si tout échoue, recréer l'objet depuis une sauvegarde locale
            return await self._fallback_restore(object_name)

    
    
    async def hard_delete_object(self, object_name: str):
        """Hard delete: supprime définitivement TOUTES les versions de l'objet."""
        try:
            # Lister toutes les versions de l'objet
            versions = self.client.list_object_versions(
                self.bucket_name, 
                prefix=object_name
            )
            
            # Supprimer chaque version individuellement
            deleted_count = 0
            for version in versions:
                if version.object_name == object_name:
                    self.client.remove_object(
                        self.bucket_name,
                        object_name,
                        version_id=version.version_id
                    )
                    deleted_count += 1
            
            logger.info(f"{deleted_count} versions supprimées pour l'objet: {object_name}")
            return deleted_count > 0
            
        except S3Error as e:
            logger.error(f"Erreur lors du hard delete de {object_name}: {e}")
            raise

    async def object_exists(self, object_name: str, include_deleted: bool = False):
        """Vérifie si un objet existe, avec option d'inclure les objets masqués par un DeleteMarker."""
        try:
            if include_deleted:
                # Lister les versions pour voir si l'objet existe, même avec un DeleteMarker
                versions = list(self.client.list_object_versions(self.bucket_name, prefix=object_name))
                return any(v.object_name == object_name for v in versions)
            else:
                # Vérifie seulement la version courante (n'inclut pas les objets avec DeleteMarker)
                self.client.stat_object(self.bucket_name, object_name)
                return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise    
    
    async def list_objects_with_prefix(self, prefix: str):
        """Liste tous les objets avec un préfixe donné"""
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Erreur lors de la liste des objets avec préfixe {prefix}: {e}")
            raise
    
    async def soft_delete_prefix(self, prefix: str):
        """Soft delete tous les objets avec un préfixe donné"""
        try:
            objects = await self.list_objects_with_prefix(prefix)
            for obj_name in objects:
                await self.soft_delete_object(obj_name)
            logger.info(f"Tous les objets avec préfixe {prefix} soft-deletés")
        except S3Error as e:
            logger.error(f"Erreur soft delete préfixe {prefix}: {e}")
            raise
    
    async def restore_prefix(self, prefix: str):
        """Restaure tous les objets soft-deletés avec un préfixe donné"""
        try:
            # Lister toutes les versions
            objects = self.client.list_object_versions(self.bucket_name, prefix=prefix)
            restored_count = 0
            
            for obj in objects:
                if obj.is_delete_marker and obj.object_name.startswith(prefix):
                    await self.restore_object(obj.object_name)
                    restored_count += 1
            
            logger.info(f"{restored_count} objets restaurés pour le préfixe {prefix}")
            return restored_count > 0
        except S3Error as e:
            logger.error(f"Erreur restauration préfixe {prefix}: {e}")
            raise
    
    async def hard_delete_prefix(self, prefix: str):
        """Supprime définitivement tous les objets avec un préfixe donné"""
        try:
            # Lister toutes les versions
            objects = self.client.list_object_versions(self.bucket_name, prefix=prefix)
            
            for obj in objects:
                if obj.object_name.startswith(prefix):
                    await self.hard_delete_object(obj.object_name)
            
            logger.info(f"Tous les objets avec préfixe {prefix} définitivement supprimés")
        except S3Error as e:
            logger.error(f"Erreur hard delete préfixe {prefix}: {e}")
            raise

    async def delete_prefix(self, prefix: str) -> bool:
        """
        Supprime récursivement tous les objets avec un préfixe donné
        """
        try:
            # Lister tous les objets avec ce préfixe
            objects = self.client.list_objects(
                self.bucket_name, 
                prefix=prefix, 
                recursive=True
            )
            
            deleted_count = 0
            for obj in objects:
                try:
                    # Supprimer l'objet
                    self.client.remove_object(self.bucket_name, obj.object_name)
                    deleted_count += 1
                    logger.info(f"Objet supprimé: {obj.object_name}")
                except Exception as e:
                    logger.error(f"Erreur suppression objet {obj.object_name}: {e}")
            
            logger.info(f"{deleted_count} objets supprimés avec le préfixe {prefix}")
            return deleted_count > 0
            
        except S3Error as e:
            logger.error(f"Erreur lors de la suppression du préfixe {prefix}: {e}")
            raise

# Singleton instance
minio_service = MinioService.get_instance()