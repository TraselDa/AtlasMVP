"""Configuration centralisee du service LLM Core Taffolio.

Centralise toutes les variables d'environnement du service LLM
en utilisant Pydantic Settings pour la validation et le chargement.

Utilisation:
    >>> from app.core.config import settings
    >>> print(settings.LLM_MODEL_NAME)
"""

from typing import List
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """Configuration du service LLM Core."""

    # LLM Performance
    LLM_MAX_CONCURRENT: int = 1
    LLM_N_THREADS: int = 4
    LLM_CTX: int = 2048
    LLM_TIMEOUT: int = 20

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL_NAME: str = "google/gemma-3n-e4b-it"
    LLM_CONFIG_MODEL_NAME: str = "google/gemini-2.5-flash-lite"

    # API Security (CORS en str brut, split via property)
    LLM_CORS_ORIGINS: str = "https://dev.slim-engine.com"
    LLM_INTERNAL_API_KEY: str = ""

    # OpenTelemetry
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "taffolio-llm-core"
    OTEL_SERVICE_VERSION: str = "1.0.0"
    OTEL_ENVIRONMENT: str = "development"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.LLM_CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = LLMSettings()
