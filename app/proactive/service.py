"""Proactive Decision Engine Service for Phase 8.

Identifies meaningful, evidence-backed weather-driven operational events for
registered farmers and general users, performing deterministic change-detection,
deduplication, and decoupled notification delivery.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.analytics.et0 import calculate_et0
from app.analytics.water_balance import (
    calculate_crop_water_balance,
    evaluate_spray_window,
)
from app.contracts.location import LocationContext
from app.db.repositories.farmer import FarmerPlotRepository
from app.decision.alert_impact import AlertImpactEngine
from app.decision.engine import DeterministicDecisionEngine
from app.decision.evidence_builder import EvidenceBundleBuilder
from app.decision.models import (
    ConfidenceLevel,
    DecisionLocationQuery,
    DecisionOutcome,
    EvidenceBundle,
    ExposureState,
    SeverityLevel,
)
from app.farmer.analytics import (
    UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
    evaluate_crop_weather_risk,
    evaluate_harvest_window,
    evaluate_sowing_fieldwork,
)
from app.farmer.models import FieldWorkState, HarvestSuitabilityState
from app.proactive.deduplication import EventDeduplicationRegistry
from app.proactive.delivery import InMemoryNotificationDeliveryService, NotificationDeliveryService
from app.proactive.models import (
    EventDeliveryStatus,
    EventSeverity,
    UserProactivePreferences,
    WeatherDecisionEvent,
    WeatherDecisionEventType,
)

logger = logging.getLogger(__name__)

CROP_STAGE_DISCLAIMER = "Default crop stage assumed; adjust for local maturity."


class ProactiveDecisionService:
    """Core Phase 8 service that evaluates proactive weather decisions and delivers them."""

    def __init__(
        self,
        evidence_builder: EvidenceBundleBuilder,
        decision_engine: DeterministicDecisionEngine,
        farmer_repo: Optional[FarmerPlotRepository] = None,
        dedup_registry: Optional[EventDeduplicationRegistry] = None,
        delivery_service: Optional[NotificationDeliveryService] = None,
        explanation_bridge: Optional[Any] = None,
    ):
        self.evidence_builder = evidence_builder
        self.decision_engine = decision_engine
        self.farmer_repo = farmer_repo
        self.dedup_registry = dedup_registry or EventDeduplicationRegistry()
        self.delivery_service = delivery_service or InMemoryNotificationDeliveryService()
        self.explanation_bridge = explanation_bridge
        self.alert_impact_engine = AlertImpactEngine()

    # ========================================================================
    # 1. Registered Farmer Plot Evaluation
    # ========================================================================

    async def evaluate_farmer_plot(
        self,
        plot: Any,
        preferences: Optional[UserProactivePreferences] = None,
        force_reevaluate: bool = False,
    ) -> List[WeatherDecisionEvent]:
        """Evaluates operational weather decisions across all operations for a registered farmer plot."""
        events: List[WeatherDecisionEvent] = []
        user_id = plot.user_id
        crop_name = plot.crop_name or "Field Crop"
        plot_name = plot.plot_name or "Registered Plot"

        # Check user preferences if supplied
        if preferences and not preferences.enabled:
            logger.info("ProactiveService: Proactive alerts disabled by user preferences for %s", user_id)
            return []

        # 1. Build verified meteorological evidence bundle
        location_query = DecisionLocationQuery(
            name=plot_name,
            latitude=float(plot.centroid_lat),
            longitude=float(plot.centroid_lon),
        )
        evidence = await self.evidence_builder.build_bundle(
            location_query=location_query,
            domain="farmer",
            context={"crop_name": crop_name},
        )

        now_utc = datetime.now(timezone.utc)
        valid_until_iso = (now_utc + timedelta(hours=12)).isoformat()

        # --------------------------------------------------------------------
        # Evaluation A: Official Severe Weather Warnings
        # --------------------------------------------------------------------
        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=now_utc.isoformat(),
        )

        if primary_alert and primary_alert.is_active and primary_alert.exposure_state == ExposureState.INSIDE:
            sev_map = {
                "Red": EventSeverity.CRITICAL,
                "Orange": EventSeverity.HIGH,
                "Yellow": EventSeverity.MODERATE,
            }
            alert_sev = sev_map.get(primary_alert.warning_level, EventSeverity.MODERATE)
            verdict = DecisionOutcome.NO_GO if primary_alert.warning_level.upper() in ("RED", "ORANGE") else DecisionOutcome.PROCEED_WITH_CAUTION

            dedup_k = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=str(plot.plot_id),
                event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
                operation="farm_safety",
                verdict=verdict,
                severity=alert_sev,
                hazard_identifier=primary_alert.alert_id,
            )

            event = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                plot_id=str(plot.plot_id),
                plot_name=plot_name,
                crop_name=crop_name,
                event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
                severity=alert_sev,
                location={
                    "name": plot_name,
                    "latitude": float(plot.centroid_lat),
                    "longitude": float(plot.centroid_lon),
                    "district": evidence.location.district,
                    "state": evidence.location.state,
                },
                operation="farm_safety",
                verdict=verdict,
                recommended_action=primary_alert.prescribed_action,
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"official_source": primary_alert.issuing_office, "status": "verified"},
                why=[
                    f"Official {primary_alert.warning_level} Alert in effect: {primary_alert.hazard_type}.",
                    f"Plot location confirmed INSIDE warning perimeter.",
                    f"Composite operational impact score: {primary_alert.composite_impact_score:.1f}/10.0.",
                ],
                evidence={
                    "alert_id": primary_alert.alert_id,
                    "warning_level": primary_alert.warning_level,
                    "hazard_type": primary_alert.hazard_type,
                    "exposure_state": primary_alert.exposure_state.value,
                    "composite_impact_score": primary_alert.composite_impact_score,
                },
                provenance={
                    "issuing_office": primary_alert.issuing_office,
                    "retrieved_at": now_utc.isoformat(),
                },
                valid_from=now_utc.isoformat(),
                valid_until=primary_alert.expires_time_iso or valid_until_iso,
                dedup_key=dedup_k,
            )

            should_emit, reason = self.dedup_registry.should_emit_event(event, force=force_reevaluate)
            if should_emit:
                self.dedup_registry.record_event(event)
                await self.delivery_service.deliver(event)
                events.append(event)

        # If user prefers official warnings only, skip operational advisories
        if preferences and preferences.official_warnings_only:
            return events

        # --------------------------------------------------------------------
        # Evaluation B: Chemical Spraying Window Suitability
        # --------------------------------------------------------------------
        spray_card = self.decision_engine._evaluate_farmer_spray(
            decision_id=f"dec_spray_{plot.plot_id}",
            evidence=evidence,
            question=f"Should I spray my {crop_name} field?",
            context={"crop_name": crop_name},
        )

        sev_spray = EventSeverity.HIGH if spray_card.verdict == DecisionOutcome.NO_GO else (
            EventSeverity.MODERATE if spray_card.verdict == DecisionOutcome.POSTPONE else EventSeverity.LOW
        )

        dedup_spray = self.dedup_registry.generate_dedup_key(
            user_id=user_id,
            target_entity=str(plot.plot_id),
            event_type=WeatherDecisionEventType.SPRAY_WINDOW_CHANGE,
            operation="chemical_spraying",
            verdict=spray_card.verdict,
            severity=sev_spray,
            hazard_identifier=f"spray_{spray_card.verdict.value}",
        )

        spray_event = WeatherDecisionEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            plot_id=str(plot.plot_id),
            plot_name=plot_name,
            crop_name=crop_name,
            event_type=WeatherDecisionEventType.SPRAY_WINDOW_CHANGE,
            severity=sev_spray,
            location={
                "name": plot_name,
                "latitude": float(plot.centroid_lat),
                "longitude": float(plot.centroid_lon),
                "district": evidence.location.district,
                "state": evidence.location.state,
            },
            operation="chemical_spraying",
            verdict=spray_card.verdict,
            recommended_action=spray_card.recommended_action,
            action_window=spray_card.action_window.model_dump() if hasattr(spray_card.action_window, "model_dump") else spray_card.action_window,
            confidence=spray_card.confidence,
            uncertainty=spray_card.uncertainty,
            why=spray_card.why,
            evidence=spray_card.evidence,
            provenance={
                "engine": "DeterministicDecisionEngine",
                "rules": "Wind <= 15 km/h, Rain chance <= 30%, 4h Rain == 0 mm",
            },
            valid_from=now_utc.isoformat(),
            valid_until=valid_until_iso,
            dedup_key=dedup_spray,
        )

        should_emit_spray, _ = self.dedup_registry.should_emit_event(spray_event, force=force_reevaluate)
        if should_emit_spray:
            self.dedup_registry.record_event(spray_event)
            await self.delivery_service.deliver(spray_event)
            events.append(spray_event)

        # --------------------------------------------------------------------
        # Evaluation C: Irrigation Water Balance Decision
        # --------------------------------------------------------------------
        forecast_rain_48h = float(evidence.forecast.get("rainfall_total_mm", 0.0))
        et0_res = calculate_et0(
            temp_c=float(evidence.observations.get("temperature_c", 28.0)),
            relative_humidity_pct=float(evidence.observations.get("relative_humidity_pct", 60.0)),
            wind_speed_2m_ms=2.0,
            solar_radiation_mj_m2_day=20.0,
            elevation_m=100.0,
        )
        wb_res = calculate_crop_water_balance(
            et0_mm_day=et0_res.et0_mm_day,
            crop_coefficient_kc=1.15,
            precipitation_mm=0.0,
            forecast_rain_48h_mm=forecast_rain_48h,
        )

        # Determine if irrigation advisory represents an actionable state
        irr_verdict = DecisionOutcome.NO_GO if wb_res.advisory_action.value == "POSTPONE" else (
            DecisionOutcome.GO if wb_res.advisory_action.value == "IRRIGATE" else DecisionOutcome.PROCEED_WITH_CAUTION
        )
        irr_sev = EventSeverity.MODERATE if irr_verdict == DecisionOutcome.GO else EventSeverity.LOW

        dedup_irr = self.dedup_registry.generate_dedup_key(
            user_id=user_id,
            target_entity=str(plot.plot_id),
            event_type=WeatherDecisionEventType.IRRIGATION_CHANGE,
            operation="irrigation",
            verdict=irr_verdict,
            severity=irr_sev,
            hazard_identifier=f"irrigation_{irr_verdict.value}",
        )

        irr_event = WeatherDecisionEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            plot_id=str(plot.plot_id),
            plot_name=plot_name,
            crop_name=crop_name,
            event_type=WeatherDecisionEventType.IRRIGATION_CHANGE,
            severity=irr_sev,
            location={
                "name": plot_name,
                "latitude": float(plot.centroid_lat),
                "longitude": float(plot.centroid_lon),
                "district": evidence.location.district,
                "state": evidence.location.state,
            },
            operation="irrigation",
            verdict=irr_verdict,
            recommended_action=wb_res.operational_guidance,
            confidence=ConfidenceLevel.HIGH,
            uncertainty={
                "soil_moisture_disclaimer": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
                "crop_stage_disclaimer": CROP_STAGE_DISCLAIMER,
            },
            why=[
                f"Crop daily water demand (ETc): {wb_res.daily_balance.etc_mm:.1f} mm.",
                f"Forecast 48h rainfall: {forecast_rain_48h:.1f} mm.",
                UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
                CROP_STAGE_DISCLAIMER,
            ],
            evidence={
                "reference_et0_mm_day": et0_res.et0_mm_day,
                "forecast_rain_48h_mm": forecast_rain_48h,
                "net_deficit_mm": wb_res.daily_balance.net_deficit_mm,
                "action": wb_res.advisory_action.value,
            },
            provenance={
                "method": "FAO-56 Penman-Monteith (Deterministic Engine)",
                "soil_water_balance": "Allen et al. (1998)",
            },
            valid_from=now_utc.isoformat(),
            valid_until=valid_until_iso,
            dedup_key=dedup_irr,
        )

        should_emit_irr, _ = self.dedup_registry.should_emit_event(irr_event, force=force_reevaluate)
        if should_emit_irr:
            self.dedup_registry.record_event(irr_event)
            await self.delivery_service.deliver(irr_event)
            events.append(irr_event)

        # --------------------------------------------------------------------
        # Evaluation D: Harvest Window Suitability
        # --------------------------------------------------------------------
        forecast_rain_24h = float(evidence.forecast.get("rainfall_24h_mm", evidence.forecast.get("rainfall_total_mm", 0.0)))
        hourly_forecast = evidence.forecast.get("hourly_forecast", evidence.forecast.get("hourly", []))
        harvest_res = evaluate_harvest_window(
            hourly_forecast=hourly_forecast,
            current_temp_c=float(evidence.observations.get("temperature_c", 28.0)),
            current_humidity_pct=float(evidence.observations.get("relative_humidity_pct", 60.0)),
            current_wind_kmh=float(evidence.observations.get("wind_speed_kmh", 10.0)),
            forecast_rain_24h_mm=forecast_rain_24h,
            crop_name=crop_name,
            active_alerts=evidence.alerts,
        )
        if not harvest_res.get("is_suitable", True) or harvest_res.get("state") == HarvestSuitabilityState.MARGINAL:
            harvest_verdict = (
                DecisionOutcome.NO_GO
                if harvest_res.get("state") == HarvestSuitabilityState.UNSUITABLE
                else DecisionOutcome.POSTPONE
            )
            harvest_sev = EventSeverity.HIGH if harvest_verdict == DecisionOutcome.NO_GO else EventSeverity.MODERATE
            dedup_harvest = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=str(plot.plot_id),
                event_type=WeatherDecisionEventType.HARVEST_WINDOW_CHANGE,
                operation="crop_harvesting",
                verdict=harvest_verdict,
                severity=harvest_sev,
                hazard_identifier=f"harvest_{harvest_verdict.value}",
            )
            harvest_event = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                plot_id=str(plot.plot_id),
                plot_name=plot_name,
                crop_name=crop_name,
                event_type=WeatherDecisionEventType.HARVEST_WINDOW_CHANGE,
                severity=harvest_sev,
                location={
                    "name": plot_name,
                    "latitude": float(plot.centroid_lat),
                    "longitude": float(plot.centroid_lon),
                    "district": evidence.location.district,
                    "state": evidence.location.state,
                },
                operation="crop_harvesting",
                verdict=harvest_verdict,
                recommended_action=harvest_res.get("recommended_action", f"Postpone harvesting {crop_name}."),
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"note": harvest_res.get("uncertainty", "Generic weather constraints applied.")},
                why=harvest_res.get("blocking_factors", [f"Harvesting unsuitable due to forecast weather."]),
                evidence={"forecast_rain_24h_mm": forecast_rain_24h, "state": str(harvest_res.get("state"))},
                provenance={"engine": "evaluate_harvest_window", "rules": "Generic Operational Weather Constraints"},
                valid_from=now_utc.isoformat(),
                valid_until=valid_until_iso,
                dedup_key=dedup_harvest,
            )
            should_emit_h, _ = self.dedup_registry.should_emit_event(harvest_event, force=force_reevaluate)
            if should_emit_h:
                self.dedup_registry.record_event(harvest_event)
                await self.delivery_service.deliver(harvest_event)
                events.append(harvest_event)

        # --------------------------------------------------------------------
        # Evaluation E: Sowing & Field-Work Suitability
        # --------------------------------------------------------------------
        fieldwork_res = evaluate_sowing_fieldwork(
            temp_max_c=float(evidence.forecast.get("temperature_max_c", evidence.observations.get("temperature_c", 30.0))),
            temp_min_c=float(evidence.forecast.get("temperature_min_c", 20.0)),
            rainfall_24h_mm=forecast_rain_24h,
            forecast_rain_48h_mm=forecast_rain_48h,
            wind_speed_kmh=float(evidence.observations.get("wind_speed_kmh", 12.0)),
            active_alerts=evidence.alerts,
            crop_name=crop_name,
        )
        if not fieldwork_res.get("is_favorable", True):
            fw_verdict = (
                DecisionOutcome.NO_GO
                if fieldwork_res.get("state") == FieldWorkState.UNFAVORABLE
                else DecisionOutcome.POSTPONE
            )
            fw_sev = EventSeverity.HIGH if fw_verdict == DecisionOutcome.NO_GO else EventSeverity.MODERATE
            dedup_fw = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=str(plot.plot_id),
                event_type=WeatherDecisionEventType.FIELD_WORK_RISK,
                operation="field_work",
                verdict=fw_verdict,
                severity=fw_sev,
                hazard_identifier=f"fieldwork_{fw_verdict.value}",
            )
            fw_event = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                plot_id=str(plot.plot_id),
                plot_name=plot_name,
                crop_name=crop_name,
                event_type=WeatherDecisionEventType.FIELD_WORK_RISK,
                severity=fw_sev,
                location={
                    "name": plot_name,
                    "latitude": float(plot.centroid_lat),
                    "longitude": float(plot.centroid_lon),
                    "district": evidence.location.district,
                    "state": evidence.location.state,
                },
                operation="field_work",
                verdict=fw_verdict,
                recommended_action=fieldwork_res.get("recommended_action", f"Postpone field operations for {crop_name}."),
                confidence=ConfidenceLevel.HIGH,
                uncertainty={
                    "soil_moisture_disclaimer": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
                    "crop_stage_disclaimer": CROP_STAGE_DISCLAIMER,
                },
                why=[
                    fieldwork_res.get("reason", "Field work unsuitable due to soil/weather conditions."),
                    UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
                ],
                evidence={"forecast_rain_48h_mm": forecast_rain_48h, "state": str(fieldwork_res.get("state"))},
                provenance={"engine": "evaluate_sowing_fieldwork", "rules": "Generic Soil Workability & Agronomic Weather"},
                valid_from=now_utc.isoformat(),
                valid_until=valid_until_iso,
                dedup_key=dedup_fw,
            )
            should_emit_fw, _ = self.dedup_registry.should_emit_event(fw_event, force=force_reevaluate)
            if should_emit_fw:
                self.dedup_registry.record_event(fw_event)
                await self.delivery_service.deliver(fw_event)
                events.append(fw_event)

        return events

    async def evaluate_farmer_events(
        self,
        user_id: str,
        preferences: Optional[UserProactivePreferences] = None,
        force_reevaluate: bool = False,
    ) -> List[WeatherDecisionEvent]:
        """Scans all registered plots for a farmer and generates proactive decisions."""
        if not self.farmer_repo:
            logger.warning("ProactiveService: FarmerPlotRepository not configured.")
            return []

        plots = await self.farmer_repo.get_by_user(user_id)
        logger.info("ProactiveService: Evaluating proactive events for farmer %s across %d plots", user_id, len(plots))

        all_events: List[WeatherDecisionEvent] = []
        for plot in plots:
            plot_events = await self.evaluate_farmer_plot(
                plot=plot,
                preferences=preferences,
                force_reevaluate=force_reevaluate,
            )
            all_events.extend(plot_events)

        return all_events

    # ========================================================================
    # 2. General Coordinate / User Location Evaluation
    # ========================================================================

    async def evaluate_location_events(
        self,
        latitude: float,
        longitude: float,
        location_name: str = "Current Location",
        district: Optional[str] = None,
        state: Optional[str] = None,
        user_id: str = "guest_user",
        preferences: Optional[UserProactivePreferences] = None,
        force_reevaluate: bool = False,
    ) -> List[WeatherDecisionEvent]:
        """Evaluates general meteorological risks (heat, heavy rain, wind, official alerts) for a coordinate location."""
        events: List[WeatherDecisionEvent] = []
        now_utc = datetime.now(timezone.utc)
        valid_until_iso = (now_utc + timedelta(hours=12)).isoformat()

        # Build verified evidence
        loc_query = DecisionLocationQuery(
            name=location_name,
            latitude=latitude,
            longitude=longitude,
        )
        evidence = await self.evidence_builder.build_bundle(
            location_query=loc_query,
            domain="general",
        )

        # --------------------------------------------------------------------
        # Hazard Check 1: Official Alerts
        # --------------------------------------------------------------------
        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=now_utc.isoformat(),
        )

        if primary_alert and primary_alert.is_active and primary_alert.exposure_state == ExposureState.INSIDE:
            sev_map = {
                "Red": EventSeverity.CRITICAL,
                "Orange": EventSeverity.HIGH,
                "Yellow": EventSeverity.MODERATE,
            }
            alert_sev = sev_map.get(primary_alert.warning_level, EventSeverity.MODERATE)
            verdict = DecisionOutcome.NO_GO if primary_alert.warning_level.upper() in ("RED", "ORANGE") else DecisionOutcome.PROCEED_WITH_CAUTION

            dedup_alert = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=f"{latitude:.3f}_{longitude:.3f}",
                event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
                operation="general_safety",
                verdict=verdict,
                severity=alert_sev,
                hazard_identifier=primary_alert.alert_id,
            )

            alert_evt = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
                severity=alert_sev,
                location={
                    "name": location_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "district": evidence.location.district or district,
                    "state": evidence.location.state or state,
                },
                operation="general_safety",
                verdict=verdict,
                recommended_action=primary_alert.prescribed_action,
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"official_source": primary_alert.issuing_office},
                why=[
                    f"Official {primary_alert.warning_level} Warning in effect: {primary_alert.hazard_type}.",
                    f"Spatial containment verified as INSIDE warning zone.",
                ],
                evidence={
                    "alert_id": primary_alert.alert_id,
                    "warning_level": primary_alert.warning_level,
                    "hazard_type": primary_alert.hazard_type,
                },
                provenance={"issuing_office": primary_alert.issuing_office},
                valid_from=now_utc.isoformat(),
                valid_until=primary_alert.expires_time_iso or valid_until_iso,
                dedup_key=dedup_alert,
            )

            should_emit, _ = self.dedup_registry.should_emit_event(alert_evt, force=force_reevaluate)
            if should_emit:
                self.dedup_registry.record_event(alert_evt)
                await self.delivery_service.deliver(alert_evt)
                events.append(alert_evt)

        # --------------------------------------------------------------------
        # Hazard Check 2: Heavy Rainfall Approaching
        # --------------------------------------------------------------------
        rain_total_mm = float(evidence.forecast.get("rainfall_total_mm", 0.0))
        rain_prob = float(evidence.forecast.get("rain_probability_pct", 0.0))

        if rain_total_mm >= 35.5 or (rain_prob >= 75.0 and rain_total_mm >= 20.0):
            rain_sev = EventSeverity.HIGH if rain_total_mm >= 64.5 else EventSeverity.MODERATE
            dedup_rain = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=f"{latitude:.3f}_{longitude:.3f}",
                event_type=WeatherDecisionEventType.HEAVY_RAIN_RISK,
                operation="outdoor_travel",
                verdict=DecisionOutcome.POSTPONE if rain_sev == EventSeverity.HIGH else DecisionOutcome.PROCEED_WITH_CAUTION,
                severity=rain_sev,
                hazard_identifier=f"rain_{rain_total_mm:.0f}mm",
            )

            rain_evt = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                event_type=WeatherDecisionEventType.HEAVY_RAIN_RISK,
                severity=rain_sev,
                location={
                    "name": location_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "district": evidence.location.district or district,
                    "state": evidence.location.state or state,
                },
                operation="outdoor_travel",
                verdict=DecisionOutcome.POSTPONE if rain_sev == EventSeverity.HIGH else DecisionOutcome.PROCEED_WITH_CAUTION,
                recommended_action="Postpone non-essential travel. Expect waterlogging in low-lying roads and localized drainage backup.",
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"forecast_horizon_hours": 24},
                why=[
                    f"Forecast cumulative precipitation of {rain_total_mm:.1f} mm exceeds safety thresholds.",
                    f"Rain probability is {rain_prob:.0f}%.",
                ],
                evidence={"forecast_rain_mm": rain_total_mm, "rain_prob_pct": rain_prob},
                provenance={"provider": "Open-Meteo & NOAA GFS 0.25°"},
                valid_from=now_utc.isoformat(),
                valid_until=valid_until_iso,
                dedup_key=dedup_rain,
            )

            should_emit_rain, _ = self.dedup_registry.should_emit_event(rain_evt, force=force_reevaluate)
            if should_emit_rain:
                self.dedup_registry.record_event(rain_evt)
                await self.delivery_service.deliver(rain_evt)
                events.append(rain_evt)

        # --------------------------------------------------------------------
        # Hazard Check 3: Severe Heat Hazard
        # --------------------------------------------------------------------
        temp_max_c = float(evidence.forecast.get("temperature_c") or evidence.observations.get("temperature_c", 30.0))
        if temp_max_c >= 40.0:
            heat_sev = EventSeverity.HIGH if temp_max_c >= 44.0 else EventSeverity.MODERATE
            dedup_heat = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=f"{latitude:.3f}_{longitude:.3f}",
                event_type=WeatherDecisionEventType.HEAT_RISK,
                operation="outdoor_exposure",
                verdict=DecisionOutcome.POSTPONE if heat_sev == EventSeverity.HIGH else DecisionOutcome.PROCEED_WITH_CAUTION,
                severity=heat_sev,
                hazard_identifier=f"heat_{temp_max_c:.0f}c",
            )

            heat_evt = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                event_type=WeatherDecisionEventType.HEAT_RISK,
                severity=heat_sev,
                location={
                    "name": location_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "district": evidence.location.district or district,
                    "state": evidence.location.state or state,
                },
                operation="outdoor_exposure",
                verdict=DecisionOutcome.POSTPONE if heat_sev == EventSeverity.HIGH else DecisionOutcome.PROCEED_WITH_CAUTION,
                recommended_action="Avoid direct sun exposure between 12:00 and 15:30 IST. Maintain frequent hydration and protect livestock.",
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"thermal_stress_metric": "ambient_air_temperature"},
                why=[
                    f"Forecast maximum temperature of {temp_max_c:.1f}°C breaches regional heat threshold (40.0°C).",
                    "Elevated risk of heat cramps, exhaustion, and dehydration.",
                ],
                evidence={"temperature_c": temp_max_c},
                provenance={"provider": "Open-Meteo Surface Reanalysis"},
                valid_from=now_utc.isoformat(),
                valid_until=valid_until_iso,
                dedup_key=dedup_heat,
            )

            should_emit_heat, _ = self.dedup_registry.should_emit_event(heat_evt, force=force_reevaluate)
            if should_emit_heat:
                self.dedup_registry.record_event(heat_evt)
                await self.delivery_service.deliver(heat_evt)
                events.append(heat_evt)

        # --------------------------------------------------------------------
        # Hazard Check 4: High Wind Squall Risk
        # --------------------------------------------------------------------
        wind_speed_kmh = float(evidence.forecast.get("wind_speed_kmh") or evidence.observations.get("wind_speed_kmh", 10.0))
        if wind_speed_kmh >= 35.0:
            wind_sev = EventSeverity.HIGH if wind_speed_kmh >= 50.0 else EventSeverity.MODERATE
            dedup_wind = self.dedup_registry.generate_dedup_key(
                user_id=user_id,
                target_entity=f"{latitude:.3f}_{longitude:.3f}",
                event_type=WeatherDecisionEventType.HIGH_WIND_RISK,
                operation="outdoor_structures",
                verdict=DecisionOutcome.NO_GO if wind_sev == EventSeverity.HIGH else DecisionOutcome.PROCEED_WITH_CAUTION,
                severity=wind_sev,
                hazard_identifier=f"wind_{wind_speed_kmh:.0f}kmh",
            )

            wind_evt = WeatherDecisionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                event_type=WeatherDecisionEventType.HIGH_WIND_RISK,
                severity=wind_sev,
                location={
                    "name": location_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "district": evidence.location.district or district,
                    "state": evidence.location.state or state,
                },
                operation="outdoor_structures",
                verdict=DecisionOutcome.NO_GO if wind_sev == EventSeverity.HIGH else DecisionOutcome.PROCEED_WITH_CAUTION,
                recommended_action="Secure loose roofing sheets, solar panels, and outdoor equipment against squally winds.",
                confidence=ConfidenceLevel.HIGH,
                uncertainty={"wind_measurement_height_m": 10},
                why=[
                    f"Sustained wind speeds ({wind_speed_kmh:.1f} km/h) exceed safe threshold (35.0 km/h).",
                    "Elevated risk of projectile debris and structural damage.",
                ],
                evidence={"wind_speed_kmh": wind_speed_kmh},
                provenance={"provider": "NOAA GFS 0.25° NWP"},
                valid_from=now_utc.isoformat(),
                valid_until=valid_until_iso,
                dedup_key=dedup_wind,
            )

            should_emit_wind, _ = self.dedup_registry.should_emit_event(wind_evt, force=force_reevaluate)
            if should_emit_wind:
                self.dedup_registry.record_event(wind_evt)
                await self.delivery_service.deliver(wind_evt)
                events.append(wind_evt)

        return events

    # ========================================================================
    # 3. Lifecycle Queries & User Actions
    # ========================================================================

    def get_user_events(self, user_id: str) -> List[WeatherDecisionEvent]:
        """Returns all proactive events logged for a specific user."""
        return self.dedup_registry.get_events_for_user(user_id)

    def acknowledge_event(self, event_id: str) -> bool:
        """Marks an event as acknowledged by the user."""
        return self.dedup_registry.acknowledge_event(event_id)

    async def _attach_explanation(self, event: WeatherDecisionEvent, language: str = "en") -> WeatherDecisionEvent:
        """Optionally generates explanatory text via LLM bridge while strictly preserving deterministic verdict & severity.
        
        The LLM is strictly explanation-only: it can NEVER mutate event.verdict, event.severity,
        event.recommended_action, event.why, or event.evidence.
        """
        if not self.explanation_bridge:
            return event
        try:
            explanation = await self.explanation_bridge.explain_decision(
                verdict=event.verdict.value,
                operation=event.operation or "general",
                recommended_action=event.recommended_action,
                why=event.why,
                language=language,
            )
            if explanation:
                event.explanation = str(explanation)
        except Exception as exc:
            logger.warning("ProactiveService: Explanation generation skipped/failed: %s", exc)
        return event
