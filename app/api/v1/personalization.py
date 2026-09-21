"""Personalization, Decision Quality & History REST API Router (/api/v1/personalization).

Delivers:
- User preferences configuration (language, minimum severity, quiet hours, crop priorities).
- Deterministic personalized "Today for You" prioritized dashboard.
- User action tracking (viewed, acknowledged, dismissed, followed).
- Explicit operational outcome recording (spraying completed/postponed, irrigation).
- Auditable immutable decision history queries.
- Statistical forecast accuracy verification and decision utility metrics.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.providers import get_personalization_service
from app.personalization.domain_models import (
    DecisionOutcomeRecordDTO,
    QualitySummaryResponse,
    RecordActionRequest,
    RecordOutcomeRequest,
    TodayForYouDashboard,
    UserActionRecordDTO,
    UserPreferences,
)
from app.personalization.service import PersonalizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/personalization", tags=["Personalization & Decision Quality (Phase 10)"])


# ============================================================================
# 1. Preferences Endpoints
# ============================================================================

@router.get(
    "/{user_id}/preferences",
    response_model=UserPreferences,
    status_code=status.HTTP_200_OK,
    summary="Fetch user personalization preferences",
)
async def get_user_preferences(
    user_id: str,
    service: PersonalizationService = Depends(get_personalization_service),
) -> UserPreferences:
    """Returns the persistent preferences for the specified user or default settings if unconfigured."""
    return await service.get_preferences(user_id=user_id)


@router.post(
    "/preferences",
    response_model=UserPreferences,
    status_code=status.HTTP_200_OK,
    summary="Upsert user personalization preferences",
)
async def save_user_preferences(
    preferences: UserPreferences,
    service: PersonalizationService = Depends(get_personalization_service),
) -> UserPreferences:
    """Updates or creates user personalization preferences."""
    return await service.update_preferences(preferences=preferences)


# ============================================================================
# 2. Personalized Dashboard ("Today for You")
# ============================================================================

@router.get(
    "/{user_id}/today",
    response_model=TodayForYouDashboard,
    status_code=status.HTTP_200_OK,
    summary="Get personalized 'Today for You' prioritized decision dashboard",
)
async def get_today_for_you_dashboard(
    user_id: str,
    service: PersonalizationService = Depends(get_personalization_service),
) -> TodayForYouDashboard:
    """Ranks and groups proactive weather decisions and official alerts deterministically for the user."""
    return await service.get_today_for_you_dashboard(user_id=user_id)


# ============================================================================
# 3. User Action Tracking Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/action",
    response_model=UserActionRecordDTO,
    status_code=status.HTTP_200_OK,
    summary="Record user interaction action on a proactive event",
)
async def record_event_action(
    event_id: str,
    request: RecordActionRequest,
    service: PersonalizationService = Depends(get_personalization_service),
) -> UserActionRecordDTO:
    """Logs explicit user interaction (e.g. viewed, acknowledged, dismissed) with an event."""
    return await service.record_user_action(
        user_id=request.user_id,
        action_type=request.action_type,
        event_id=event_id,
        metadata=request.metadata,
    )


# ============================================================================
# 4. Outcome Recording Endpoints
# ============================================================================

@router.post(
    "/decisions/{decision_id}/outcome",
    response_model=DecisionOutcomeRecordDTO,
    status_code=status.HTTP_200_OK,
    summary="Record verified real-world operational outcome for a decision",
)
async def record_decision_outcome(
    decision_id: str,
    request: RecordOutcomeRequest,
    service: PersonalizationService = Depends(get_personalization_service),
) -> DecisionOutcomeRecordDTO:
    """Records explicit user-reported outcome (e.g. spraying postponed, irrigation completed)."""
    return await service.record_decision_outcome(
        user_id=request.user_id,
        outcome_type=request.outcome_type,
        decision_id=decision_id,
        notes=request.notes,
        metadata=request.metadata,
    )


# ============================================================================
# 5. Auditable Decision History Endpoints
# ============================================================================

@router.get(
    "/decisions/{user_id}/history",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Retrieve auditable immutable decision history for a user",
)
async def get_user_decision_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: PersonalizationService = Depends(get_personalization_service),
) -> List[Dict[str, Any]]:
    """Fetches auditable decision records including evidence snapshots, provenance, and action windows."""
    return await service.get_user_history(user_id=user_id, limit=limit)


# ============================================================================
# 6. Quality & Verification Endpoints
# ============================================================================

@router.get(
    "/quality/{location_or_user}",
    response_model=QualitySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast accuracy and decision utility metrics",
)
async def get_quality_metrics(
    location_or_user: str,
    latitude: Optional[float] = Query(default=None, ge=6.0, le=38.0),
    longitude: Optional[float] = Query(default=None, ge=68.0, le=98.0),
    service: PersonalizationService = Depends(get_personalization_service),
) -> QualitySummaryResponse:
    """Computes statistical forecast verification metrics (MAE, rain accuracy) and decision utility adherence."""
    return await service.get_quality_summary(
        location_or_user=location_or_user,
        latitude=latitude,
        longitude=longitude,
    )
