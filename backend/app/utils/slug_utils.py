import re
import unicodedata
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.mongodb.mongodb import mongodb_manager
from app.utils.logger import get_logger

logger = get_logger("slug_service")

class SlugService:
    """Service de génération et gestion des slugs"""
    
    @staticmethod
    def  generate_slug(text: str, separator: str = '-', max_length: int = 200) -> str:
        """
        Génère un slug à partir d'un texte
        
        Args:
            text: Texte à transformer en slug
            separator: Séparateur (par défaut '-')
            max_length: Longueur maximale du slug
            
        Returns:
            Slug normalisé
        """
        try:
            if not text:
                return ""
            
            # Normaliser les caractères unicode (enlever les accents)
            text = unicodedata.normalize('NFKD', str(text))
            text = text.encode('ASCII', 'ignore').decode('ASCII')
            
            # Convertir en minuscules
            text = text.lower()
            
            # Remplacer les caractères non alphanumériques par le séparateur
            text = re.sub(r'[^a-z0-9\s-]', '', text)
            
            # Remplacer les espaces par le séparateur
            text = re.sub(r'[\s-]+', separator, text)
            
            # Supprimer les séparateurs en début et fin
            text = text.strip(separator)
            
            # Tronquer si nécessaire
            if len(text) > max_length:
                text = text[:max_length].rstrip(separator)
            
            return text
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du slug: {e}")
            raise Exception(f"Erreur lors de la génération du slug: {str(e)}")
    
    @staticmethod
    async def generate_unique_slug(
        base_text: str, 
        collection_name: str, 
        existing_slug: Optional[str] = None,
        separator: str = '-',
        max_length: int = 200,
        id_field: str = "_id"
    ) -> str:
        """
        Génère un slug unique pour une collection donnée
        
        Args:
            base_text: Texte de base pour le slug
            collection_name: Nom de la collection MongoDB
            existing_slug: Slug existant (pour les mises à jour)
            separator: Séparateur
            max_length: Longueur maximale
            id_field: Nom du champ ID pour exclure le document actuel
            
        Returns:
            Slug unique
        """
        try:
            collection = mongodb_manager.get_collection(collection_name)
            
            # Générer le slug de base
            base_slug = SlugService.generate_slug(base_text, separator, max_length)
            
            if not base_slug:
                # Si le slug est vide, générer un slug par défaut
                base_slug = "untitled"
            
            # Si c'est une mise à jour et que le slug n'a pas changé, retourner l'existant
            if existing_slug and existing_slug == base_slug:
                return existing_slug
            
            # Vérifier si le slug existe déjà
            query = {"slug": base_slug}
            
            # Si on a un ID (pour mise à jour), exclure le document actuel
            if existing_slug:
                # Dans ce cas, on vérifie si un autre document a déjà ce slug
                existing_doc = await collection.find_one({"slug": existing_slug})
                if existing_doc:
                    query[id_field] = {"$ne": existing_doc[id_field]}
            
            existing = await collection.find_one(query)
            
            if not existing:
                return base_slug
            
            # Si le slug existe déjà, ajouter un suffixe numérique
            counter = 1
            while True:
                new_slug = f"{base_slug}{separator}{counter}"
                
                # Vérifier si ce slug existe
                query = {"slug": new_slug}
                if existing_slug and existing_doc:
                    query[id_field] = {"$ne": existing_doc[id_field]}
                
                existing = await collection.find_one(query)
                
                if not existing:
                    return new_slug
                
                counter += 1
                
                # Sécurité pour éviter une boucle infinie
                if counter > 100:
                    raise Exception("Impossible de générer un slug unique après 100 tentatives")
                    
        except Exception as e:
            logger.error(f"Erreur lors de la génération du slug unique: {e}")
            raise Exception(f"Erreur lors de la génération du slug unique: {str(e)}")
    
    @staticmethod
    async def get_document_by_slug(collection_name: str, slug: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un document par son slug
        
        Args:
            collection_name: Nom de la collection
            slug: Slug à rechercher
            
        Returns:
            Document ou None
        """
        try:
            collection = mongodb_manager.get_collection(collection_name)
            return await collection.find_one({"slug": slug})
            
        except Exception as e:
            logger.error(f"Erreur récupération par slug {slug}: {e}")
            return None
    
    @staticmethod
    async def update_slug(
        collection_name: str, 
        document_id: str, 
        new_slug: str, 
        id_field: str = "_id"
    ) -> bool:
        """
        Met à jour le slug d'un document
        
        Args:
            collection_name: Nom de la collection
            document_id: ID du document
            new_slug: Nouveau slug
            id_field: Nom du champ ID
            
        Returns:
            True si mis à jour, False sinon
        """
        try:
            collection = mongodb_manager.get_collection(collection_name)
            
            # Vérifier si le nouveau slug est déjà utilisé par un autre document
            existing = await collection.find_one({
                "slug": new_slug,
                id_field: {"$ne": ObjectId(document_id) if id_field == "_id" else document_id}
            })
            
            if existing:
                return False
            
            # Mettre à jour le slug
            result = await collection.update_one(
                {id_field: ObjectId(document_id) if id_field == "_id" else document_id},
                {"$set": {"slug": new_slug}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Erreur mise à jour slug {document_id}: {e}")
            return False
    
    @staticmethod
    async def validate_slug(
        collection_name: str, 
        slug: str, 
        exclude_document_id: Optional[str] = None,
        id_field: str = "_id"
    ) -> bool:
        """
        Vérifie si un slug est disponible
        
        Args:
            collection_name: Nom de la collection
            slug: Slug à valider
            exclude_document_id: ID du document à exclure (pour les mises à jour)
            id_field: Nom du champ ID
            
        Returns:
            True si disponible, False sinon
        """
        try:
            collection = mongodb_manager.get_collection(collection_name)
            
            query = {"slug": slug}
            
            if exclude_document_id:
                query[id_field] = {"$ne": ObjectId(exclude_document_id) if id_field == "_id" else exclude_document_id}
            
            existing = await collection.find_one(query)
            
            return existing is None
            
        except Exception as e:
            logger.error(f"Erreur validation slug {slug}: {e}")
            return False
    
    @staticmethod
    async def generate_slug_from_multiple_fields(
        fields: List[str],
        collection_name: str,
        separator: str = '-',
        max_length: int = 200,
        existing_slug: Optional[str] = None,
        id_field: str = "_id"
    ) -> str:
        """
        Génère un slug à partir de plusieurs champs
        
        Args:
            fields: Liste de valeurs de champs
            collection_name: Nom de la collection
            separator: Séparateur
            max_length: Longueur maximale
            existing_slug: Slug existant (pour mise à jour)
            id_field: Nom du champ ID
            
        Returns:
            Slug unique
        """
        try:
            # Concaténer les champs (filtrer les valeurs vides)
            text_parts = [str(field).strip() for field in fields if field]
            text = f" {separator} ".join(text_parts)
            
            # Générer le slug unique
            return await SlugService.generate_unique_slug(
                base_text=text,
                collection_name=collection_name,
                existing_slug=existing_slug,
                separator=separator,
                max_length=max_length,
                id_field=id_field
            )
            
        except Exception as e:
            logger.error(f"Erreur génération slug multiple: {e}")
            raise Exception(f"Erreur génération slug multiple: {str(e)}")

slug_service = SlugService()