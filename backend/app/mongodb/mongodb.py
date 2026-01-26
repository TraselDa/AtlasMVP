import logging
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.settings.config import settings

logger = logging.getLogger(__name__)

class MongoDBManager:
    _instance = None
    _client = None
    _db = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MongoDBManager()
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._client = AsyncIOMotorClient(settings.MONGODB_URL)
            self._db = self._client[settings.MONGODB_DB_NAME]
            logger.info("MongoDB service initialized")
    
    def get_database(self):
        return self._db
    
    def get_collection(self, collection_name: str):
        return self._db[collection_name]
    
    async def create_collection(self, collection_name: str, validator: Optional[Dict] = None):
        """Create a new collection with optional schema validation"""
        try:
            await self._db.create_collection(collection_name)
            if validator:
                await self._db.command({
                    "collMod": collection_name,
                    "validator": validator,
                    "validationLevel": "strict"
                })
            logger.info(f"Created collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            raise
    
    async def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            await self._db[collection_name].drop()
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {e}")
            raise
    
    async def insert_document(self, collection_name: str, document: Dict[str, Any]):
        """Insert a single document"""
        try:
            result = await self._db[collection_name].insert_one(document)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting document into {collection_name}: {e}")
            raise
    
    async def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]):
        """Insert multiple documents"""
        try:
            result = await self._db[collection_name].insert_many(documents)
            return result.inserted_ids
        except Exception as e:
            logger.error(f"Error inserting documents into {collection_name}: {e}")
            raise
    
    async def find(self, collection_name: str, query: Dict[str, Any], 
                   skip: int = 0, limit: int = 100, 
                   sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """Find documents with pagination"""
        try:
            cursor = self._db[collection_name].find(query).skip(skip).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            
            documents = await cursor.to_list(length=limit)
            return documents
        except Exception as e:
            logger.error(f"Error finding documents in {collection_name}: {e}")
            raise
    
    async def count(self, collection_name: str, query: Dict[str, Any]) -> int:
        """Count documents matching query"""
        try:
            return await self._db[collection_name].count_documents(query)
        except Exception as e:
            logger.error(f"Error counting documents in {collection_name}: {e}")
            raise
    
    async def update_document(self, collection_name: str, query: Dict[str, Any], 
                             update: Dict[str, Any]):
        """Update a document"""
        try:
            result = await self._db[collection_name].update_one(query, {"$set": update})
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating document in {collection_name}: {e}")
            raise
    
    async def delete_document(self, collection_name: str, query: Dict[str, Any]):
        """Delete a document"""
        try:
            result = await self._db[collection_name].delete_one(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting document from {collection_name}: {e}")
            raise

mongodb_manager = MongoDBManager.get_instance()