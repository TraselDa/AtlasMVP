import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Configuration de l'application"""

    # Minio Configuration
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str 
    MINIO_SECRET_KEY: str 
    MINIO_SECURE: bool = False  # HTTPS ou HTTP
    MINIO_BUCKET_NAME: str = "atlas"
    MINIO_PUBLIC_URL: Optional[str] = None  # URL publique si configurée
    MINIO_PUBLIC_ACCESS: bool = False

    # Redis Configuration

    # Email Configuration

    
    # Frontend URLs

    # Application
    APP_NAME: str = "ATLAS API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str
    #SECRET_KEY: str
    DEBUG: bool = False

    
    # Database
    MONGODB_URL: str   
    MONGODB_DB_NAME: str
    
    # Chroma DB
    #CHROMA_DB: str
    
        # Vector Database Configuration
    CHROMADB_URL: Optional[str] = None  # Ex: http://localhost:8000
    CHROMADB_PERSIST_DIR: str = "./chromadb"
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_SEARCH_TOP_K: int = 10
    VECTOR_BATCH_SIZE: int = 100
    
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # LLM Configuration
    LLM_API_URL: str 
    LLM_API_KEY: str

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def is_development(self):
        return self.ENVIRONMENT == "development"
    
    @property
    def is_quality(self):
        return self.ENVIRONMENT == "qa"

    @property
    def is_production(self):
        return self.ENVIRONMENT == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instance globale des settings
settings = Settings()