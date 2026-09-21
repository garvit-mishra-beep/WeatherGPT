"""Farmer Intelligence Service (Phase 6).

Coordinates:
1. FarmerContext parsing (ensuring crop_stage='UNKNOWN' if not provided).
2. Meteorological and agricultural evidence collation (FarmerEvidence).
3. Deterministic Decision Engine execution for irrigation, spraying, harvesting, sowing,
   daily farm planning, and crop-weather risk.
4. Optional Gemma 4:e2b explanation via FarmerExplanationBridge.

STRICT INVARIANTS:
- No LLM calculations or estimations.
- Never invent soil moisture, crop stage, or crop-specific thresholds.
- Mandatory soil disclaimer when unmeasured.
- Alert priority preserved.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.adapters.strategy import WeatherProviderManager
from app.analytics.water_balance import calculate_crop_water_balance, evaluate_spray_window
from app.climate.service import ClimateIntelligenceService
from app.contracts.location import LocationContext
from app.decision.action_window import ActionWindowEngine
from app.decision.alert_impact import AlertImpactEngine
from app.decision.engine import DeterministicDecisionEngine
from app.decision.evidence_builder import EvidenceBundleBuilder
from app.decision.models import (
    ConfidenceLevel,
    DecisionLocationQuery,
    DecisionOutcome,
    EvidenceBundle,
    NirnayCard,
    SeverityLevel,
)
from app.farmer.analytics import (
    UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
    evaluate_crop_weather_risk,
    evaluate_harvest_window,
    evaluate_irrigation_intelligence,
    evaluate_sowing_fieldwork,
    generate_daily_farm_plan,
    get_crop_coefficient,
)
from app.farmer.explanation_bridge import FarmerExplanationBridge
from app.farmer.models import (
    DailyFarmPlan,
    FarmerAdvisoryRequest,
    FarmerAdvisoryResponse,
    FarmerContext,
    FarmerEvidence,
    HarvestSuitabilityState,
    IrrigationState,
)
from app.tools.catalog import INDIAN_LOCATIONS

logger = logging.getLogger(__name__)


class FarmerIntelligenceService:
    """Service providing end-to-end deterministic agricultural intelligence."""

    def __init__(
        self,
        decision_engine: Optional[DeterministicDecisionEngine] = None,
        action_window_engine: Optional[ActionWindowEngine] = None,
        alert_impact_engine: Optional[AlertImpactEngine] = None,
        climate_service: Optional[ClimateIntelligenceService] = None,
        explanation_bridge: Optional[FarmerExplanationBridge] = None,
        evidence_builder: Optional[EvidenceBundleBuilder] = None,
    ) -> None:
        self.action_window_engine = action_window_engine or ActionWindowEngine()
        self.alert_impact_engine = alert_impact_engine or AlertImpactEngine()
        self.decision_engine = decision_engine or DeterministicDecisionEngine(
            action_window_engine=self.action_window_engine,
            alert_impact_engine=self.alert_impact_engine,
        )
        self.climate_service = climate_service
        self.explanation_bridge = explanation_bridge
        self.evidence_builder = evidence_builder or EvidenceBundleBuilder()

    def resolve_farmer_context(self, request: FarmerAdvisoryRequest) -> FarmerContext:
        """Parses and normalizes FarmerContext.

        CRITICAL INVARIANT:
        If crop_stage is missing or empty, sets crop_stage='UNKNOWN' and never guesses.
        """
        ctx = request.context or FarmerContext()

        crop = request.crop or ctx.crop
        raw_stage = request.crop_stage or ctx.crop_stage
        resolved_stage = raw_stage.strip() if raw_stage and raw_stage.strip().upper() not in ("NONE", "") else "UNKNOWN"

        lat = request.latitude if request.latitude is not None else ctx.latitude
        lon = request.longitude if request.longitude is not None else ctx.longitude
        loc_name = request.location or ctx.location

        # If location name provided but no coordinates, look up in INDIAN_LOCATIONS
        if loc_name and (lat is None or lon is None):
            lookup = INDIAN_LOCATIONS.get(loc_name.strip().lower())
            if lookup:
                lat = lookup["lat"]
                lon = lookup["lon"]

        return FarmerContext(
            crop=crop,
            crop_stage=resolved_stage,
            location=loc_name,
            latitude=lat,
            longitude=lon,
            soil_type=ctx.soil_type,
            irrigation_method=ctx.irrigation_method,
            field_size=ctx.field_size,
            sowing_date=ctx.sowing_date,
            last_irrigation=ctx.last_irrigation,
            last_rainfall=ctx.last_rainfall,
            crop_coefficient=ctx.crop_coefficient,
            user_provided_field_information=ctx.user_provided_field_information,
        )

    def build_farmer_evidence(
        self,
        evidence_bundle: EvidenceBundle,
        farmer_context: FarmerContext,
        climate_context: Optional[Dict[str, Any]] = None,
    ) -> FarmerEvidence:
        """Constructs canonical FarmerEvidence package."""
        kc, resolved_stage, is_stage_known = get_crop_coefficient(
            crop_name=farmer_context.crop,
            stage=farmer_context.crop_stage,
            override_kc=farmer_context.crop_coefficient,
        )

        obs = evidence_bundle.observations or {}
        fc = evidence_bundle.forecast or {}
        alerts = evidence_bundle.alerts or []

        weather_evidence = {
            "temperature_c": obs.get("temperature_c", fc.get("temperature_c", 28.0)),
            "wind_speed_kmh": obs.get("wind_speed_kmh", fc.get("wind_speed_kmh", 10.0)),
            "rain_probability_pct": fc.get("rain_probability_pct", 0.0),
            "rainfall_today_mm": obs.get("rainfall_mm", 0.0),
            "forecast_rainfall_48h_mm": fc.get("rainfall_total_mm", 0.0),
            "relative_humidity_pct": obs.get("relative_humidity_pct", fc.get("relative_humidity_pct", 60.0)),
            "et0_mm_day": fc.get("et0_mm_day", 4.5),
        }

        crop_evidence = {
            "crop": farmer_context.crop or "Not specified",
            "stage": resolved_stage,
            "crop_coefficient_kc": kc,
            "stage_confidence": "SPECIFIED" if is_stage_known else "UNKNOWN_DEFAULT",
            "stage_caveat": None if is_stage_known else "Growth stage is unspecified (UNKNOWN); using standard default Kc.",
        }

        water_evidence = {
            "recent_rainfall_mm": obs.get("rainfall_mm", 0.0),
            "forecast_rain_48h_mm": fc.get("rainfall_total_mm", 0.0),
            "soil_type": farmer_context.soil_type or "Unspecified",
            "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
        }

        hazard_evidence = {
            "active_alerts_count": len(alerts),
            "alerts": alerts,
        }

        uncertainty_evidence = {
            "wrf_regional_available": False,
            "wrf_honesty_statement": "Regional WRF unconfigured. Surface forecast from GFS 0.25°.",
            "soil_moisture": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            "crop_stage": "Stage unknown; recommendations use generic baseline." if not is_stage_known else "Verified.",
        }

        return FarmerEvidence(
            weather=weather_evidence,
            crop=crop_evidence,
            water=water_evidence,
            hazard=hazard_evidence,
            climate=climate_context,
            provenance=evidence_bundle.source_information or [],
            uncertainty=uncertainty_evidence,
        )

    async def evaluate_advisory(self, request: FarmerAdvisoryRequest) -> FarmerAdvisoryResponse:
        """Main entry point for farmer agricultural advisories."""
        farmer_ctx = self.resolve_farmer_context(request)

        # 1. Resolve EvidenceBundle
        loc_query = DecisionLocationQuery(
            name=farmer_ctx.location or "Gwalior",
            latitude=farmer_ctx.latitude or 26.2183,
            longitude=farmer_ctx.longitude or 78.1828,
        )
        bundle = await self.evidence_builder.build_bundle(
            location_query=loc_query,
            domain="farmer",
            context=farmer_ctx.model_dump(),
        )

        # 2. Extract Climate Context if available
        climate_ctx: Optional[Dict[str, Any]] = None
        if self.climate_service:
            try:
                # Query climate anomalies for location
                loc_name = farmer_ctx.location or "Delhi"
                now_month = datetime.now(timezone.utc).month
                temp_normal, _, temp_avail, _, _ = self.climate_service.resolve_baseline(
                    location=loc_name, month=now_month
                )
                curr_temp = float(bundle.forecast.get("temperature_c", 28.0))
                if temp_avail and temp_normal:
                    temp_anomaly = round(curr_temp - temp_normal, 2)
                    climate_ctx = {
                        "temperature_anomaly_c": temp_anomaly,
                        "reference_normal_temp_c": temp_normal,
                        "is_heat_anomaly": temp_anomaly >= 3.0,
                    }
            except Exception as e:
                logger.debug("Climate service lookup failed: %s", e)

        # 3. Build FarmerEvidence
        farmer_evidence = self.build_farmer_evidence(bundle, farmer_ctx, climate_ctx)

        # 4. Route Operation
        op = (request.operation or "general").strip().lower()
        q = request.query or ""
        q_lower = q.lower()

        # Infer operation if general
        if op == "general":
            if any(k in q_lower for k in ["irrigate", "irrigation", "water", "पानी", "सिंचाई"]):
                op = "irrigation"
            elif any(k in q_lower for k in ["spray", "pesticide", "fertilizer", "छिड़काव", "दवा", "कीटनाशक"]):
                op = "spray"
            elif any(k in q_lower for k in ["harvest", "कटाई"]):
                op = "harvest"
            elif any(k in q_lower for k in ["sow", "sowing", "field work", "fieldwork", "बुवाई", "खेत का काम"]):
                op = "sowing"
            elif any(k in q_lower for k in ["plan", "what should i do", "daily", "आज क्या करें"]):
                op = "daily_plan"
            elif any(k in q_lower for k in ["risk", "heat", "dry spell", "जोखिम", "नुकसान"]):
                op = "risk"

        daily_plan: Optional[DailyFarmPlan] = None

        if op == "daily_plan":
            hourly_fc = getattr(bundle, "hourly_forecast", None) or bundle.forecast.get("hourly_forecast", []) or []
            daily_plan = generate_daily_farm_plan(
                farmer_context=farmer_ctx,
                weather_data=farmer_evidence.weather,
                hourly_forecast=hourly_fc,
                active_alerts=bundle.alerts or [],
                climate_context=climate_ctx,
            )
            # NirnayCard for daily plan
            has_no_go = any(item.status == "NO_GO" for item in daily_plan.operations)
            has_postpone = any(item.status in ("POSTPONE", "WAIT") for item in daily_plan.operations)
            card_verdict = DecisionOutcome.NO_GO if has_no_go else (DecisionOutcome.POSTPONE if has_postpone else DecisionOutcome.GO)
            card = NirnayCard(
                question=q or f"What should I do on my farm today for {farmer_ctx.crop or 'my crop'}?",
                verdict=card_verdict,
                severity=SeverityLevel.HIGH if has_no_go else (SeverityLevel.MODERATE if has_postpone else SeverityLevel.LOW),
                recommended_action=daily_plan.primary_advisory,
                action_window={"status": "available", "summary": "Full daily operational schedule generated."},
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"soil_moisture": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER},
                why=[f"{item.operation}: {item.status} ({item.reason})" for item in daily_plan.operations],
                impact={"daily_plan_summary": daily_plan.primary_advisory},
                alternatives=[item.action for item in daily_plan.operations],
                evidence=farmer_evidence.weather,
                ledger=None,
            )

        elif op == "harvest":
            card = self.decision_engine._evaluate_farmer_harvest(
                decision_id=f"dec_harv_{uuid.uuid4().hex[:6]}",
                evidence=bundle,
                question=q or f"Can I harvest my {farmer_ctx.crop or 'crop'} tomorrow?",
                context=farmer_ctx.model_dump(),
            )

        elif op in ("sowing", "field_work"):
            card = self.decision_engine._evaluate_farmer_sowing_fieldwork(
                decision_id=f"dec_fw_{uuid.uuid4().hex[:6]}",
                evidence=bundle,
                question=q or f"Should I sow / do field work today for {farmer_ctx.crop or 'my crop'}?",
                context=farmer_ctx.model_dump(),
            )

        elif op == "risk":
            card = self.decision_engine._evaluate_farmer_crop_risk(
                decision_id=f"dec_risk_{uuid.uuid4().hex[:6]}",
                evidence=bundle,
                question=q or f"What is the weather risk for my {farmer_ctx.crop or 'crop'} this week?",
                context=farmer_ctx.model_dump(),
                climate_context=climate_ctx,
            )

        elif op == "irrigation":
            card = self.decision_engine._evaluate_farmer_irrigation(
                decision_id=f"dec_irr_{uuid.uuid4().hex[:6]}",
                evidence=bundle,
                question=q or f"Should I irrigate my {farmer_ctx.crop or 'crop'} today?",
                context=farmer_ctx.model_dump(),
            )

        elif op == "spray":
            card = self.decision_engine._evaluate_farmer_spray(
                decision_id=f"dec_spray_{uuid.uuid4().hex[:6]}",
                evidence=bundle,
                question=q or f"Should I spray my {farmer_ctx.crop or 'cotton'} tonight?",
                context=farmer_ctx.model_dump(),
            )

        else:
            # General fallback to standard decision engine
            card = self.decision_engine.evaluate_decision(
                evidence=bundle,
                question=q or "What are the weather conditions for farming today?",
                domain="farmer",
                context=farmer_ctx.model_dump(),
            )

        # 5. Optional Gemma 4:e2b explanation
        explanation: Optional[str] = None
        if request.include_explanation and self.explanation_bridge:
            explanation = await self.explanation_bridge.explain_farmer_decision(
                card=card,
                farmer_context=farmer_ctx,
                farmer_evidence=farmer_evidence,
                language=request.language,
            )

        return FarmerAdvisoryResponse(
            decision_id=f"adv_{uuid.uuid4().hex[:8]}",
            operation=op,
            nirnay_card=card,
            farmer_context=farmer_ctx,
            evidence=farmer_evidence,
            explanation=explanation,
            daily_plan=daily_plan,
        )
