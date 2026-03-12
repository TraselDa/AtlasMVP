"""Minimal OpenTelemetry setup for LLM Core."""

import time
import logging
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.config import settings

logger = logging.getLogger(__name__)


def init_telemetry():
    """Initialize OpenTelemetry for LLM Core."""
    if not settings.OTEL_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME

    resource = Resource.create({
        SERVICE_NAME: settings.OTEL_SERVICE_NAME,
        "service.version": settings.OTEL_SERVICE_VERSION,
        "deployment.environment": settings.OTEL_ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


_EXCLUDED_PATHS = frozenset({"/health", "/"})


class OTelTraceMiddleware:
    """Lightweight ASGI trace middleware for LLM Core."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        from opentelemetry import trace
        from opentelemetry.propagate import extract as _extract
        self._tracer = trace.get_tracer("taffolio.llm-core.http.server")
        self._extract = _extract

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path in _EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        from opentelemetry.trace import StatusCode, SpanKind

        method = scope.get("method", "GET")
        headers = {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        parent_ctx = self._extract(headers)

        with self._tracer.start_as_current_span(
            f"{method} {path}",
            context=parent_ctx,
            kind=SpanKind.SERVER,
            attributes={
                "http.method": method,
                "http.route": path,
            },
        ) as span:
            start_time = time.time()
            status_code = 500

            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 500)
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
                duration = time.time() - start_time
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("http.response_time_ms", round(duration * 1000, 2))
                if status_code >= 500:
                    span.set_status(StatusCode.ERROR, f"HTTP {status_code}")
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
