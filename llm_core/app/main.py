"""Point d'entrée principal du service LLM Core.

Ce module initialise et configure l'application FastAPI dédiée aux
fonctionnalités d'Intelligence Artificielle (RAG, réévaluation de CV, 
enrichissement sémantique).

Il met en place:
- Les middlewares de sécurité (CORS strict, vérification d'API Key interne)
- L'intégration d'OpenTelemetry (si activée) pour le tracing distribué
- Le routage vers les endpoints spécifiques de l'IA
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.telemetry import init_telemetry, OTelTraceMiddleware
from app.middleware.api_key import LLMAPIKeyMiddleware

from app.api import rag_router

# Initialize OpenTelemetry before anything else
init_telemetry()

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Factory pour créer l'application FastAPI."""

    app = FastAPI(
        title="Taffolio LLM Core Service",
        version="1.0.0",
    )

    # Middleware CORS - Restreint au backend uniquement
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )

    # Middleware API Key (vérification inter-services Backend -> LLM Core)
    app.add_middleware(LLMAPIKeyMiddleware)

    # OpenTelemetry trace middleware (tracing distribué)
    if settings.OTEL_ENABLED:
        app.add_middleware(OTelTraceMiddleware)

    # Routers
    app.include_router(rag_router)

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "llm-core"}

    return app


app = create_app()
