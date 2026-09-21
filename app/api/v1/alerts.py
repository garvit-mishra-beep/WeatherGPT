"""Alert Ingestion and Pipeline Trigger API."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.providers import get_alert_pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/alerts",
    tags=["Alert Notification Pipeline"],
)


from typing import Any, Dict, Optional

class AlertWebhookPayload(BaseModel):
    """Payload representing an incoming CAP alert or synthetic webhook."""
    hazard_type: str = Field(..., description="E.g., Rain, Wind, Squall")
    headline: str = Field(..., description="Alert headline")
    wkt_polygon: Optional[str] = Field(None, description="WKT Polygon of the hazard boundary (EPSG:4326)")
    warning_level: str = Field(..., description="Red, Orange, Yellow, Green")
    prescribed_action: Optional[str] = Field(None, description="Official prescribed action")
    sender: Optional[str] = Field(default="NDMA Sachet CAP", description="Issuing authority or sender")
    alert_id: Optional[str] = Field(default=None, description="Unique CAP alert identifier")
    area_description: Optional[str] = Field(default=None, description="Affected area description")
    effective_time_iso: Optional[str] = Field(default=None, description="ISO-8601 start timestamp")
    expires_time_iso: Optional[str] = Field(default=None, description="ISO-8601 expiry timestamp")


async def execute_alert_pipeline(
    payload: Dict[str, Any],
    service: Any
):
    """Background task runner for the alert pipeline."""
    try:
        if service is None:
            logger.error("Alert Pipeline Service is offline.")
            return
            
        push_payloads = await service.process_alert(payload)
        logger.info("Alert pipeline generated %d push notifications.", len(push_payloads))
        
        # Here we would normally send push_payloads to an outbox or Kafka topic.
        # For this Phase 7 implementation, we log them explicitly to demonstrate the pipeline end-to-end.
        for p in push_payloads:
            logger.info("PUSH NOTIFICATION -> Farmer: %s | Plot: %s | Verdict: %s | Action: %s",
                        p.get("user_id"), p.get("plot_name"), p.get("verdict"), p.get("action"))
    except Exception as exc:
        logger.error("Alert pipeline failed: %s", str(exc))


@router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a CAP alert and trigger pipeline",
    description="Acts as a webhook to ingest an alert and asynchronously trigger the Alert->Impact->Action pipeline.",
)
async def ingest_alert_webhook(
    payload: AlertWebhookPayload,
    background_tasks: BackgroundTasks,
    service: Any = Depends(get_alert_pipeline_service),
) -> Dict[str, str]:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert Pipeline service is offline or unconfigured."
        )

    # Queue the pipeline in the background so the webhook returns quickly
    background_tasks.add_task(
        execute_alert_pipeline,
        payload.model_dump(),
        service
    )
    
    return {"status": "accepted", "message": "Alert ingestion queued for processing."}
