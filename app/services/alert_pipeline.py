"""Background pipeline bridging CAP alerts to Farmer Plots (USP Phase 7).

This service receives active alerts, finds intersecting registered farmer plots
using PostGIS, builds a live EvidenceBundle for each plot, and pushes it through
the DeterministicDecisionEngine to generate localized push notification payloads.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.farmer import FarmerPlotRepository
from app.decision.engine import DeterministicDecisionEngine
from app.decision.evidence_builder import EvidenceBundleBuilder
from app.decision.models import DecisionLocationQuery

logger = logging.getLogger(__name__)


class AlertPipelineService:
    """Pipelines active severe weather alerts to affected farmers."""

    _processed_alert_ids: set = set()

    def __init__(
        self,
        session: AsyncSession,
        farmer_repo: FarmerPlotRepository,
        evidence_builder: EvidenceBundleBuilder,
        decision_engine: DeterministicDecisionEngine,
    ):
        self.session = session
        self.farmer_repo = farmer_repo
        self.evidence_builder = evidence_builder
        self.decision_engine = decision_engine

    async def process_alert(self, alert_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processes an incoming CAP alert and generates push payloads for affected farmers.
        
        Args:
            alert_payload: Dictionary containing alert details, notably a WKT polygon 
                           representing the hazard boundary in `wkt_polygon`.
                           
        Returns:
            List of generated push notification payloads.
        """
        alert_id = alert_payload.get("alert_id")
        if alert_id:
            if alert_id in AlertPipelineService._processed_alert_ids:
                logger.info("AlertPipelineService: Alert '%s' already processed (duplicate ignored).", alert_id)
                return []
            AlertPipelineService._processed_alert_ids.add(alert_id)

        wkt_polygon = alert_payload.get("wkt_polygon")
        if not wkt_polygon:
            logger.warning("AlertPipelineService: Received alert without wkt_polygon geometry (spatial state UNKNOWN).")
            return []
            
        logger.info("AlertPipelineService: Processing new alert for hazard %s", alert_payload.get("hazard_type", "Unknown"))
        
        # 1. Find all intersecting plots
        affected_plots = await self.farmer_repo.find_plots_in_polygon(wkt_polygon)
        logger.info("AlertPipelineService: Found %d affected farmer plots in alert polygon.", len(affected_plots))
        
        push_payloads = []
        
        # 2. Generate customized decisions for each plot
        for plot in affected_plots:
            try:
                location_query = DecisionLocationQuery(
                    name=plot.plot_name,
                    latitude=float(plot.centroid_lat),
                    longitude=float(plot.centroid_lon),
                )
                
                # Build localized evidence
                evidence = await self.evidence_builder.build_bundle(
                    location_query=location_query,
                    domain="farmer",
                    context={"crop_name": plot.crop_name}
                )
                
                # Normalize CAP alert dictionary preserving metadata
                alert_dict = {
                    "alert_id": alert_id or "OFFICIAL-ALERT-01",
                    "sender": alert_payload.get("sender", "NDMA Sachet CAP"),
                    "warning_level": alert_payload.get("warning_level", "Yellow"),
                    "hazard_type": alert_payload.get("hazard_type", "Severe Weather"),
                    "event_title": alert_payload.get("headline", "Official Warning"),
                    "headline": alert_payload.get("headline", ""),
                    "description": alert_payload.get("headline", ""),
                    "instruction": alert_payload.get("prescribed_action"),
                    "area_description": alert_payload.get("area_description", plot.plot_name),
                    "polygons": [wkt_polygon] if wkt_polygon else [],
                    "effective": alert_payload.get("effective_time_iso"),
                    "expires": alert_payload.get("expires_time_iso"),
                }
                
                # Inject normalized alert into evidence package
                if not any(a.get("alert_id") == alert_dict["alert_id"] for a in evidence.alerts):
                    evidence.alerts.append(alert_dict)
                
                # Evaluate decision (e.g. for spraying, field operations, irrigation)
                question = f"What should I do on my {plot.crop_name} field given the incoming weather?"
                nirnay_card = self.decision_engine.evaluate_decision(
                    evidence=evidence,
                    question=question,
                    domain="farmer",
                    context={"crop_name": plot.crop_name}
                )
                
                # Formulate push notification payload with full auditability
                payload = {
                    "user_id": plot.user_id,
                    "plot_id": plot.plot_id,
                    "plot_name": plot.plot_name,
                    "crop_name": plot.crop_name,
                    "hazard": alert_payload.get("hazard_type"),
                    "warning_level": alert_payload.get("warning_level"),
                    "sender": alert_dict["sender"],
                    "verdict": nirnay_card.verdict.value,
                    "severity": nirnay_card.severity.value,
                    "action": nirnay_card.recommended_action,
                    "why": nirnay_card.why,
                    "exposure_state": nirnay_card.evidence.get("exposure_state", "INSIDE"),
                    "nirnay_card": nirnay_card.model_dump(),
                }
                push_payloads.append(payload)
                
                logger.info("AlertPipelineService: Generated %s payload for user %s (Plot: %s)", 
                            nirnay_card.verdict.value, plot.user_id, plot.plot_name)
                            
            except Exception as e:
                logger.error("AlertPipelineService: Failed to process plot %s: %s", plot.plot_id, str(e))
                
        return push_payloads
