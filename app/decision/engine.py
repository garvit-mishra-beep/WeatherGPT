"""Deterministic Decision Engine for Vayubodhak (USP Phase 1, 2 & 3).

Evaluates verified EvidenceBundles against physical, agronomic, spatial exposure,
and official alert constraint rules to produce canonical NirnayCards and auditable
EvidenceLedgers.

PIPELINE:
Official Alert → Hazard → Affected Area → Verified Exposure → Risk / Potential Impact → Decision → NirnayCard → Action

ZERO LLM DEPENDENCY:
Functions entirely via verified Python calculation engines and deterministic logic
without requiring Ollama, Gemma, or external AI endpoints.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.analytics.water_balance import evaluate_spray_window
from app.decision.action_window import ActionWindowEngine
from app.decision.alert_impact import AlertImpactEngine
from app.decision.models import (
    ActionWindow,
    ConfidenceLevel,
    DecisionOutcome,
    EvidenceBundle,
    EvidenceLedger,
    ExposureState,
    LedgerRuleEvaluation,
    NirnayCard,
    SeverityLevel,
)
from app.farmer.analytics import (
    UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
    evaluate_crop_weather_risk,
    evaluate_harvest_window,
    evaluate_sowing_fieldwork,
    generate_daily_farm_plan,
    get_crop_coefficient,
)
from app.farmer.models import (
    CropWeatherRiskTier,
    DailyFarmPlan,
    FieldWorkState,
    HarvestSuitabilityState,
)

logger = logging.getLogger(__name__)


class DeterministicDecisionEngine:
    """Executes rule-based operational decision intelligence over EvidenceBundles."""

    def __init__(
        self,
        action_window_engine: Optional[ActionWindowEngine] = None,
        alert_impact_engine: Optional[AlertImpactEngine] = None,
    ) -> None:
        self.action_window_engine = action_window_engine or ActionWindowEngine()
        self.alert_impact_engine = alert_impact_engine or AlertImpactEngine()

    def evaluate_decision(
        self,
        evidence: EvidenceBundle,
        question: str,
        domain: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> NirnayCard:
        """Evaluates an operational question against the EvidenceBundle deterministically."""
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        q_lower = question.lower().strip()
        ctx = context or {}

        # Determine decision category
        is_spray = any(k in q_lower for k in ["spray", "pesticide", "fertilizer", "छिड़काव", "कीटनाशक", "दवा"]) or (
            domain == "farmer" and "spray" in q_lower
        )
        is_irrigation = any(k in q_lower for k in ["irrigate", "irrigation", "water balance", "सिंचाई", "पानी"])
        is_harvest = any(k in q_lower for k in ["harvest", "कटाई", "फसल काटना"])
        is_sowing_fieldwork = any(k in q_lower for k in ["sow", "sowing", "field work", "fieldwork", "बुवाई", "खेत का काम", "जोताई", "tillage"])
        is_daily_plan = any(k in q_lower for k in ["farm plan", "what should i do on my farm", "today's plan", "daily plan", "आज क्या करें", "खेत में क्या करें"])
        is_crop_risk = any(k in q_lower for k in ["crop risk", "weather risk", "heat affect", "dry spell", "फसल जोखिम", "गर्मी का असर", "सूखा"])

        if is_spray:
            return self._evaluate_farmer_spray(decision_id, evidence, question, ctx)
        elif is_irrigation:
            return self._evaluate_farmer_irrigation(decision_id, evidence, question, ctx)
        elif is_harvest:
            return self._evaluate_farmer_harvest(decision_id, evidence, question, ctx)
        elif is_sowing_fieldwork:
            return self._evaluate_farmer_sowing_fieldwork(decision_id, evidence, question, ctx)
        elif is_crop_risk:
            return self._evaluate_farmer_crop_risk(decision_id, evidence, question, ctx)
        elif is_daily_plan:
            return self._evaluate_farmer_daily_plan(decision_id, evidence, question, ctx)
        else:
            return self._evaluate_general_operational(decision_id, evidence, question, ctx)

    # ========================================================================
    # 1. Farmer Spray Decision ("Should I spray my cotton tonight?")
    # ========================================================================

    def _evaluate_farmer_spray(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
    ) -> NirnayCard:
        """Evaluates chemical spraying suitability under verified alert, exposure & weather conditions."""
        crop_name = context.get("crop_name") or ("Cotton" if "cotton" in question.lower() or "कपास" in question.lower() else "Field Crop")

        # 1. Extract physical variables from EvidenceBundle
        wind_speed_kmh = float(
            evidence.observations.get("wind_speed_kmh")
            or evidence.forecast.get("wind_speed_kmh", 12.0)
        )
        rain_prob_pct = float(
            evidence.forecast.get("rain_probability_pct", 0.0)
        )
        rainfall_4h_mm = float(
            evidence.forecast.get("rainfall_total_mm", 0.0)
        )

        # 2. Evaluate Official Alerts via AlertImpactEngine (USP Phase 3)
        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=evidence.requested_time,
        )

        # 3. Execute deterministic spray calculation from existing Analytics Engine
        spray_output = evaluate_spray_window(
            wind_speed_kmh=wind_speed_kmh,
            rain_probability_pct=rain_prob_pct,
            rain_4h_post_spray_mm=rainfall_4h_mm,
        )

        # 4. Formulate Deterministic Physical Rules for Ledger
        rule_wind = LedgerRuleEvaluation(
            rule_name="wind_drift_safety_threshold",
            threshold=15.0,
            observed_value=wind_speed_kmh,
            unit="km/h",
            operator="<=",
            satisfied=spray_output.wind_suitable,
            rationale="Wind speeds > 15 km/h cause droplet drift away from target foliage and into non-target areas.",
        )
        rule_rain_prob = LedgerRuleEvaluation(
            rule_name="precipitation_probability_threshold",
            threshold=30.0,
            observed_value=rain_prob_pct,
            unit="%",
            operator="<=",
            satisfied=spray_output.rain_probability_suitable,
            rationale="Precipitation probability > 30% indicates elevated risk of convective showers.",
        )
        rule_washoff = LedgerRuleEvaluation(
            rule_name="post_spray_rain_washoff_threshold",
            threshold=0.0,
            observed_value=rainfall_4h_mm,
            unit="mm",
            operator="==",
            satisfied=spray_output.rain_washoff_suitable,
            rationale="Rainfall occurring within 4 hours post-application dissolves and washes away active chemical residue.",
        )
        ledger_rules: List[LedgerRuleEvaluation] = [rule_wind, rule_rain_prob, rule_washoff]

        # Scan forward action windows (USP Phase 2 & 3: Alert-aware)
        forward_win = self.action_window_engine.find_action_window(
            evidence=evidence,
            action_type="cotton_spray",
            context=context,
        )

        why_bullets: List[str] = []
        alternatives: List[str] = []

        # 5. Alert Presence & Spatial Exposure Evaluation
        has_red_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_red_outside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.OUTSIDE
            and primary_alert.is_active
        )
        has_orange_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() in ("ORANGE", "AMBER")
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_yellow_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "YELLOW"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )

        if primary_alert:
            rule_alert = LedgerRuleEvaluation(
                rule_name="official_severe_weather_clearance",
                threshold=f"Preserve {primary_alert.warning_level} Warning",
                observed_value=f"{primary_alert.warning_level} ({primary_alert.hazard_type})",
                unit="official_severity",
                operator="==",
                satisfied=not (has_red_inside or has_orange_inside),
                rationale=f"Official {primary_alert.issuing_office} {primary_alert.warning_level} warning severity is strictly immutable.",
            )
            rule_exposure = LedgerRuleEvaluation(
                rule_name="spatial_exposure_verification",
                threshold="Location containment in alert geometry/district",
                observed_value=f"{primary_alert.exposure_state.value} (Overlap: {primary_alert.exposed_area_pct:.0f}%)",
                unit="exposure_state",
                operator="in [INSIDE, BUFFER, OUTSIDE]",
                satisfied=True,
                rationale=f"Spatial evaluation confirmed {evidence.location.district or evidence.location.name} status as {primary_alert.exposure_state.value}.",
            )
            rule_impact = LedgerRuleEvaluation(
                rule_name="composite_impact_calculation",
                threshold="H x E x V formula (0.50*H + 0.30*E + 0.20*V)",
                observed_value=f"Impact: {primary_alert.composite_impact_score:.1f}/10.0 (H={primary_alert.hazard_score:.1f}, E={primary_alert.exposure_score:.1f}, V={primary_alert.vulnerability_score:.1f})",
                unit="impact_score",
                operator="<=",
                satisfied=primary_alert.composite_impact_score < 7.0,
                rationale=f"Quantified deterministic operational impact as {primary_alert.risk_category} risk tier.",
            )
            ledger_rules.extend([rule_alert, rule_exposure, rule_impact])
        else:
            rule_alert = LedgerRuleEvaluation(
                rule_name="official_severe_weather_clearance",
                threshold="No Red/Orange Alert",
                observed_value="Clear",
                unit="alert_level",
                operator="not in [Red, Orange]",
                satisfied=True,
                rationale="No active official IMD severe weather warnings detected.",
            )
            ledger_rules.append(rule_alert)

        # 6. Synthesize Verdict, Action, and Explanations
        if has_red_inside:
            verdict = DecisionOutcome.NO_GO
            severity = SeverityLevel.CRITICAL
            recommended_action = primary_alert.prescribed_action
            why_bullets.append(
                f"Official {primary_alert.issuing_office} Red Alert ({primary_alert.event_title or primary_alert.hazard_type}) "
                f"is active for {evidence.location.district or evidence.location.name} until {primary_alert.expires_time_iso or 'further notice'}."
            )
            why_bullets.append(
                f"Spatial exposure verified as INSIDE warning perimeter (Exposure score: {primary_alert.exposure_score:.1f}/10.0, "
                f"{primary_alert.exposed_area_pct:.0f}% coverage)."
            )
            why_bullets.append(
                f"Composite operational impact score: {primary_alert.composite_impact_score:.1f}/10.0 ({primary_alert.risk_category.upper()} risk tier)."
            )
            why_bullets.append("Imminent threat to life and total destruction of exposed chemical applications.")
            action_window = forward_win
            impact = {
                "primary_risk": f"Catastrophic {primary_alert.hazard_type.lower()} hazard requiring immediate operational cessation.",
                "loss_potential": "Complete chemical wash-off and severe equipment/canopy damage.",
                "composite_impact_score": f"{primary_alert.composite_impact_score:.1f}/10.0",
                "risk_category": primary_alert.risk_category,
                "exposed_area_sqkm": primary_alert.exposed_area_sqkm,
                "exposure_state": primary_alert.exposure_state.value,
            }
            alternatives = [
                "Move farm personnel and equipment to secure reinforced indoor shelter immediately.",
                "Do not attempt chemical spraying until official expiration or cancellation of Red Alert.",
                "Monitor district disaster management authority (DDMA) emergency advisories.",
            ]

        elif has_orange_inside:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH
            recommended_action = primary_alert.prescribed_action
            why_bullets.append(
                f"Official {primary_alert.issuing_office} Orange Alert ('Be Prepared') for {primary_alert.hazard_type} "
                f"in effect for {evidence.location.district or evidence.location.name}."
            )
            why_bullets.append(
                f"Spatial exposure verified as INSIDE warning perimeter (Exposure: {primary_alert.exposure_score:.1f}/10.0)."
            )
            why_bullets.append(
                f"Composite operational impact score: {primary_alert.composite_impact_score:.1f}/10.0 ({primary_alert.risk_category.upper()} risk)."
            )
            if not spray_output.wind_suitable:
                why_bullets.append(f"Wind speed ({wind_speed_kmh:.1f} km/h) exceeds safe drift limit of 15.0 km/h.")
            if not spray_output.rain_washoff_suitable:
                why_bullets.append(f"Forecast rainfall ({rainfall_4h_mm:.1f} mm) will dissolve chemical residue.")

            action_window = forward_win
            impact = {
                "chemical_wastage": "High risk (estimated 70-90% chemical wash-off or drift loss).",
                "financial_loss": f"Estimated wasted input cost of ₹1,500 - ₹2,500 per acre on {crop_name}.",
                "composite_impact_score": f"{primary_alert.composite_impact_score:.1f}/10.0",
                "exposure_state": primary_alert.exposure_state.value,
            }
            alternatives = [
                "Postpone chemical spraying until official Orange Alert expires.",
                "Prepare spray equipment and monitor forward safe windows.",
            ]
            if forward_win.status == "available" and forward_win.best_window:
                bw = forward_win.best_window
                why_bullets.append(f"Safe operational window identified AFTER alert expiration: {bw.summary}.")
                alternatives.insert(0, f"Plan chemical application for recommended post-alert window: {bw.summary}.")

        elif has_red_outside:
            if spray_output.is_suitable:
                verdict = DecisionOutcome.PROCEED_WITH_CAUTION
                severity = SeverityLevel.MODERATE
                recommended_action = primary_alert.prescribed_action
                why_bullets.append(
                    f"Official Red Alert ({primary_alert.hazard_type}) active for {primary_alert.area_description or 'neighboring areas'}, "
                    f"but spatial verification confirms {evidence.location.district or evidence.location.name} is OUTSIDE the active warning boundary."
                )
                why_bullets.append(f"Local meteorological parameters are within safe operational limits (Wind: {wind_speed_kmh:.1f} km/h, Rain prob: {rain_prob_pct:.0f}%).")
                why_bullets.append(f"Local exposure score is 0.0/10.0 (Impact score: {primary_alert.composite_impact_score:.1f}/10.0).")
                action_window = forward_win
                impact = {
                    "efficiency": "Normal local pesticide retention feasible; heightened regional awareness required.",
                    "chemical_loss_risk": "Low local drift risk; monitor convective cloud movement from alerted boundary.",
                    "composite_impact_score": f"{primary_alert.composite_impact_score:.1f}/10.0",
                    "exposure_state": "OUTSIDE",
                }
                alternatives = [
                    "Proceed with spraying while continuously monitoring radar echoes from the neighboring warning zone.",
                    "Ensure immediate suspension protocol if localized squalls develop.",
                ]
            else:
                verdict = DecisionOutcome.POSTPONE
                severity = SeverityLevel.MODERATE
                recommended_action = f"Do NOT spray {crop_name} tonight due to adverse local conditions."
                if not spray_output.wind_suitable:
                    why_bullets.append(f"Local wind speed ({wind_speed_kmh:.1f} km/h) exceeds safe drift limit of 15.0 km/h.")
                if not spray_output.rain_probability_suitable:
                    why_bullets.append(f"Local rain probability ({rain_prob_pct:.0f}%) exceeds safety threshold.")
                why_bullets.append(f"Note: Regional Red Alert is active for {primary_alert.area_description}, though your location is outside the direct perimeter.")
                action_window = forward_win
                impact = {
                    "chemical_wastage": "High risk from local meteorological factors.",
                    "financial_loss": f"Estimated wasted input cost of ₹1,200 - ₹2,000 per acre on {crop_name}.",
                    "exposure_state": "OUTSIDE",
                }
                alternatives = [
                    "Postpone spraying and monitor tomorrow morning's forecast.",
                ]

        elif has_yellow_inside:
            if spray_output.is_suitable:
                verdict = DecisionOutcome.PROCEED_WITH_CAUTION
                severity = SeverityLevel.MODERATE
                recommended_action = primary_alert.prescribed_action
                why_bullets.append(
                    f"Official Yellow Alert ('Be Updated / Watch') active for {evidence.location.district or evidence.location.name} ({primary_alert.hazard_type})."
                )
                why_bullets.append(f"Surface wind speed ({wind_speed_kmh:.1f} km/h) and rain probability ({rain_prob_pct:.0f}%) satisfy baseline criteria.")
                why_bullets.append(f"Composite operational impact score: {primary_alert.composite_impact_score:.1f}/10.0 ({primary_alert.risk_category} risk).")
                action_window = forward_win
                impact = {
                    "efficiency": "Moderate efficiency; watch for sudden convective changes.",
                    "chemical_loss_risk": "Low to moderate.",
                    "composite_impact_score": f"{primary_alert.composite_impact_score:.1f}/10.0",
                    "exposure_state": primary_alert.exposure_state.value,
                }
                alternatives = [
                    "Maintain active weather watch during spraying.",
                    "Calibrate nozzles to coarse droplet size to minimize unexpected gust drift.",
                ]
            else:
                verdict = DecisionOutcome.POSTPONE
                severity = SeverityLevel.MODERATE
                recommended_action = f"Do NOT spray {crop_name} tonight. Postpone application until meteorological conditions stabilize."
                if not spray_output.wind_suitable:
                    why_bullets.append(f"Wind speed is {wind_speed_kmh:.1f} km/h, which exceeds the safe limit of 15.0 km/h.")
                if not spray_output.rain_probability_suitable:
                    why_bullets.append(f"Rain probability is {rain_prob_pct:.0f}%, which exceeds the 30% safety threshold.")
                why_bullets.append(f"Official Yellow Alert active for {evidence.location.district or evidence.location.name}.")
                action_window = forward_win
                impact = {
                    "chemical_wastage": "High risk of chemical wash-off or drift loss.",
                    "financial_loss": f"Estimated wasted input cost of ₹1,200 - ₹2,000 per acre on {crop_name}.",
                }
                alternatives = [
                    "Postpone spraying and monitor tomorrow morning's forecast.",
                ]

        else:
            # Baseline: Green alert or no alerts
            is_safe = spray_output.is_suitable
            if is_safe:
                verdict = DecisionOutcome.GO
                severity = SeverityLevel.LOW
                recommended_action = f"Proceed with chemical spraying on {crop_name} tonight during calm hours."
                why_bullets.append(f"Wind speed ({wind_speed_kmh:.1f} km/h) is below the 15.0 km/h drift threshold.")
                why_bullets.append(f"Rain probability ({rain_prob_pct:.0f}%) is below the 30% rain risk threshold.")
                why_bullets.append("Zero rainfall predicted in the 4-hour chemical absorption window.")
                why_bullets.append("No active official severe weather warnings for the district.")
                if forward_win.status == "available" and forward_win.best_window:
                    action_window = forward_win
                else:
                    action_window = {
                        "status": "available",
                        "recommended_start": "Tonight 19:00 IST",
                        "recommended_end": "Tonight 23:00 IST",
                        "rationale": "Surface winds and thermal turbulence typically subside after sunset.",
                    }
                impact = {
                    "efficiency": "High pesticide retention and target canopy coverage.",
                    "chemical_loss_risk": "Low (< 5% estimated drift loss).",
                    "crop_protection": f"Effective preventative coverage against target {crop_name} pests.",
                }
                alternatives = [
                    "If delayed tonight, re-evaluate tomorrow morning between 06:00 and 08:30 IST before surface heating increases wind speeds.",
                ]
                if forward_win.status == "available" and forward_win.best_window:
                    alternatives.append(f"Secondary forward window: {forward_win.best_window.summary}.")
            else:
                verdict = DecisionOutcome.POSTPONE
                severity = SeverityLevel.HIGH if rainfall_4h_mm >= 5.0 else SeverityLevel.MODERATE
                recommended_action = f"Do NOT spray {crop_name} tonight. Postpone application until meteorological conditions stabilize."
                if not spray_output.wind_suitable:
                    why_bullets.append(f"Wind speed is {wind_speed_kmh:.1f} km/h, which exceeds the safe limit of 15.0 km/h (severe spray drift hazard).")
                if not spray_output.rain_probability_suitable:
                    why_bullets.append(f"Rain probability is {rain_prob_pct:.0f}%, which exceeds the 30% safety threshold (imminent rain hazard).")
                if not spray_output.rain_washoff_suitable:
                    why_bullets.append(f"Forecast rainfall of {rainfall_4h_mm:.1f} mm within 4 hours post-spray will dissolve and wash off active ingredients.")
                action_window = forward_win
                impact = {
                    "chemical_wastage": "High risk (estimated 60-80% active ingredient lost to wind drift or rain wash-off).",
                    "financial_loss": f"Estimated wasted input cost of ₹1,200 - ₹2,000 per acre on {crop_name}.",
                    "agronomic_risk": "Inadequate pest control efficacy; potential runoff into field drainage.",
                }
                alternatives = [
                    "Postpone spraying and monitor tomorrow morning's forecast between 06:00 and 09:00 IST.",
                    f"Verify physical pest economic threshold level (ETL) on {crop_name} scouting before re-scheduling.",
                    "Ensure spray equipment nozzles are calibrated for drift-reducing coarse droplets when spraying resumes.",
                ]
                if forward_win.status == "available" and forward_win.best_window:
                    bw = forward_win.best_window
                    why_bullets.append(
                        f"Optimal future action window identified: {bw.summary} (Score: {bw.score:.1f}/100, "
                        f"avg wind: {bw.avg_wind_speed_kmh:.1f} km/h, rain chance <= {bw.max_rain_probability_pct:.0f}%)."
                    )
                    alternatives.insert(
                        0,
                        f"Plan chemical application for recommended window: {bw.summary} (Score: {bw.score:.1f}/100).",
                    )
                    for fb in forward_win.fallback_windows:
                        alternatives.append(f"Alternative fallback window: {fb.summary} (Score: {fb.score:.1f}/100).")

        # 7. Add Forward Window Search to Ledger Rules
        if forward_win.status == "available" and forward_win.best_window:
            rule_forward = LedgerRuleEvaluation(
                rule_name="forward_action_window_search",
                threshold="Contiguous valid hours >= 2 (wind <= 15 km/h, rain prob <= 30%, rain == 0 mm)",
                observed_value=f"Best window: {forward_win.best_window.summary} (Score: {forward_win.best_window.score:.1f})",
                unit="operational_window",
                operator="exists",
                satisfied=True,
                rationale="Identified optimal future action window via hourly forecast forward scanning.",
            )
            ledger_rules.append(rule_forward)
        elif not has_red_inside and not spray_output.is_suitable:
            rule_forward = LedgerRuleEvaluation(
                rule_name="forward_action_window_search",
                threshold="Contiguous valid hours >= 2 (wind <= 15 km/h, rain prob <= 30%, rain == 0 mm)",
                observed_value="No valid window found in forecast horizon",
                unit="operational_window",
                operator="exists",
                satisfied=False,
                rationale=forward_win.reason,
            )
            ledger_rules.append(rule_forward)

        # 8. Honest Uncertainty Statement (WRF Honesty Rule)
        wrf_info = evidence.model_information.get("wrf", {})
        is_wrf_active = wrf_info.get("status") == "available"

        uncertainty_dict = {
            "forecast_lead_time": "0-72 hours",
            "model_source": "NOAA GFS 0.25° / Synoptic Observation",
            "wrf_regional_available": is_wrf_active,
            "multi_model_agreement": "single_model_dominant",
            "statement": (
                "Decision rendered using verified GFS 0.25° / surface synoptic data. "
                "WRF regional model is unconfigured and not active; no multi-model divergence is claimed."
                if not is_wrf_active
                else "Multi-model consensus verified across GFS and active WRF regional stream."
            ),
        }

        # 9. Traceable Evidence Data
        evidence_data = {
            "location": f"{evidence.location.name}, {evidence.location.district or ''}, {evidence.location.state or ''}",
            "crop_evaluated": crop_name,
            "wind_speed_observed_kmh": wind_speed_kmh,
            "wind_speed_threshold_kmh": 15.0,
            "rain_probability_pct": rain_prob_pct,
            "rain_probability_threshold_pct": 30.0,
            "rainfall_4h_post_spray_mm": rainfall_4h_mm,
            "alerts_active_count": len(alert_evals),
            "primary_alert_id": primary_alert.alert_id if primary_alert else None,
            "primary_warning_level": primary_alert.warning_level if primary_alert else None,
            "issuing_office": primary_alert.issuing_office if primary_alert else None,
            "is_official": primary_alert.is_official if primary_alert else (len(evidence.alerts) > 0),
            "hazard_type": primary_alert.hazard_type if primary_alert else None,
            "affected_area_name": primary_alert.area_description if primary_alert else None,
            "prescribed_action": primary_alert.prescribed_action if primary_alert else None,
            "exposure_state": primary_alert.exposure_state.value if primary_alert else None,
            "composite_impact_score": primary_alert.composite_impact_score if primary_alert else 0.0,
            "sources": [s.get("provider", "Unknown") for s in evidence.source_information],
            "action_window_status": action_window.status if hasattr(action_window, "status") else action_window.get("status", "unknown"),
        }

        # 10. Compile Evidence Ledger
        calc_dict: Dict[str, Any] = {
            "spray_suitability": spray_output.model_dump(),
            "engine_version": "3.0.0",
            "method": "FAO-56 / Agronomic Drift-Washoff Matrix / AlertImpactEngine / ActionWindowEngine",
        }
        if alert_evals:
            calc_dict["alert_evaluations"] = [a.model_dump() for a in alert_evals]
        if hasattr(action_window, "hourly_evaluations") and action_window.hourly_evaluations:
            calc_dict["action_window_scan"] = {
                "status": action_window.status,
                "score": action_window.score,
                "total_candidate_hours_scanned": len(action_window.hourly_evaluations),
                "valid_hours_count": sum(1 for h in action_window.hourly_evaluations if h.passed),
                "best_window": action_window.best_window.model_dump() if action_window.best_window else None,
                "fallback_windows_count": len(action_window.fallback_windows),
            }

        ledger = EvidenceLedger(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            question=question,
            inputs={
                "crop_name": crop_name,
                "wind_speed_kmh": wind_speed_kmh,
                "rain_probability_pct": rain_prob_pct,
                "rain_4h_post_spray_mm": rainfall_4h_mm,
                "alerts_active_count": len(alert_evals),
            },
            rules=ledger_rules,
            calculations=calc_dict,
            sources=evidence.source_information,
            timestamps={
                "requested_time": evidence.requested_time,
                "data_retrieved_at": evidence.source_information[0].get("retrieved_at", "") if evidence.source_information else "",
                "valid_window_start": evidence.valid_time.get("start", ""),
                "valid_window_end": evidence.valid_time.get("end", ""),
            },
            output={
                "verdict": verdict.value,
                "severity": severity.value,
                "recommended_action": recommended_action,
                "confidence": ConfidenceLevel.HIGH.value,
            },
        )

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=recommended_action,
            action_window=action_window,
            confidence=ConfidenceLevel.HIGH,
            uncertainty=uncertainty_dict,
            why=why_bullets,
            impact=impact,
            alternatives=alternatives,
            evidence=evidence_data,
            ledger=ledger,
        )

    # ========================================================================
    # 2. Farmer Irrigation Decision ("Should I irrigate my wheat field?")
    # ========================================================================

    def _evaluate_farmer_irrigation(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
    ) -> NirnayCard:
        """Evaluates crop irrigation scheduling using deterministic water balance & alert overlay."""
        crop_name = context.get("crop_name") or "Wheat"
        rain_48h = float(evidence.forecast.get("rainfall_total_mm", 0.0))

        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=evidence.requested_time,
        )

        has_red_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_orange_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() in ("ORANGE", "AMBER")
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )

        if has_red_inside:
            verdict = DecisionOutcome.NO_GO
            severity = SeverityLevel.CRITICAL
            action = primary_alert.prescribed_action
            why = [
                f"Official Red Alert bulletin active for {evidence.location.district or evidence.location.name}.",
                "Immediate suspension of all irrigation pump operations to prevent electrical hazards and root waterlogging.",
            ]
            alternatives = ["Wait until emergency Red Alert has officially lapsed."]
        elif has_orange_inside or rain_48h >= 10.0:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH if has_orange_inside else SeverityLevel.MODERATE
            action = primary_alert.prescribed_action if has_orange_inside else f"Postpone irrigation for {crop_name}. Incoming rain will satisfy crop water demand."
            why = [
                f"Official Orange Alert active for {evidence.location.district or evidence.location.name}." if has_orange_inside else f"Significant rainfall of {rain_48h:.1f} mm forecast within 48h.",
                "Irrigating prior to rain causes severe root waterlogging and nutrient leaching.",
            ]
            alternatives = ["Re-evaluate soil moisture 24 hours after rainfall ceases."]
        else:
            verdict = DecisionOutcome.GO
            severity = SeverityLevel.LOW
            action = f"Proceed with planned irrigation for {crop_name}."
            why = [
                f"Low rainfall forecast ({rain_48h:.1f} mm < 10.0 mm); soil moisture requires replenishment.",
            ]
            alternatives = ["Apply standard irrigation depth according to root zone capacity."]

        crop_stage = context.get("crop_stage", "UNKNOWN")
        stage_caveat = ""
        if str(crop_stage).upper() in ("UNKNOWN", "NONE", ""):
            stage_caveat = " Note: Growth stage is unspecified (UNKNOWN); recommendation is based on standard baseline crop water requirements."

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=action + stage_caveat,
            action_window={"status": "unavailable", "reason": "Irrigation scheduling does not scan spray action windows."},
            confidence=ConfidenceLevel.HIGH,
            uncertainty={
                "wrf_available": False,
                "statement": "GFS 0.25° guidance; WRF regional model unconfigured.",
                "soil_moisture": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
                "crop_stage": "Stage unknown; recommendation uses generic baseline." if str(crop_stage).upper() in ("UNKNOWN", "NONE", "") else "Verified.",
            },
            why=why,
            impact={"water_savings": "Conserves irrigation fuel/electricity by utilizing natural rainfall." if verdict == DecisionOutcome.POSTPONE else "Maintains optimal transpiration."},
            alternatives=alternatives,
            evidence={
                "forecast_rain_48h_mm": rain_48h,
                "crop_name": crop_name,
                "crop_stage": crop_stage,
                "alerts_count": len(alert_evals),
                "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            },
            ledger=None,
        )

    # ========================================================================
    # 2b. Farmer Harvest Decision ("Can I harvest tomorrow?")
    # ========================================================================

    def _evaluate_farmer_harvest(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
    ) -> NirnayCard:
        """Evaluates harvesting weather window feasibility deterministically."""
        crop_name = context.get("crop") or context.get("crop_name") or "Field Crop"
        temp_c = float(evidence.forecast.get("temperature_c", 28.0))
        humidity = float(evidence.forecast.get("relative_humidity_pct", 55.0))
        wind_kmh = float(evidence.forecast.get("wind_speed_kmh", 12.0))
        rain_24h = float(evidence.forecast.get("rainfall_total_mm", 0.0))

        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=evidence.requested_time,
        )

        has_red_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_orange_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() in ("ORANGE", "AMBER")
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )

        hourly_fc = getattr(evidence, "hourly_forecast", None) or evidence.forecast.get("hourly_forecast", []) or []
        res = evaluate_harvest_window(
            hourly_forecast=hourly_fc,
            current_temp_c=temp_c,
            current_humidity_pct=humidity,
            current_wind_kmh=wind_kmh,
            forecast_rain_24h_mm=rain_24h,
            crop_name=crop_name,
            active_alerts=evidence.alerts,
        )

        if has_red_inside:
            verdict = DecisionOutcome.NO_GO
            severity = SeverityLevel.CRITICAL
            action = primary_alert.prescribed_action
            why = [
                f"Official Red Alert bulletin active for {evidence.location.district or evidence.location.name}.",
                "Suspension of all harvesting and machinery operations due to extreme meteorological hazard.",
            ]
            action_window = {"status": "unavailable", "reason": "Official Red Alert in effect."}
        elif has_orange_inside or rain_24h > 0.0 or not res["is_suitable"]:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH if has_orange_inside else SeverityLevel.MODERATE
            action = primary_alert.prescribed_action if has_orange_inside else res["recommended_action"]
            why = res["blocking_factors"] if res["blocking_factors"] else [
                f"Rainfall forecast of {rain_24h:.1f} mm exceeds 0.0 mm dry harvest threshold.",
            ]
            action_window = {"status": "unavailable", "reason": "; ".join(why)}
        else:
            verdict = DecisionOutcome.GO
            severity = SeverityLevel.LOW
            action = res["recommended_action"]
            why = [
                "Dry weather forecast (0.0 mm rain, rain probability <= 25%).",
                f"Wind speed ({wind_kmh:.1f} km/h) and relative humidity ({humidity:.0f}%) are within safe harvesting limits.",
                "Continuous dry operational window identified.",
            ]
            action_window = res.get("workable_window") or {"status": "available", "summary": "Full daylight operational window favorable."}

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=action,
            action_window=action_window,
            confidence=ConfidenceLevel.HIGH,
            uncertainty={
                "crop_specific_rules": "Generic operational weather constraints applied (crop-specific maturity thresholds unavailable).",
                "wrf_available": False,
                "statement": "Recommendation based on verified GFS 0.25° surface weather.",
            },
            why=why,
            impact={"harvest_quality": "Protects grain quality and avoids mechanical harvesting in wet soil." if verdict == DecisionOutcome.POSTPONE else "Optimal moisture and low shattering loss."},
            alternatives=["Delay harvesting until a verified 4-hour dry window opens."] if verdict == DecisionOutcome.POSTPONE else ["Proceed with harvesting and ensure clean storage."],
            evidence={
                "rainfall_24h_mm": rain_24h,
                "wind_speed_kmh": wind_kmh,
                "relative_humidity_pct": humidity,
                "alerts_count": len(alert_evals),
            },
            ledger=None,
        )

    # ========================================================================
    # 2c. Farmer Sowing & Field Work Decision ("Should I sow today?")
    # ========================================================================

    def _evaluate_farmer_sowing_fieldwork(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
    ) -> NirnayCard:
        """Evaluates field-work and sowing feasibility deterministically."""
        crop_name = context.get("crop") or context.get("crop_name") or "Field Crop"
        temp_max = float(evidence.forecast.get("temperature_c", 32.0))
        temp_min = float(evidence.observations.get("temperature_c", 22.0))
        rain_today = float(evidence.observations.get("rainfall_mm", 0.0))
        rain_48h = float(evidence.forecast.get("rainfall_total_mm", 0.0))
        wind_kmh = float(evidence.forecast.get("wind_speed_kmh", 12.0))

        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=evidence.requested_time,
        )

        has_red_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_orange_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() in ("ORANGE", "AMBER")
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )

        res = evaluate_sowing_fieldwork(
            temp_max_c=temp_max,
            temp_min_c=temp_min,
            rainfall_24h_mm=rain_today,
            forecast_rain_48h_mm=rain_48h,
            wind_speed_kmh=wind_kmh,
            active_alerts=evidence.alerts,
            crop_name=crop_name,
        )

        if has_red_inside:
            verdict = DecisionOutcome.NO_GO
            severity = SeverityLevel.CRITICAL
            action = primary_alert.prescribed_action
            why = [
                f"Official Red Alert bulletin active for {evidence.location.district or evidence.location.name}.",
                "Suspend all field work, tillage, and sowing immediately.",
            ]
        elif has_orange_inside or not res["is_favorable"]:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH if has_orange_inside else SeverityLevel.MODERATE
            action = primary_alert.prescribed_action if has_orange_inside else res["recommended_action"]
            why = [res["reason"]]
        elif res["state"] == FieldWorkState.CAUTION:
            verdict = DecisionOutcome.PROCEED_WITH_CAUTION
            severity = SeverityLevel.MODERATE
            action = res["recommended_action"]
            why = [res["reason"]]
        else:
            verdict = DecisionOutcome.GO
            severity = SeverityLevel.LOW
            action = res["recommended_action"]
            why = [res["reason"]]

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=action,
            action_window={"status": "available" if verdict == DecisionOutcome.GO else "unavailable"},
            confidence=ConfidenceLevel.HIGH,
            uncertainty={
                "soil_moisture": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
                "wrf_available": False,
                "statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            },
            why=why,
            impact={"operational_efficacy": "Protects against soil compaction and seed washout." if verdict == DecisionOutcome.POSTPONE else "Favorable soil workability."},
            alternatives=["Monitor soil moisture recharge after rainfall."] if verdict == DecisionOutcome.POSTPONE else ["Complete primary field preparation."],
            evidence={
                "rainfall_today_mm": rain_today,
                "forecast_rain_48h_mm": rain_48h,
                "temp_max_c": temp_max,
                "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            },
            ledger=None,
        )

    # ========================================================================
    # 2d. Farmer Crop-Weather Risk Decision ("What is the weather risk?")
    # ========================================================================

    def _evaluate_farmer_crop_risk(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
        climate_context: Optional[Dict[str, Any]] = None,
    ) -> NirnayCard:
        """Quantifies deterministic crop-weather risk without diagnosing diseases."""
        crop_name = context.get("crop") or context.get("crop_name") or "Field Crop"
        temp_max = float(evidence.forecast.get("temperature_c", 32.0))
        wind_kmh = float(evidence.forecast.get("wind_speed_kmh", 12.0))
        rain_48h = float(evidence.forecast.get("rainfall_total_mm", 0.0))
        temp_anomaly = climate_context.get("temperature_anomaly_c") if climate_context else None

        res = evaluate_crop_weather_risk(
            temp_max_c=temp_max,
            wind_speed_kmh=wind_kmh,
            forecast_rain_48h_mm=rain_48h,
            temperature_anomaly_c=temp_anomaly,
            active_alerts=evidence.alerts,
            crop_name=crop_name,
        )

        tier = res["risk_tier"]
        if tier == "SEVERE":
            verdict = DecisionOutcome.NO_GO
            severity = SeverityLevel.CRITICAL
        elif tier == "HIGH":
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH
        elif tier == "MODERATE":
            verdict = DecisionOutcome.PROCEED_WITH_CAUTION
            severity = SeverityLevel.MODERATE
        else:
            verdict = DecisionOutcome.GO
            severity = SeverityLevel.LOW

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=res["primary_risk"],
            action_window={"status": "unavailable", "reason": "Weather risk assessment does not scan operational action windows."},
            confidence=ConfidenceLevel.HIGH,
            uncertainty={
                "disease_disclaimer": "Weather risk evaluates atmospheric exposure only. Agronomic disease diagnosis requires physical scouting.",
                "wrf_available": False,
            },
            why=res["risks"],
            impact={"crop_risk_tier": tier, "primary_risk": res["primary_risk"]},
            alternatives=["Take protective crop measures such as light irrigation or windbreaks if applicable."],
            evidence=res["metrics"],
            ledger=None,
        )

    # ========================================================================
    # 2e. Farmer Daily Farm Plan Decision ("What should I do on my farm today?")
    # ========================================================================

    def _evaluate_farmer_daily_plan(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
    ) -> NirnayCard:
        """Synthesizes a multi-operation Daily Farm Action Plan deterministically."""
        from app.farmer.models import FarmerContext
        farmer_ctx = FarmerContext(
            crop=context.get("crop") or context.get("crop_name"),
            crop_stage=context.get("crop_stage", "UNKNOWN"),
            location=context.get("location") or evidence.location.name,
            latitude=evidence.location.latitude,
            longitude=evidence.location.longitude,
        )
        weather_dict = {
            "wind_speed_kmh": float(evidence.forecast.get("wind_speed_kmh", 12.0)),
            "rain_probability_pct": float(evidence.forecast.get("rain_probability_pct", 0.0)),
            "rainfall_today_mm": float(evidence.observations.get("rainfall_mm", 0.0)),
            "rainfall_forecast_48h_mm": float(evidence.forecast.get("rainfall_total_mm", 0.0)),
            "temp_max_c": float(evidence.forecast.get("temperature_c", 30.0)),
            "temp_min_c": float(evidence.observations.get("temperature_c", 20.0)),
            "relative_humidity_pct": float(evidence.forecast.get("relative_humidity_pct", 55.0)),
            "et0_mm_day": float(evidence.forecast.get("et0_mm_day", 4.5)),
        }
        hourly_fc = getattr(evidence, "hourly_forecast", None) or evidence.forecast.get("hourly_forecast", []) or []
        plan = generate_daily_farm_plan(
            farmer_context=farmer_ctx,
            weather_data=weather_dict,
            hourly_forecast=hourly_fc,
            active_alerts=evidence.alerts or [],
        )

        has_no_go = any(item.status == "NO_GO" for item in plan.operations)
        has_postpone = any(item.status in ("POSTPONE", "WAIT") for item in plan.operations)
        verdict = DecisionOutcome.NO_GO if has_no_go else (DecisionOutcome.POSTPONE if has_postpone else DecisionOutcome.GO)
        severity = SeverityLevel.HIGH if has_no_go else (SeverityLevel.MODERATE if has_postpone else SeverityLevel.LOW)

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=plan.primary_advisory,
            action_window={"status": "available", "summary": "Comprehensive daily operational schedule generated."},
            confidence=ConfidenceLevel.HIGH,
            uncertainty={"soil_moisture": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER},
            why=[f"{op.operation}: {op.status} ({op.reason})" for op in plan.operations],
            impact={"daily_plan_summary": plan.primary_advisory},
            alternatives=[op.action for op in plan.operations],
            evidence=weather_dict,
            ledger=None,
        )

    # ========================================================================
    # 3. General Operational / Hazard Decision
    # ========================================================================

    def _evaluate_general_operational(
        self,
        decision_id: str,
        evidence: EvidenceBundle,
        question: str,
        context: Dict[str, Any],
    ) -> NirnayCard:
        """Evaluates general outdoor operations, logistics, or hazard safety."""
        alert_evals, primary_alert = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=evidence.requested_time,
        )

        rain_mm = float(evidence.forecast.get("rainfall_total_mm", 0.0))
        wind_kmh = float(evidence.forecast.get("wind_speed_kmh", 10.0))

        has_red_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_red_outside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "RED"
            and primary_alert.exposure_state == ExposureState.OUTSIDE
            and primary_alert.is_active
        )
        has_orange_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() in ("ORANGE", "AMBER")
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )
        has_yellow_inside = (
            primary_alert is not None
            and primary_alert.warning_level.upper() == "YELLOW"
            and primary_alert.exposure_state == ExposureState.INSIDE
            and primary_alert.is_active
        )

        if has_red_inside or rain_mm >= 64.5:
            verdict = DecisionOutcome.NO_GO
            severity = SeverityLevel.CRITICAL
            action = primary_alert.prescribed_action if has_red_inside else "Cancel or suspend all unprotected outdoor operations immediately."
            why = [
                f"Official Red Alert bulletin in effect for {evidence.location.district or evidence.location.name}." if has_red_inside else "Extreme rainfall (>= 64.5 mm) detected.",
                "Direct risk to human safety and physical infrastructure.",
            ]
            if primary_alert and has_red_inside:
                why.append(f"Composite operational impact score: {primary_alert.composite_impact_score:.1f}/10.0 ({primary_alert.risk_category.upper()} risk).")
        elif has_orange_inside or rain_mm >= 25.0 or wind_kmh >= 40.0:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH
            action = primary_alert.prescribed_action if has_orange_inside else "Postpone outdoor activities or relocate to reinforced indoor shelters."
            why = [
                f"Official Orange Alert in effect for {evidence.location.district or evidence.location.name}." if has_orange_inside else "Elevated meteorological risk from heavy precipitation or high wind gusts.",
            ]
            if primary_alert and has_orange_inside:
                why.append(f"Composite operational impact score: {primary_alert.composite_impact_score:.1f}/10.0.")
        elif has_red_outside:
            verdict = DecisionOutcome.PROCEED_WITH_CAUTION
            severity = SeverityLevel.MODERATE
            action = primary_alert.prescribed_action
            why = [
                f"Official Red Alert active for {primary_alert.area_description}, but {evidence.location.district or evidence.location.name} is outside the active warning boundary.",
                f"Local conditions remain within operational thresholds (Rain: {rain_mm:.1f} mm, Wind: {wind_kmh:.1f} km/h).",
            ]
        elif has_yellow_inside or rain_mm >= 10.0 or wind_kmh >= 25.0:
            verdict = DecisionOutcome.PROCEED_WITH_CAUTION
            severity = SeverityLevel.MODERATE
            action = primary_alert.prescribed_action if has_yellow_inside else "Proceed with caution; prepare on-site contingency plans and flexible scheduling."
            why = [
                f"Official Yellow Alert active for {evidence.location.district or evidence.location.name}." if has_yellow_inside else f"Moderate weather conditions observed (Rain: {rain_mm:.1f} mm, Wind: {wind_kmh:.1f} km/h).",
            ]
        else:
            verdict = DecisionOutcome.GO
            severity = SeverityLevel.LOW
            action = "Conditions are favorable for normal outdoor activities and logistics."
            why = [
                "Weather parameters are within safe operational limits; no active severe alerts.",
            ]

        uncertainty_dict = {
            "wrf_available": False,
            "statement": "Decision rendered using verified GFS 0.25° / surface synoptic data. Regional WRF unconfigured.",
        }

        # Build ledger if alerts present
        ledger_rules = []
        if primary_alert:
            rule_alert = LedgerRuleEvaluation(
                rule_name="official_severe_weather_clearance",
                threshold=f"Preserve {primary_alert.warning_level} Warning",
                observed_value=f"{primary_alert.warning_level} ({primary_alert.hazard_type})",
                unit="official_severity",
                operator="==",
                satisfied=not has_red_inside,
                rationale=f"Official {primary_alert.issuing_office} {primary_alert.warning_level} warning severity is strictly immutable.",
            )
            rule_exposure = LedgerRuleEvaluation(
                rule_name="spatial_exposure_verification",
                threshold="Location containment in alert geometry/district",
                observed_value=f"{primary_alert.exposure_state.value}",
                unit="exposure_state",
                operator="in [INSIDE, BUFFER, OUTSIDE]",
                satisfied=True,
                rationale=f"Spatial evaluation confirmed {evidence.location.district or evidence.location.name} status as {primary_alert.exposure_state.value}.",
            )
            ledger_rules.extend([rule_alert, rule_exposure])

        ledger = EvidenceLedger(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            question=question,
            inputs={"rain_total_mm": rain_mm, "wind_speed_kmh": wind_kmh, "alerts_count": len(evidence.alerts)},
            rules=ledger_rules,
            calculations={"alert_evaluations": [a.model_dump() for a in alert_evals]},
            sources=evidence.source_information,
            timestamps={
                "requested_time": evidence.requested_time,
                "data_retrieved_at": evidence.source_information[0].get("retrieved_at", "") if evidence.source_information else "",
                "valid_window_start": evidence.valid_time.get("start", ""),
                "valid_window_end": evidence.valid_time.get("end", ""),
            },
            output={"verdict": verdict.value, "severity": severity.value, "recommended_action": action, "confidence": ConfidenceLevel.HIGH.value},
        ) if primary_alert else None

        return NirnayCard(
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=action,
            action_window={"status": "unavailable", "reason": "General operational hazard query does not scan spray action windows."},
            confidence=ConfidenceLevel.HIGH if not has_orange_inside else ConfidenceLevel.MEDIUM,
            uncertainty=uncertainty_dict,
            why=why,
            impact={
                "operational_risk": f"Severity tier evaluated as {severity.value}.",
                "composite_impact_score": f"{primary_alert.composite_impact_score:.1f}/10.0" if primary_alert else "0.0/10.0",
                "exposure_state": primary_alert.exposure_state.value if primary_alert else "NONE",
            },
            alternatives=["Monitor local radar updates and official weather bulletins."],
            evidence={
                "rain_total_mm": rain_mm,
                "wind_speed_kmh": wind_kmh,
                "alerts_count": len(evidence.alerts),
                "primary_alert_id": primary_alert.alert_id if primary_alert else None,
                "primary_warning_level": primary_alert.warning_level if primary_alert else None,
                "hazard_type": primary_alert.hazard_type if primary_alert else None,
                "issuing_office": primary_alert.issuing_office if primary_alert else None,
                "is_official": primary_alert.is_official if primary_alert else (len(evidence.alerts) > 0),
                "affected_area_name": primary_alert.area_description if primary_alert else None,
                "exposure_state": primary_alert.exposure_state.value if primary_alert else None,
                "composite_impact_score": primary_alert.composite_impact_score if primary_alert else 0.0,
                "sources": [s.get("provider", "Unknown") for s in evidence.source_information],
            },
            ledger=ledger,
        )
