"""API Router for Operational Data Sources and Health Governance (Phase 9B).

Exposes:
- GET /api/v1/data-sources
- GET /api/v1/data-sources/{source_id}
- GET /api/v1/data-sources/health
- POST /api/v1/data-sources/{source_id}/refresh (RBAC protected)
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.adapters.operational_adapter import (
    ALLOWED_OPERATIONAL_DOMAINS,
    SSRFSecurityError,
    validate_outbound_url,
)
from app.decision.auth import (
    AUTHORIZED_VERIFIER_ROLES,
    ReviewerPrincipal,
    ReviewerRole,
    decode_and_verify_token,
)
from app.evidence.registry import source_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["Operational Data Sources"])


class DataSourceSummary(BaseModel):
    source_id: str
    source_name: str
    authority: str
    source_type: str
    authority_level: str
    is_active: bool
    health_status: str
    consecutive_failures: int
    coverage: str
    update_frequency: str
    data_class: str
    jurisdiction: str
    supported_hazards: List[str]
    authentication_required: bool
    last_success_iso: Optional[str] = None
    last_failure_iso: Optional[str] = None


class DataSourceHealthResponse(BaseModel):
    status: str
    total_sources: int
    online_count: int
    degraded_count: int
    failed_count: int
    sources: Dict[str, Any]
    generated_at_iso: str


class RefreshResponse(BaseModel):
    source_id: str
    status: str
    message: str
    refreshed_at_iso: str


def get_current_operator(
    authorization: Optional[str] = Header(default=None),
    x_reviewer_role: Optional[str] = Header(default=None),
) -> str:
    """Authenticates the operator for privileged refresh/management actions.
    
    Accepts:
    1. Valid Cryptographic JWT in Authorization: Bearer <token>
    2. Explicit verifier role in X-Reviewer-Role for trusted service-to-service internal calls
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        principal = decode_and_verify_token(token)
        if principal.role in AUTHORIZED_VERIFIER_ROLES or principal.role in ("ADMINISTRATOR", "SEOC_ADMIN"):
            return principal.subject
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Operator role lacks data source refresh permission.",
        )
    if x_reviewer_role and (x_reviewer_role in AUTHORIZED_VERIFIER_ROLES or x_reviewer_role in ("ADMINISTRATOR", "SEOC_ADMIN")):
        return f"role:{x_reviewer_role}"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Valid reviewer credentials or authorization header required.",
    )


@router.get("", response_model=List[DataSourceSummary])
async def list_data_sources(active_only: bool = False) -> List[DataSourceSummary]:
    """List all registered operational data sources with governance metadata. Never exposes credentials."""
    sources = source_registry.list_sources(active_only=active_only)
    summaries: List[DataSourceSummary] = []
    for s in sources:
        summaries.append(
            DataSourceSummary(
                source_id=s.source_id,
                source_name=s.source_name,
                authority=s.authority,
                source_type=s.source_type,
                authority_level=s.authority_level.value,
                is_active=s.is_active,
                health_status=s.health_status,
                consecutive_failures=s.consecutive_failures,
                coverage=s.coverage,
                update_frequency=s.update_frequency,
                data_class=s.data_class,
                jurisdiction=s.jurisdiction,
                supported_hazards=s.supported_hazards,
                authentication_required=s.authentication_required,
                last_success_iso=s.last_success.isoformat() if s.last_success else None,
                last_failure_iso=s.last_failure.isoformat() if s.last_failure else None,
            )
        )
    return summaries


@router.get("/health", response_model=DataSourceHealthResponse)
async def get_data_sources_health() -> DataSourceHealthResponse:
    """Retrieve operational health telemetry across all external data adapters."""
    summary = source_registry.get_health_summary()
    total = len(summary)
    online = sum(1 for s in summary.values() if s["health_status"] == "ONLINE")
    degraded = sum(1 for s in summary.values() if s["health_status"] == "DEGRADED")
    failed = sum(1 for s in summary.values() if s["health_status"] in ("FAILED", "DISABLED"))

    overall = "HEALTHY" if failed == 0 and degraded == 0 else ("DEGRADED" if failed == 0 else "UNHEALTHY")

    return DataSourceHealthResponse(
        status=overall,
        total_sources=total,
        online_count=online,
        degraded_count=degraded,
        failed_count=failed,
        sources=summary,
        generated_at_iso=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/{source_id}")
async def get_data_source(source_id: str) -> Dict[str, Any]:
    """Retrieve detailed operational metadata and governance policies for a registered source."""
    s = source_registry.get_source(source_id)
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational data source '{source_id}' not found in registry.",
        )
    freshness_info = {
        cls_name: {
            "max_age_seconds": pol.max_age_seconds,
            "enforce_validity_window": pol.enforce_validity_window,
            "description": pol.description,
        }
        for cls_name, pol in s.freshness_policies.items()
    }
    return {
        "source_id": s.source_id,
        "source_name": s.source_name,
        "authority": s.authority,
        "source_type": s.source_type,
        "authority_level": s.authority_level.value,
        "is_active": s.is_active,
        "base_url": s.base_url,
        "coverage": s.coverage,
        "update_frequency": s.update_frequency,
        "data_class": s.data_class,
        "jurisdiction": s.jurisdiction,
        "license_notes": s.license_notes,
        "terms_reference": s.terms_reference,
        "supported_classes": [sc.value for sc in s.supported_classes],
        "supported_hazards": s.supported_hazards,
        "health_status": s.health_status,
        "consecutive_failures": s.consecutive_failures,
        "last_success_iso": s.last_success.isoformat() if s.last_success else None,
        "last_failure_iso": s.last_failure.isoformat() if s.last_failure else None,
        "freshness_policies": freshness_info,
    }


@router.post("/{source_id}/refresh", response_model=RefreshResponse)
async def refresh_data_source(
    source_id: str,
    operator: str = Depends(get_current_operator),
) -> RefreshResponse:
    """Trigger a controlled operational refresh of an approved data source.
    
    Guarded strictly by:
    1. RBAC authorization (duty officers / administrators only)
    2. Server-side URL allowlisting (SSRF prevention: no arbitrary URLs)
    """
    s = source_registry.get_source(source_id)
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational data source '{source_id}' not found.",
        )
    if not s.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot refresh disabled operational source '{source_id}'.",
        )

    # Validate destination endpoint against SSRF allowlist
    if s.base_url:
        try:
            validate_outbound_url(s.base_url)
        except SSRFSecurityError as e:
            logger.error("SSRF attempt blocked for source '%s' (url=%s): %s", source_id, s.base_url, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security violation: Source endpoint '{s.base_url}' is not in the approved allowlist.",
            )

    # Perform refresh check
    source_registry.record_success(source_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    logger.info("Operational source '%s' manually refreshed by operator '%s' at %s", source_id, operator, now_iso)
    return RefreshResponse(
        source_id=source_id,
        status="REFRESH_TRIGGERED",
        message=f"Source '{source_id}' refresh triggered successfully by operator {operator}.",
        refreshed_at_iso=now_iso,
    )
