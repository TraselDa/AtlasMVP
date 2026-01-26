from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings.config import settings
from app.utils.logger import setup_logging
from app.services.minio.minio_service import minio_service
from app.mongodb.mongodb import mongodb_manager
from app.services.vector.vector_service import vector_service

# Import routers
from app.api.user_routes import router as user_router
from app.api.user_system_routes import router as user_system_router
from app.api.ocr_routes import router as ocr_router
from app.api.ocr_routes import router as ocr_router
import logging




from app.settings.config import settings
from app.utils.logger import setup_logging
from app.services.minio.minio_service import minio_service
logger = logging.getLogger(__name__)

# Import des tâches planifiées pour les forfaits
import asyncio
from pathlib import Path
# Inclure les routes OCR
def create_application() -> FastAPI:
    """Factory pour créer l'application FastAPI"""
    
    # Créer l'instance du service
    #change_stream_service = ChangeStreamService()
    # Configuration de l'application
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="API Backend pour la plateforme Atlas",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )
    
    # Middleware CORS - Configuration pour autoriser toutes les origines
    if "*" in settings.CORS_ORIGINS:
        # Autoriser toutes les origines
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Utiliser la liste spécifique d'origines
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Ajouter le middleware de métriques Prometheus
    
    
    # Inclusion des routers

    app.include_router(ocr_router)
    app.include_router(user_router)
    app.include_router(user_system_router)

    
        # Dictionnaire pour stocker les objets partagés
    app.state.schedulers = {}

    # Événements de démarrage/arrêt
    @app.on_event("startup")
    async def startup_event():
        setup_logging()
        logger.info("🔵 Démarrage des services..."  )
        
        try:
        # Cette ligne va s'assurer que le bucket existe
            minio_service.ensure_bucket_exists()
            logger.info("MinIO service initialisé avec succès")

                        # Initialize MongoDB
            mongodb_manager.get_database()
            logger.info("✅ MongoDB service initialisé avec succès")
            
            # Initialize Vector Service
            vector_service._client  # Trigger initialization
            logger.info("✅ Vector service initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation MinIO: {e}")


        
        

        logger.info("✅ Tous les services démarrés")
        print("🚀 Atlas API démarrée avec succès")
        print(f"🌐 CORS configuré pour autoriser toutes les origines")
    
    @app.on_event("shutdown")
    async def shutdown_event():

        logger.info("🔴 Tous les services arrêtés")
        print("👋 Atlas API arrêtée")
    


    return app

    


# Application principale
app = create_application()