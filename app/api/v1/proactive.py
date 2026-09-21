"""Proactive Weather Intelligence & Decision API Router (/api/v1/proactive)."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.providers import (
    get_device_token_repository,
    get_outbox_delivery_worker,
    get_proactive_decision_service,
)
from app.proactive.delivery import NotificationPayload
from app.proactive.models import (
    AcknowledgeEventResponse,
    DeviceTokenDTO,
    EventDeliveryStatus,
    OutboxProcessResponse,
    ProactiveEvaluateFarmerRequest,
    ProactiveEvaluateLocationRequest,
    RegisterDeviceRequest,
    RegisterDeviceResponse,
    WeatherDecisionEvent,
)
from app.proactive.service import ProactiveDecisionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/proactive",
    tags=["Proactive Weather Intelligence & Decisions"],
)


@router.post(
    "/evaluate/farmer/{user_id}",
    response_model=List[WeatherDecisionEvent],
    summary="Evaluate proactive weather decisions for registered farmer plots",
    description="Deterministically evaluates operational weather risks and action window changes across all registered plots of a farmer.",
)
async def evaluate_farmer_proactive_events(
    user_id: str,
    request: Optional[ProactiveEvaluateFarmerRequest] = None,
    service: Any = Depends(get_proactive_decision_service),
) -> List[WeatherDecisionEvent]:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proactive Decision service is offline or unconfigured."
        )

    try:
        prefs = request.preferences if request else None
        force = request.force_reevaluate if request else False
        events = await service.evaluate_farmer_events(
            user_id=user_id,
            preferences=prefs,
            force_reevaluate=force,
        )
        return events
    except Exception as exc:
        logger.exception("Failed to evaluate farmer proactive events for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate farmer proactive events: {str(exc)}"
        )


@router.post(
    "/evaluate/location",
    response_model=List[WeatherDecisionEvent],
    summary="Evaluate proactive weather decisions for geographic coordinates",
    description="Evaluates severe weather risks (heat, heavy rain, wind squalls, official alerts) for a general coordinate location.",
)
async def evaluate_location_proactive_events(
    request: ProactiveEvaluateLocationRequest,
    service: Any = Depends(get_proactive_decision_service),
) -> List[WeatherDecisionEvent]:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proactive Decision service is offline or unconfigured."
        )

    try:
        events = await service.evaluate_location_events(
            latitude=request.latitude,
            longitude=request.longitude,
            location_name=request.location_name or "Target Location",
            district=request.district,
            state=request.state,
            user_id=request.user_id or "guest_user",
            preferences=request.preferences,
            force_reevaluate=request.force_reevaluate,
        )
        return events
    except Exception as exc:
        logger.exception("Failed to evaluate location proactive events: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate location proactive events: {str(exc)}"
        )


@router.get(
    "/events/{user_id}",
    response_model=List[WeatherDecisionEvent],
    summary="Get recorded proactive events for a user",
    description="Retrieves active and recent proactive decision events for a given user.",
)
async def get_user_proactive_events(
    user_id: str,
    service: Any = Depends(get_proactive_decision_service),
) -> List[WeatherDecisionEvent]:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proactive Decision service is offline or unconfigured."
        )

    return service.get_user_events(user_id)


@router.post(
    "/events/{event_id}/acknowledge",
    response_model=AcknowledgeEventResponse,
    summary="Acknowledge a proactive decision event",
    description="Updates the event lifecycle status to ACKNOWLEDGED.",
)
async def acknowledge_proactive_event(
    event_id: str,
    service: Any = Depends(get_proactive_decision_service),
) -> AcknowledgeEventResponse:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proactive Decision service is offline or unconfigured."
        )

    success = service.acknowledge_event(event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proactive event '{event_id}' not found."
        )

    return AcknowledgeEventResponse(
        event_id=event_id,
        acknowledged=True,
        delivery_status=EventDeliveryStatus.ACKNOWLEDGED,
        message="Event marked as acknowledged.",
    )


@router.get(
    "/notifications/{user_id}",
    response_model=List[NotificationPayload],
    summary="Get delivery outbox notifications for a user",
    description="Retrieves queued or delivered notifications from the decoupled notification outbox.",
)
async def get_user_notifications(
    user_id: str,
    service: Any = Depends(get_proactive_decision_service),
) -> List[NotificationPayload]:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proactive Decision service is offline or unconfigured."
        )

    return service.delivery_service.get_outbox(user_id)


@router.post(
    "/devices",
    response_model=RegisterDeviceResponse,
    summary="Register or refresh a user device push token",
    description="Registers an active FCM push token for an Android or iOS client.",
)
async def register_device_token(
    request: RegisterDeviceRequest,
    device_repo: Any = Depends(get_device_token_repository),
) -> RegisterDeviceResponse:
    if device_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device token repository is offline or database unconfigured.",
        )

    try:
        record = await device_repo.register_or_update_token(
            user_id=request.user_id,
            device_id=request.device_id,
            fcm_token=request.fcm_token,
            platform=request.platform,
        )
        return RegisterDeviceResponse(
            device_id=record.device_id,
            user_id=record.user_id,
            registered=True,
            message="Device push token registered successfully.",
        )
    except Exception as exc:
        logger.exception("Failed to register device token for %s: %s", request.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register device token: {str(exc)}",
        )


@router.get(
    "/devices/{user_id}",
    response_model=List[DeviceTokenDTO],
    summary="List active registered devices for a user",
    description="Retrieves all active device push tokens associated with the user account.",
)
async def get_user_devices(
    user_id: str,
    device_repo: Any = Depends(get_device_token_repository),
) -> List[DeviceTokenDTO]:
    if device_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device token repository is offline or database unconfigured.",
        )

    devices = await device_repo.get_active_tokens_for_user(user_id)
    return [
        DeviceTokenDTO(
            device_id=d.device_id,
            user_id=d.user_id,
            platform=d.platform,
            is_active=d.is_active,
            created_at=d.created_at.isoformat() if hasattr(d.created_at, "isoformat") else str(d.created_at),
            updated_at=d.updated_at.isoformat() if hasattr(d.updated_at, "isoformat") else str(d.updated_at),
        )
        for d in devices
    ]


@router.delete(
    "/devices/{device_id}",
    summary="Deactivate a registered device",
    description="Deactivates or removes a device push token.",
)
async def deactivate_user_device(
    device_id: str,
    device_repo: Any = Depends(get_device_token_repository),
) -> Dict[str, Any]:
    if device_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device token repository is offline or database unconfigured.",
        )

    success = await device_repo.deactivate_device(device_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )
    return {"device_id": device_id, "deactivated": True}


@router.post(
    "/outbox/process",
    response_model=OutboxProcessResponse,
    summary="Process pending outbox delivery batch",
    description="Triggers the background delivery worker to process a batch of pending proactive outbox items.",
)
async def process_outbox_batch(
    worker: Any = Depends(get_outbox_delivery_worker),
) -> OutboxProcessResponse:
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outbox delivery worker is offline or database unconfigured.",
        )

    try:
        stats = await worker.process_batch()
        return OutboxProcessResponse(**stats)
    except Exception as exc:
        logger.exception("Outbox worker processing failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Outbox processing failed: {str(exc)}",
        )

