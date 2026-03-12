"""Middleware ASGI pur de securite par API Key pour les requetes inter-services.

Verifie que les requetes proviennent du backend via X-API-Key.
Les endpoints publics (healthcheck, docs) sont exclus.
"""

import json
import logging
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.config import settings

logger = logging.getLogger(__name__)

_EXCLUDED_PATHS = frozenset({"/health", "/", "/docs", "/openapi.json"})


class LLMAPIKeyMiddleware:
    """Verifie que les requetes proviennent du backend via X-API-Key (ASGI pur)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/")

        if method == "OPTIONS" or path in _EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        if not settings.LLM_INTERNAL_API_KEY:
            await self.app(scope, receive, send)
            return

        # Extraire X-API-Key des headers ASGI
        api_key = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-api-key":
                api_key = header_value.decode("latin-1")
                break

        if not api_key or api_key != settings.LLM_INTERNAL_API_KEY:
            logger.warning(f"LLM - API Key invalide: {method} {path}")
            body = json.dumps({"detail": "API Key invalide"}).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
