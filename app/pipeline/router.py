"""FastAPI REST API router for VAYUBODHAK Phase 9A — Operational Pipeline Orchestration.

Exposes endpoints for:
- POST /api/v1/pipeline/run: Execute or retrieve an end-to-end multi-hazard pipeline run.
- GET  /api/v1/pipeline/{pipeline_run_id}: Retrieve full run record and NirnayCard.
- GET  /api/v1/pipeline/{pipeline_run_id}/status: Retrieve lightweight operational status.
- GET  /api/v1/pipeline/{pipeline_run_id}/trace: Retrieve deep backward lineage trace.
- POST /api/v1/pipeline/{pipeline_run_id}/resume: Resume an interrupted or failed pipeline run.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.decision.auth import (
    ReviewerPrincipal,
    ReviewerRole,
    decode_and_verify_token,
)
from app.pipeline.models import (
    DataSourceStatus,
    PipelineInput,
    PipelineRun,
    PipelineStatusResponse,
    PipelineTrace,
)
from app.pipeline.orchestrator import vayubodhak_pipeline
from app.pipeline.repository import pipeline_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Phase 9A Operational Pipeline Orchestration"])


# ============================================================================
# RBAC Dependencies for Pipeline Orchestration
# ============================================================================

def get_current_principal_optional(
    authorization: Optional[str] = Header(default=None),
) -> Optional[ReviewerPrincipal]:
    """Extracts authenticated principal if present, without failing anonymous requests."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    raw_token = authorization.split("Bearer ", 1)[1].strip()
    if not raw_token:
        return None
    try:
        return decode_and_verify_token(raw_token)
    except HTTPException:
        raise
    except Exception:
        return None


def require_pipeline_principal(
    authorization: Optional[str] = Header(default=None),
) -> ReviewerPrincipal:
    """Requires a valid cryptographic Bearer token for privileged pipeline actions."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Bearer token required for pipeline execution.",
        )
    raw_token = authorization.split("Bearer ", 1)[1].strip()
    return decode_and_verify_token(raw_token)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/run",
    response_model=PipelineRun,
    summary="Execute or retrieve an End-to-End Multi-Hazard Pipeline Run",
)
async def run_pipeline(
    request: PipelineInput,
    force: bool = Query(default=False, description="Bypass idempotency cache and force re-evaluation"),
    principal: Optional[ReviewerPrincipal] = Depends(get_current_principal_optional),
) -> PipelineRun:
    """Executes the canonical Phase 2A -> Phase 8 multi-hazard pipeline.
    
    Guarantees:
    - Zero client override of internal hazard states, risk tiers, or decision rules.
    - Idempotency: identical inputs return the existing run unless 'force' is True.
    - Deterministic execution across Evidence -> Hazard -> Exposure -> Vulnerability -> Risk -> Impact -> Decision.
    """
    logger.info(
        "POST /api/v1/pipeline/run: Starting run for input reference '%s' (geography=%s, caller=%s)",
        request.input_reference,
        request.geography,
        principal.subject if principal else "anonymous",
    )

    run = await vayubodhak_pipeline.run(request, force_reevaluate=force)
    return run


@router.get(
    "/{pipeline_run_id}",
    response_model=PipelineRun,
    summary="Get full PipelineRun execution details and NirnayCard",
)
async def get_pipeline_run(
    pipeline_run_id: str,
) -> PipelineRun:
    """Retrieves full execution snapshot, entity references, and NirnayCard for a pipeline run."""
    run = await pipeline_repository.get_run(pipeline_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{pipeline_run_id}' not found.",
        )
    return run


@router.get(
    "/{pipeline_run_id}/status",
    response_model=PipelineStatusResponse,
    summary="Get lightweight operational status of a pipeline run",
)
async def get_pipeline_status(
    pipeline_run_id: str,
) -> PipelineStatusResponse:
    """Returns compact state and timing metadata for monitoring and UI polling."""
    run = await pipeline_repository.get_run(pipeline_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{pipeline_run_id}' not found.",
        )

    return PipelineStatusResponse(
        pipeline_run_id=run.pipeline_run_id,
        pipeline_state=run.pipeline_state,
        current_stage=run.current_stage,
        completed_stages=run.completed_stages,
        failed_stage=run.failed_stage,
        quality_state=run.quality_state,
        started_at_iso=run.started_at_iso,
        completed_at_iso=run.completed_at_iso,
        provenance_id=run.provenance_id,
        durability_label=run.durability_label,
    )


@router.get(
    "/{pipeline_run_id}/trace",
    response_model=PipelineTrace,
    summary="Get deep backward lineage trace from NirnayCard to Evidence",
)
async def get_pipeline_trace(
    pipeline_run_id: str,
    principal: Optional[ReviewerPrincipal] = Depends(get_current_principal_optional),
) -> PipelineTrace:
    """Answers: 'Why did this NirnayCard appear?'
    
    Provides complete backward lineage connecting:
    NirnayCard -> Decision -> Impact -> Risk -> Vulnerability -> Exposure -> Hazard -> Evidence.
    """
    run = await pipeline_repository.get_run(pipeline_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{pipeline_run_id}' not found.",
        )

    trace = vayubodhak_pipeline.build_trace(run)
    return trace


@router.post(
    "/{pipeline_run_id}/resume",
    response_model=PipelineRun,
    summary="Resume an interrupted or failed pipeline run from checkpoint",
)
async def resume_pipeline(
    pipeline_run_id: str,
    principal: ReviewerPrincipal = Depends(require_pipeline_principal),
) -> PipelineRun:
    """Resumes execution of an interrupted or failed pipeline run from its failure checkpoint.
    
    Requires an authenticated reviewer token to prevent unauthorized mutation.
    """
    logger.info(
        "POST /api/v1/pipeline/%s/resume: Resumed by subject '%s' (role=%s)",
        pipeline_run_id,
        principal.subject,
        principal.role,
    )

    try:
        run = await vayubodhak_pipeline.resume(pipeline_run_id)
        return run
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume pipeline run: {exc}",
        )
