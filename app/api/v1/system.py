"""System-level endpoints: health, readiness, and root metadata."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.adapters.metrics import provider_metrics
from app.core.metrics import api_metrics
from app.core.readiness import ReadinessChecker
from app.llm.metrics import default_llm_metrics
from app.tools.metrics import default_tool_metrics

router = APIRouter(tags=["System"])


class HealthResponse(BaseModel):
    """Lightweight liveness payload — no expensive dependency probes."""

    status: str = Field(..., description="Liveness status (always 'healthy' when reachable)")
    app_name: str = Field(..., description="Application name")
    environment: str = Field(..., description="Runtime environment")
    version: str = Field(..., description="Active API version")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")


class DependencyStatus(BaseModel):
    status: str
    latency_ms: float = 0.0
    detail: str = ""
    postgis: Optional[str] = Field(
        default=None,
        description="PostGIS availability/version for the database probe (when present)",
    )


class ReadyResponse(BaseModel):
    """Readiness payload aggregating pluggable dependency probes."""

    status: str = Field(..., description="'ready' when all probes pass, else 'not_ready'")
    ready: bool = Field(..., description="Boolean readiness flag")
    dependencies: Dict[str, DependencyStatus] = Field(
        default_factory=dict,
        description="Per-dependency probe results (only for registered dependencies)",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check (liveness)",
)
async def health(request: Request) -> HealthResponse:
    """Confirm the backend process is alive.

    Deliberately lightweight: it never calls the LLM, weather providers, GIS,
    NWP, or any expensive database operation. Use for load-balancer / Docker
    liveness probes.
    """
    settings = request.app.state.settings
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        environment=settings.app_env,
        version=settings.api_version,
        timestamp=_now_iso(),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
)
async def ready(request: Request) -> ReadyResponse:
    """Report whether the backend is ready to serve traffic.

    Runs the pluggable :class:`ReadinessChecker` probes registered during
    startup. Only probes whose dependencies actually exist are registered —
    no fabricated database/GIS/NWP checks.
    """
    readiness: ReadinessChecker = request.app.state.readiness
    ready_flag, results = await readiness.check_all()

    dependencies: Dict[str, DependencyStatus] = {}
    for result in results:
        dependencies[result.name] = DependencyStatus(
            status="connected" if result.ok else "unavailable",
            latency_ms=result.latency_ms,
            detail=result.detail,
            postgis=result.metadata.get("postgis"),
        )

    return ReadyResponse(
        status="ready" if ready_flag else "not_ready",
        ready=ready_flag,
        dependencies=dependencies,
    )


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Application and Provider Metrics",
)
async def metrics(request: Request) -> Dict[str, Any]:
    """Expose application-level HTTP/API metrics, external provider metrics, and request deduplication telemetry."""
    deduplicator = getattr(request.app.state.container, "deduplicator", None)
    dedup_summary = deduplicator.metrics.get_summary() if deduplicator else {}

    return {
        "api": api_metrics.get_summary(),
        "providers": provider_metrics.get_summary(),
        "deduplication": dedup_summary,
        "llm": default_llm_metrics.get_summary(),
        "tools": default_tool_metrics.get_summary(),
        "timestamp": _now_iso(),
    }


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root metadata",
)
async def root(request: Request) -> Dict[str, Any]:
    """Root endpoint exposing navigation metadata."""
    return {
        "message": f"Welcome to {request.app.state.settings.app_name} API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "health_url": "/api/v1/health",
        "ready_url": "/api/v1/ready",
        "metrics_url": "/api/v1/metrics",
        "version": request.app.state.settings.api_version,
    }
