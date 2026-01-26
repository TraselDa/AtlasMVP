import logging
import sys
from app.settings.config import settings


def setup_logging():
    """Configure le système de logging"""
    
    logging_level = logging.DEBUG if settings.is_development else logging.INFO
    
    # Configuration de base
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Configuration spécifique pour différents loggers
    loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "sqlalchemy.engine",
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging_level)
    
    # Réduit le verbosité des logs SQLAlchemy en production
    if not settings.is_development:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # Logger de démarrage
    logging.info("✅ Logging configuré avec succès")


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger configuré"""
    return logging.getLogger(name)


# Loggers pré-configurés
app_logger = get_logger("atlas.app")
auth_logger = get_logger("atlas.auth")
db_logger = get_logger("atlas.database")
api_logger = get_logger("atlas.api")