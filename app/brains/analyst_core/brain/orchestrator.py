"""End-to-end analytical pipeline orchestrator with Canonical State, Data Fusion, and LLM Validation."""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

from app.brains.analyst_core.models.schemas import (
    QueryCategory,
    RiskLevel,
    ConfidenceLevel,
    HazardType,
    Persona,
    AlertSeverity,
    WarningFeedStatus,
)
from app.brains.analyst_core.models.query_entities import QueryEntities
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
)
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState
from app.brains.analyst_core.models.analysis_context import AnalysisContext
from app.brains.analyst_core.models.analyst_result import (
    AnalystResult,
    EvidenceItem,
    UncertaintyFactor,
    SectorImpact,
    DecisionSupport,
)
from app.brains.analyst_core.nlu.intent_classifier import IntentClassifier
from app.brains.analyst_core.nlu.entity_extractor import EntityExtractor
from app.brains.analyst_core.nlu.slot_filler import SlotFiller
from app.brains.analyst_core.nlu.context_memory import ConversationMemory
from app.brains.analyst_core.data.providers.base import DataProvider
from app.brains.analyst_core.data.fusion import DataFusionEngine
from app.brains.analyst_core.qc.quality_control import MeteorologicalQC
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.analysis.risk import RiskEngine
from app.brains.analyst_core.analysis.forecast import ForecastAnalyzer
from app.brains.analyst_core.analysis.comparison import ComparisonEngine
from app.brains.analyst_core.analysis.anomaly import AnomalyAnalyzer
from app.brains.analyst_core.analysis.trend import TrendAnalyzer
from app.brains.analyst_core.analysis.impact import ImpactAnalyzer
from app.brains.analyst_core.analysis.scenario import ScenarioAnalyzer
from app.brains.analyst_core.analysis.uncertainty_propagation import UncertaintyPropagator
from app.brains.analyst_core.evidence.provenance import ProvenanceTracker
from app.brains.analyst_core.evidence.confidence import ConfidenceEvaluator
from app.brains.analyst_core.evidence.uncertainty import UncertaintyQuantifier
from app.brains.analyst_core.evidence.sufficiency import EvidenceSufficiencyEvaluator
from app.brains.analyst_core.safety.safety_guard import SafetyGuard
from app.brains.analyst_core.safety.safety_gateway import SafetyGateway
from app.brains.analyst_core.safety.llm_validator import LLMOutputValidator
from app.brains.analyst_core.safety.certifier import ResponseCertifier
from app.brains.analyst_core.llm.explainer import LLMExplainer
from app.brains.analyst_core.brain.decision_engine import DecisionEngine
from app.brains.analyst_core.data.alignment import TemporalAlignmentEngine
from app.brains.analyst_core.models.schemas import PipelineState


class AnalystOrchestrator:
    """Coordinates the full meteorological intelligence pipeline.
    
    Pipeline:
        Query -> Safety Gateway -> NLU -> Data Fetch -> Meteorological QC ->
        Temporal Alignment -> Data Fusion -> Canonical Weather State ->
        Evidence Sufficiency Gate -> Hazard & Forecast Analysis ->
        Uncertainty Propagation -> Risk Engine -> Decision Support ->
        LLM Explainer -> LLM Output Validator -> Response Certifier -> Certified AnalystResult
    """

    def __init__(
        self,
        data_provider: DataProvider,
        memory: Optional[ConversationMemory] = None,
        explainer: Optional[LLMExplainer] = None,
    ):
        self.provider = data_provider
        self.memory = memory or ConversationMemory()
        self.classifier = IntentClassifier()
        self.extractor = EntityExtractor()
        self.slot_filler = SlotFiller()
        self.qc = MeteorologicalQC()
        self.alignment = TemporalAlignmentEngine()
        self.fusion = DataFusionEngine()
        self.sufficiency = EvidenceSufficiencyEvaluator()
        self.hazard_analyzer = HazardAnalyzer()
        self.risk_engine = RiskEngine()
        self.forecast_analyzer = ForecastAnalyzer()
        self.comparison_engine = ComparisonEngine()
        self.anomaly_analyzer = AnomalyAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.impact_analyzer = ImpactAnalyzer()
        self.scenario_analyzer = ScenarioAnalyzer()
        self.uncertainty_propagator = UncertaintyPropagator()
        self.provenance = ProvenanceTracker()
        self.confidence_evaluator = ConfidenceEvaluator()
        self.uncertainty_quantifier = UncertaintyQuantifier()
        self.safety_gateway = SafetyGateway()
        self.safety_guard = SafetyGuard()
        self.llm_validator = LLMOutputValidator()
        self.certifier = ResponseCertifier()
        self.decision_engine = DecisionEngine()
        self.explainer = explainer or LLMExplainer()

    def process_query(
        self,
        user_query: str,
        persona: Persona = Persona.ANALYST,
        language: str = "en",
        base_time: Optional[datetime] = None,
        context: Optional[AnalysisContext] = None,
    ) -> AnalystResult:
        """Processes user analytical weather query end-to-end with AnalysisContext audit trail."""
        now = base_time or datetime.utcnow()
        ctx = context or AnalysisContext(user_persona=persona, language=language, timestamp=now)
        ctx.record_step("QueryReceived", f"Length: {len(user_query)} chars")

        # 1. Safety Gateway Pre-Flight Inspection
        safety_dec = self.safety_gateway.inspect_query(user_query)
        ctx.record_step("SafetyGateway", f"Allowed: {safety_dec.is_allowed}")
        if not safety_dec.is_allowed:
            return AnalystResult(
                query=user_query,
                analysis_type=QueryCategory.GENERAL_ANALYTICAL_QUERY,
                risk_level=RiskLevel.UNKNOWN,
                recommendation="Query rejected due to security policy or adversarial pattern violation.",
                limitations=safety_dec.flags,
                natural_language_explanation=safety_dec.rejection_reason or "Security validation failure.",
                is_clarification_needed=False,
            )

        # 2. Intent Classification
        category, _ = self.classifier.classify(user_query)
        ctx.record_step("IntentClassifier", f"Category: {category.value}")

        # 3. Entity Extraction
        entities = self.extractor.extract(user_query, base_date=now.date())
        if entities.language == "hi" and language == "en":
            language = "hi"
            ctx.language = "hi"

        # 4. Context Memory Resolution (Multi-turn tracking)
        entities = self.memory.resolve_context(entities)
        ctx.location_name = entities.location
        ctx.target_time_window = entities.time_period
        ctx.record_step("EntityExtractor", f"Location: {entities.location}, Window: {entities.time_period}")

        # 5. Slot Filling & Missing Information Validation
        entities = self.slot_filler.validate_and_fill(
            category=category,
            entities=entities,
            context_location=self.memory.active_location,
            context_comparison_location=self.memory.active_comparison_location,
        )

        if entities.is_clarification_needed:
            return AnalystResult(
                query=user_query,
                location=entities.location,
                analysis_type=category,
                time_period=entities.time_period,
                is_clarification_needed=True,
                clarification_prompt=entities.clarification_question,
                natural_language_explanation=entities.clarification_question,
            )

        # 6. Location Resolution (TEST 2: No silent fallback!)
        loc_meta = self.provider.resolve_location(entities.location)
        if not loc_meta:
            return AnalystResult(
                query=user_query,
                location=entities.location,
                analysis_type=category,
                time_period=entities.time_period,
                risk_level=RiskLevel.UNKNOWN,
                confidence=ConfidenceLevel.INSUFFICIENT_DATA,
                recommendation="No validated data is available for this location.",
                limitations=[f"Location '{entities.location}' could not be resolved by meteorological geodetic services."],
                natural_language_explanation=f"No validated data is available for this location ({entities.location}).",
            )

        primary_loc = loc_meta.name

        # 7. Data Retrieval
        ctx.transition_to(PipelineState.DATA_RETRIEVED, f"Fetching data for {primary_loc}")
        horizon = entities.forecast_horizon_hours or (48 if category != QueryCategory.CURRENT_SITUATION_ANALYSIS else 24)
        raw_obs = self.provider.get_current_observations(primary_loc, current_time=now)
        raw_fc = self.provider.get_forecast(primary_loc, horizon_hours=horizon, current_time=now)
        warn_status = WarningFeedStatus.NO_WARNING_ISSUED
        if hasattr(self.provider, "get_warnings_with_status"):
            raw_alerts, warn_status, warn_ret = self.provider.get_warnings_with_status(primary_loc)
            ctx.retrieval_reports.append(warn_ret)
            if warn_status == WarningFeedStatus.SOURCE_UNAVAILABLE:
                ctx.record_step("WarningFeedStatus", "Official warning feed unavailable; cannot rule out active alerts")
        else:
            raw_alerts = self.provider.get_official_warnings(primary_loc)

        # 8. Meteorological QC (TEST 5: Never replace missing values with zero)
        cleaned_obs, obs_qc = self.qc.process_observations(raw_obs, current_time=now)
        cleaned_fc, fc_qc = self.qc.process_forecast(raw_fc, current_time=now)
        ctx.transition_to(PipelineState.QC_PASSED, f"Cleaned obs: {len(cleaned_obs)}, fc: {len(cleaned_fc)}")

        has_stale_obs = obs_qc["stale_records"] > 0
        freshness_status = "STALE" if has_stale_obs else "VALID"

        # 8.5 Temporal Alignment
        aligned_frame = self.alignment.align(primary_loc, cleaned_obs, cleaned_fc, current_time=now)
        ctx.transition_to(PipelineState.TEMPORALLY_ALIGNED, f"Aligned to {aligned_frame.target_time.isoformat()}")

        # 9. Data Fusion: Build Canonical Weather State
        canonical_state = self.fusion.fuse(
            location=primary_loc,
            observations=cleaned_obs,
            forecasts=cleaned_fc,
            alerts=raw_alerts,
            target_time=now,
            time_window_label=entities.time_period,
            latitude=loc_meta.latitude,
            longitude=loc_meta.longitude,
        )
        ctx.transition_to(PipelineState.STATE_FUSED, "Canonical weather state assembled")

        # 10. Evidence Sufficiency Gate
        is_sufficient, missing_vars, suff_msg = self.sufficiency.evaluate_sufficiency(
            category=category,
            state=canonical_state,
        )
        if not is_sufficient:
            return AnalystResult(
                query=user_query,
                location=primary_loc,
                analysis_type=category,
                time_period=entities.time_period,
                risk_level=RiskLevel.UNKNOWN,
                confidence=ConfidenceLevel.INSUFFICIENT_DATA,
                recommendation=f"Analysis halted: {suff_msg}",
                limitations=[f"Missing critical meteorological variables: {', '.join(missing_vars)}"],
                natural_language_explanation=f"Insufficient reliable evidence to evaluate {category.value.replace('_', ' ').title()}: {suff_msg}",
            )

        # 11. Hazard Analysis (IMD/WMO standards)
        hazards, hazard_severity, hazard_evidence = self.hazard_analyzer.analyze_hazards(
            cleaned_obs, cleaned_fc, raw_alerts
        )

        # 12. Forecast Stream & Agreement Analysis
        fc_analysis = self.forecast_analyzer.analyze_forecast_stream(cleaned_fc)
        agreement_score = fc_analysis.get("model_agreement_score")

        # 13. Specialized Analyses (Comparison, Anomaly, Trend, Scenario)
        comparison_res = None
        anomaly_res = None
        trend_res = None
        scenario_res = None

        if category in {QueryCategory.LOCATION_COMPARISON, QueryCategory.WEATHER_COMPARISON} and entities.comparison_location:
            loc_b_meta = self.provider.resolve_location(entities.comparison_location)
            if not loc_b_meta:
                return AnalystResult(
                    query=user_query,
                    location=primary_loc,
                    analysis_type=category,
                    time_period=entities.time_period,
                    risk_level=RiskLevel.UNKNOWN,
                    confidence=ConfidenceLevel.INSUFFICIENT_DATA,
                    recommendation=f"Cannot complete comparison: No validated data is available for second location '{entities.comparison_location}'.",
                    limitations=[f"Location '{entities.comparison_location}' failed geodetic validation."],
                    natural_language_explanation=f"No validated data is available for second comparison location ({entities.comparison_location}).",
                )
            loc_b_name = loc_b_meta.name
            obs_b = self.provider.get_current_observations(loc_b_name, current_time=now)
            fc_b = self.provider.get_forecast(loc_b_name, horizon_hours=horizon, current_time=now)
            alerts_b = self.provider.get_official_warnings(loc_b_name)
            hazards_b, sev_b, _ = self.hazard_analyzer.analyze_hazards(obs_b, fc_b, alerts_b)
            risk_b = self.risk_engine.evaluate_risk(hazards_b, sev_b, obs_b, fc_b, alerts_b, ConfidenceLevel.MEDIUM)

            risk_a_prelim = RiskLevel.LOW if hazard_severity < 40 else RiskLevel.MODERATE
            comparison_res = self.comparison_engine.compare_locations(
                primary_loc, cleaned_obs, cleaned_fc, risk_a_prelim,
                loc_b_name, obs_b, fc_b, risk_b.level
            )

        elif category == QueryCategory.TEMPORAL_COMPARISON:
            # Query-derived dual periods instead of fixed 7 days
            if entities.period_a_dates and entities.period_b_dates:
                p_a_start, p_a_end = entities.period_a_dates
                p_b_start, p_b_end = entities.period_b_dates
                label_a = entities.period_a_label or f"{p_a_start} to {p_a_end}"
                label_b = entities.period_b_label or f"{p_b_start} to {p_b_end}"

                # Fetch data for period A
                obs_a = self.provider.get_historical_observations(primary_loc, p_a_start, p_a_end)
                if not obs_a and p_a_start == now.date():
                    obs_a = cleaned_obs

                # Fetch data for period B
                obs_b = self.provider.get_historical_observations(primary_loc, p_b_start, p_b_end)
                if not obs_b and p_b_start == now.date():
                    obs_b = cleaned_obs

                comparison_res = self.comparison_engine.compare_temporal(
                    primary_loc, label_a, obs_a, label_b, obs_b
                )
            else:
                hist_start = now.date() - timedelta(days=7)
                hist_obs = self.provider.get_historical_observations(primary_loc, hist_start, now.date())
                comparison_res = self.comparison_engine.compare_temporal(
                    primary_loc, "Current Operational Window", cleaned_obs, "Previous 7-Day Baseline", hist_obs
                )

        elif category == QueryCategory.ANOMALY_INTERPRETATION:
            baseline = self.provider.get_climate_baseline(primary_loc, month=now.month)
            target_var = entities.weather_variable or "temperature"
            if "rain" in target_var.lower() or "precip" in target_var.lower():
                curr_rain = aligned_frame.rainfall_1h_mm or (cleaned_obs[0].rainfall_mm if cleaned_obs and cleaned_obs[0].rainfall_mm is not None else None)
                norm_r = baseline.get("normal_monthly_rainfall_mm")
                p90_r = baseline.get("rainfall_p90_mm")
                if curr_rain is not None and norm_r is not None:
                    anomaly_res = self.anomaly_analyzer.calculate_anomaly(
                        variable_name="Precipitation",
                        observed_value=curr_rain,
                        baseline_normal=norm_r,
                        units="mm",
                        reference_period=baseline.get("reference_period", "1991-2020"),
                        rainfall_p90_mm=p90_r,
                    )
                else:
                    anomaly_res = {
                        "variable": "Precipitation",
                        "status": "UNAVAILABLE",
                        "reason": f"Missing observed rainfall or climatological baseline for {primary_loc}.",
                    }
            else:
                curr_temp = aligned_frame.temperature_c
                normal_t = baseline.get("normal_temp_c")
                std_t = baseline.get("temp_std_c")
                if curr_temp is not None and normal_t is not None:
                    anomaly_res = self.anomaly_analyzer.calculate_anomaly(
                        variable_name="Surface Temperature",
                        observed_value=curr_temp,
                        baseline_normal=normal_t,
                        units="°C",
                        reference_period=baseline.get("reference_period", "1991-2020"),
                        baseline_std=std_t,
                    )
                else:
                    anomaly_res = {
                        "variable": "Surface Temperature",
                        "status": "UNAVAILABLE",
                        "reason": f"Missing observed temperature or climatological baseline for {primary_loc}.",
                    }

        elif category == QueryCategory.TREND_INTERPRETATION:
            target_var = entities.weather_variable or "temperature_c"
            # Retrieve true historical time-series data (past 30 days)
            hist_start = now.date() - timedelta(days=30)
            hist_series = self.provider.get_historical_observations(primary_loc, hist_start, now.date())
            series_to_use = hist_series if len(hist_series) >= 3 else cleaned_obs
            trend_res = self.trend_analyzer.calculate_trend(series_to_use, variable=target_var)

        elif category == QueryCategory.SCENARIO_ANALYSIS:
            base_r = fc_analysis.get("total_rainfall_mm") if fc_analysis.get("total_rainfall_mm") is not None else (aligned_frame.rainfall_1h_mm or 0.0)
            base_t = fc_analysis.get("max_temp_c") if fc_analysis.get("max_temp_c") is not None else aligned_frame.temperature_c
            if base_t is not None:
                scenario_res = self.scenario_analyzer.evaluate_scenario(
                    base_rainfall_mm=base_r,
                    base_temp_c=base_t,
                    scenario_query=entities.scenario_condition or user_query,
                    location=primary_loc,
                )
            else:
                scenario_res = {
                    "variable": "Scenario Projection",
                    "status": "UNAVAILABLE",
                    "reason": "Baseline temperature required for scenario perturbation unavailable.",
                }

        # 14. Potential Sector Impacts
        impacts = self.impact_analyzer.assess_impacts(
            hazards, cleaned_obs, cleaned_fc, requested_sector=entities.relevant_sector
        )

        # 15. Evidence Generation with explicit provenance and temporal alignment
        evidence_items: List[EvidenceItem] = []
        if cleaned_obs:
            o_aligned = min(cleaned_obs, key=lambda o: abs((o.timestamp - aligned_frame.target_time).total_seconds()))
            if o_aligned.temperature_c is not None:
                evidence_items.append(
                    self.provenance.create_observation_evidence(
                        o_aligned, "temperature", f"{o_aligned.temperature_c} °C"
                    )
                )
            if o_aligned.rainfall_mm is not None:
                evidence_items.append(
                    self.provenance.create_observation_evidence(
                        o_aligned, "rainfall", f"{o_aligned.rainfall_mm} mm"
                    )
                )
        if cleaned_fc:
            fc_aligned = min(cleaned_fc, key=lambda f: abs((f.valid_time - aligned_frame.target_time).total_seconds()))
            if fc_aligned.rainfall_mm is not None:
                evidence_items.append(
                    self.provenance.create_forecast_evidence(
                        fc_aligned, "forecast_precipitation", f"{fc_analysis.get('total_rainfall_mm', 0.0)} mm total"
                    )
                )
        for alert in raw_alerts:
            evidence_items.append(self.provenance.create_alert_evidence(alert))

        # 16. Confidence Evaluation (Orthogonal to Risk)
        confidence_level, confidence_reasons = self.confidence_evaluator.evaluate_confidence(
            cleaned_obs, cleaned_fc, raw_alerts,
            completeness_pct=obs_qc["completeness_pct"],
            model_agreement_score=agreement_score,
            horizon_hours=horizon,
        )

        uncertainty_factors, limitations = self.uncertainty_quantifier.quantify_uncertainty(
            horizon_hours=horizon,
            completeness_pct=obs_qc["completeness_pct"],
            model_agreement_score=agreement_score,
            has_stale_obs=has_stale_obs,
        )

        # 17. Risk Assessment (Decoupled Confidence & Uncertainty Interval)
        risk_score = self.risk_engine.evaluate_risk(
            hazards=hazards,
            hazard_severity=hazard_severity,
            observations=cleaned_obs,
            forecast=cleaned_fc,
            alerts=raw_alerts,
            confidence_level=confidence_level,
            sector=entities.relevant_sector or entities.user_objective,
            threshold_used=entities.metadata.get("threshold_source"),
            uncertainty_spread=12.0 if confidence_level == ConfidenceLevel.LOW else 6.0,
        )

        # 18. Decision Support
        decision_support = None
        if entities.user_objective or category == QueryCategory.DECISION_SUPPORT:
            decision_support = self.decision_engine.evaluate_decision(
                objective=entities.user_objective or "general outdoor operation",
                hazards=hazards,
                forecasts=cleaned_fc,
                alerts=raw_alerts,
                risk_level=risk_score.level,
            )

        # 19. Synthesize Operational Recommendations
        if decision_support:
            recommendation = f"Decision Recommendation: {decision_support.outcome.value}. {decision_support.justification}"
            monitoring_advice = decision_support.monitoring_points
        elif hazards and hazards != [HazardType.NONE]:
            recommendation = f"Exercise elevated vigilance due to active {', '.join(h.value for h in hazards)} conditions."
            monitoring_advice = [
                "Continuous tracking of national weather radar nowcasts",
                "Precipitation accumulation rate telemetry",
                "Local municipal drainage clearance status",
            ]
        else:
            recommendation = "Maintain routine operational monitoring; no severe weather threats detected."
            monitoring_advice = ["Standard daily forecast issuance review."]

        if warn_status == WarningFeedStatus.SOURCE_UNAVAILABLE:
            limitations.append("Official warning feed is currently unavailable; active civil emergency bulletins cannot be ruled out.")
            if category == QueryCategory.WARNING_ANALYSIS and not raw_alerts:
                recommendation = "Official warning feed is currently unavailable; active civil emergency bulletins cannot be verified or ruled out."

        # 20. Apply Safety Guard (Official alert priority & secret scrubbing)
        safe_recommendation = self.safety_guard.enforce_warning_priority(raw_alerts, recommendation)
        safe_recommendation = self.safety_guard.scrub_credentials(safe_recommendation)

        # Source Metadata with temporal alignment
        source_meta = []
        if cleaned_obs:
            o_aligned = min(cleaned_obs, key=lambda o: abs((o.timestamp - aligned_frame.target_time).total_seconds()))
            source_meta.append({
                "source": o_aligned.source,
                "data_type": o_aligned.data_type.value,
                "timestamp": o_aligned.timestamp.isoformat(),
                "retrieval_timestamp": o_aligned.retrieval_timestamp.isoformat(),
                "is_synthetic": o_aligned.is_synthetic,
                "aligned_target_time": aligned_frame.target_time.isoformat(),
            })
        if cleaned_fc:
            fc_aligned = min(cleaned_fc, key=lambda f: abs((f.valid_time - aligned_frame.target_time).total_seconds()))
            source_meta.append({
                "source": fc_aligned.source,
                "model_name": fc_aligned.model_name,
                "model_confirmed": fc_aligned.model_confirmed,
                "data_type": fc_aligned.data_type.value,
                "init_time": fc_aligned.init_time.isoformat() if fc_aligned.init_time else None,
                "valid_time": fc_aligned.valid_time.isoformat(),
                "lead_time_hours": fc_aligned.lead_time_hours,
                "retrieval_timestamp": fc_aligned.retrieval_timestamp.isoformat(),
                "is_synthetic": fc_aligned.is_synthetic,
                "aligned_target_time": aligned_frame.target_time.isoformat(),
            })

        ctx.record_step("PipelineComplete", f"Risk: {risk_score.level.value}, Confidence: {confidence_level.value}")
        source_meta.append({"analysis_context": ctx.dict()})

        # 21. Build Structured Machine-Readable AnalystResult
        result = AnalystResult(
            query=user_query,
            location=primary_loc,
            analysis_type=category,
            time_period=entities.time_period,
            hazards=hazards,
            observations=cleaned_obs,
            forecast=cleaned_fc,
            official_warnings=raw_alerts,
            risk_level=risk_score.level,
            risk_score=risk_score,
            evidence=evidence_items,
            confidence=confidence_level,
            confidence_reasons=confidence_reasons,
            potential_impacts=impacts,
            recommendation=safe_recommendation,
            monitoring_advice=monitoring_advice,
            uncertainty=uncertainty_factors,
            limitations=limitations,
            source_metadata=source_meta,
            decision_support=decision_support,
            comparison_result=comparison_res,
            scenario_result=scenario_res,
            trend_result=trend_res,
            anomaly_result=anomaly_res,
            data_freshness_status=freshness_status,
            threshold_config_version=ctx.config_version,
            is_clarification_needed=False,
        )

        # 22. Update Conversational Memory
        self.memory.update(
            user_query=user_query,
            category=category,
            entities=entities,
            risk_level=result.risk_level,
            hazards=hazards,
        )

        # 23. Natural Language Explanation & LLM Output Validation Firewall
        ctx.transition_to(PipelineState.EXPLAINED, "Generating persona-tailored explanation")
        candidate_explanation = self.explainer.explain(result, persona=persona, language=language)
        is_valid_output, validation_violations, certified_explanation = self.llm_validator.validate_and_sanitize(
            candidate_text=candidate_explanation,
            result=result,
        )
        if not is_valid_output:
            result.limitations.extend(validation_violations)

        sanitized_text = self.safety_guard.scrub_credentials(certified_explanation)
        result.natural_language_explanation = sanitized_text

        # 24. Claim-Level Fact Verification & Cryptographic Response Certification
        ctx.canonical_state = canonical_state
        ctx.evidence_items = evidence_items
        ctx.active_hazards = hazards
        ctx.risk_score = risk_score
        ctx.decision_support = decision_support

        passed_cert, certificate = self.certifier.verify_and_certify(
            context=ctx,
            response_text=sanitized_text,
        )
        result.certificate = certificate.dict()
        result.reproducibility_hash = certificate.reproducibility_hash

        return result
