"""Climate Explanation Bridge.

Connects deterministic ClimateEvidence to Gemma 4:e2b for conversational,
natural-language explanations.

Non-negotiable invariants:
1. Deterministic ClimateEvidence is the sole source of climatological truth.
2. Gemma explains verified statistics; Gemma never calculates or invents historical baselines.
3. If baseline is unavailable, Gemma must state it is unavailable.
4. If Gemma hallucinates a contradiction or fails/times out, system falls back to a deterministic explanation.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Optional, Tuple

from app.climate.models import (
    AnomalyCategory,
    ClimateAnomalyResult,
    ClimateEvidence,
    DataQuality,
    TrendDirection,
)
from app.config import Settings, settings as default_settings
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole

logger = logging.getLogger(__name__)


def generate_deterministic_fallback_explanation(
    evidence: ClimateEvidence,
    anomaly: Optional[ClimateAnomalyResult] = None,
) -> str:
    """Produces a clean, deterministic natural-language summary without calling the LLM."""
    parts = []

    # 1. Headline summary
    if evidence.variable in ("temperature", "max_temperature", "min_temperature"):
        mean_str = f"{evidence.mean:.1f}°C" if evidence.mean is not None else "N/A"
        min_str = f"{evidence.min:.1f}°C" if evidence.min is not None else "N/A"
        max_str = f"{evidence.max:.1f}°C" if evidence.max is not None else "N/A"
        parts.append(
            f"Over the period from {evidence.period_start} to {evidence.period_end}, {evidence.location} recorded "
            f"an average temperature of {mean_str} (ranging from a minimum of {min_str} to a maximum of {max_str})."
        )
        if evidence.temperature_metrics and evidence.temperature_metrics.is_heatwave:
            parts.append(f"Official criteria evaluation: {evidence.temperature_metrics.heatwave_criteria}.")

    elif evidence.variable == "rainfall":
        cum_str = f"{evidence.cumulative:.1f} mm" if evidence.cumulative is not None else "N/A"
        avg_str = f"{evidence.mean:.1f} mm/day" if evidence.mean is not None else "N/A"
        parts.append(
            f"Between {evidence.period_start} and {evidence.period_end}, {evidence.location} received a cumulative rainfall "
            f"of {cum_str} (averaging {avg_str})."
        )
        if evidence.rainfall_metrics:
            rm = evidence.rainfall_metrics
            parts.append(
                f"Rain fell on {rm.rainy_days_count} wet days (>=1.0 mm), including {rm.heavy_rain_days_r10mm} heavy rain days (>=10.0 mm). "
                f"The longest consecutive dry spell lasted {rm.consecutive_dry_days} days."
            )
    else:
        parts.append(
            f"Climate analysis for {evidence.location} over {evidence.period_start} to {evidence.period_end} "
            f"based on {evidence.sample_size} valid observations."
        )

    # 2. Anomaly & Baseline evaluation
    if anomaly and anomaly.baseline_available and anomaly.baseline_value is not None:
        sign = "+" if (anomaly.absolute_anomaly or 0.0) > 0 else ""
        pct_clause = f" ({sign}{anomaly.anomaly_percent:.1f}%)" if anomaly.anomaly_percent is not None else ""
        parts.append(
            f"Compared to the historical baseline normal of {anomaly.baseline_value:.1f} {evidence.units} "
            f"({anomaly.baseline_period or 'reference period'}, {anomaly.baseline_source or 'Official Climatology'}), "
            f"the observed value shows a departure of {sign}{anomaly.absolute_anomaly:.1f} {evidence.units}{pct_clause}, "
            f"classified as {anomaly.category.value}."
        )
    else:
        parts.append(
            "Historical climatological baseline is unavailable for this specific location/period; "
            "therefore, departures from normal cannot be computed."
        )

    # 3. Trend evaluation
    if evidence.trend and evidence.trend.direction != TrendDirection.INSUFFICIENT_DATA:
        t = evidence.trend
        if t.direction == TrendDirection.INCREASING:
            trend_desc = f"a statistically significant upward trend (+{t.slope:.4f} {evidence.units}/period, p={t.p_value:.4f})"
        elif t.direction == TrendDirection.DECREASING:
            trend_desc = f"a statistically significant downward trend ({t.slope:.4f} {evidence.units}/period, p={t.p_value:.4f})"
        else:
            trend_desc = "no statistically significant monotonic trend (stable pattern)"
        parts.append(f"Statistical Mann-Kendall trend analysis indicates {trend_desc}.")

    # 4. Uncertainty & Quality notes
    if evidence.quality != DataQuality.VALID or evidence.uncertainty:
        notes = "; ".join(evidence.uncertainty[:2]) if evidence.uncertainty else f"Coverage: {evidence.coverage_pct}%"
        parts.append(f"Data caveats: {notes}.")

    return " ".join(parts)


class ClimateExplanationBridge:
    """Bridge for generating natural-language explanations of verified ClimateEvidence via Gemma 4:e2b."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.settings = settings or default_settings

    def _build_grounding_prompt(
        self,
        evidence: ClimateEvidence,
        anomaly: Optional[ClimateAnomalyResult] = None,
    ) -> str:
        """Constructs a structured, verified evidence prompt with strict negative boundaries."""
        prompt_lines = [
            "VERIFIED CLIMATE INTELLIGENCE EVIDENCE",
            "========================================",
            f"Location: {evidence.location}",
            f"Variable: {evidence.variable.upper()}",
            f"Units: {evidence.units}",
            f"Period: {evidence.period_start} to {evidence.period_end}",
            f"Valid Observations Count: {evidence.sample_size}",
            f"Coverage Percentage: {evidence.coverage_pct}% ({evidence.quality.value})",
        ]

        if evidence.variable in ("temperature", "max_temperature", "min_temperature"):
            prompt_lines.extend([
                f"Observed Mean: {evidence.mean:.2f} {evidence.units}" if evidence.mean is not None else "Observed Mean: N/A",
                f"Observed Min: {evidence.min:.2f} {evidence.units}" if evidence.min is not None else "Observed Min: N/A",
                f"Observed Max: {evidence.max:.2f} {evidence.units}" if evidence.max is not None else "Observed Max: N/A",
            ])
            if evidence.temperature_metrics:
                tm = evidence.temperature_metrics
                prompt_lines.append(f"Heatwave Status: {'YES - ' + tm.heatwave_criteria if tm.is_heatwave else 'NO'}")

        elif evidence.variable == "rainfall":
            prompt_lines.extend([
                f"Cumulative Rainfall: {evidence.cumulative:.2f} {evidence.units}" if evidence.cumulative is not None else "Cumulative Rainfall: N/A",
                f"Daily Average: {evidence.mean:.2f} {evidence.units}/day" if evidence.mean is not None else "Daily Average: N/A",
            ])
            if evidence.rainfall_metrics:
                rm = evidence.rainfall_metrics
                prompt_lines.extend([
                    f"Rainy Days (>=1.0 mm): {rm.rainy_days_count}",
                    f"IMD Rainy Days (>=2.5 mm): {rm.imd_rainy_days_count}",
                    f"Consecutive Dry Days (CDD): {rm.consecutive_dry_days}",
                    f"Consecutive Wet Days (CWD): {rm.consecutive_wet_days}",
                    f"Heavy Rain Days (>=10.0 mm): {rm.heavy_rain_days_r10mm}",
                    f"Rx1day Max Precipitation: {rm.max_1day_precipitation_rx1day_mm:.2f} mm",
                ])

        # Baseline & Anomaly section
        if anomaly and anomaly.baseline_available and anomaly.baseline_value is not None:
            sign = "+" if (anomaly.absolute_anomaly or 0.0) > 0 else ""
            prompt_lines.extend([
                "BASELINE & DEPARTURE:",
                f"  Baseline Normal Value: {anomaly.baseline_value:.2f} {evidence.units}",
                f"  Baseline Reference Period: {anomaly.baseline_period or '1991-2020'}",
                f"  Baseline Source: {anomaly.baseline_source or 'Official Meteorological Archive'}",
                f"  Absolute Anomaly: {sign}{anomaly.absolute_anomaly:.2f} {evidence.units}",
                f"  Anomaly Percentage: {f'{sign}{anomaly.anomaly_percent:.1f}%' if anomaly.anomaly_percent is not None else 'N/A'}",
                f"  Standardized Z-Score: {f'{anomaly.z_score:.2f}σ' if anomaly.z_score is not None else 'N/A'}",
                f"  WMO Classification: {anomaly.category.value}",
            ])
        else:
            prompt_lines.extend([
                "BASELINE & DEPARTURE:",
                "  Baseline Available: FALSE (Historical climatological normal is unavailable for this station/month)",
                "  Anomaly Calculation: UNAVAILABLE",
            ])

        # Trend section
        if evidence.trend:
            t = evidence.trend
            prompt_lines.extend([
                "MONOTONIC TREND TEST (Mann-Kendall & Sen's Slope):",
                f"  Direction: {t.direction.value}",
                f"  Sen's Slope: {f'{t.slope:.4f} {evidence.units}/period' if t.slope is not None else 'N/A'}",
                f"  P-Value: {f'{t.p_value:.4f}' if t.p_value is not None else 'N/A'}",
                f"  Statistically Significant: {t.is_significant}",
            ])

        if evidence.uncertainty:
            prompt_lines.extend([
                "DATA LIMITATIONS & UNCERTAINTIES:",
                *[f"  - {u}" for u in evidence.uncertainty],
            ])

        prompt_lines.extend([
            "",
            "EXPLANATION RULES (STRICT):",
            "1. You are Vayubodhak's Climate Explanation Assistant. You are NOT the climate calculator.",
            "2. Explain this verified climate evidence clearly in natural language for the user.",
            "3. Do not modify, invent, or round away the numerical values and units above.",
            "4. If 'Baseline Available: FALSE', you MUST explicitly explain that historical baseline data is unavailable; NEVER invent a normal value.",
            "5. If WRF or another model is not mentioned, do NOT invent model consensus.",
            "6. Never contradict the verified WMO classification or trend direction.",
            "7. Explain any data limitations or coverage gaps honestly.",
        ])

        return "\n".join(prompt_lines)

    def _check_contradiction(
        self,
        explanation_text: str,
        evidence: ClimateEvidence,
        anomaly: Optional[ClimateAnomalyResult] = None,
    ) -> bool:
        """Lightweight contradiction guard to catch obvious halluncinations."""
        text_lower = explanation_text.lower()

        # 1. Check baseline hallucination when baseline is unavailable
        if anomaly and not anomaly.baseline_available:
            if re.search(r"normal is \d+(\.\d+)?", text_lower) or re.search(r"average of \d+(\.\d+)? (degrees|°c|mm) historically", text_lower):
                logger.warning("Contradiction guard: LLM invented a historical baseline when none was available.")
                return True

        # 2. Check anomaly sign contradiction
        if anomaly and anomaly.baseline_available and anomaly.absolute_anomaly is not None:
            if anomaly.category in (AnomalyCategory.SEVERELY_ABOVE_NORMAL, AnomalyCategory.ABOVE_NORMAL):
                if "cooler than normal" in text_lower or "below normal" in text_lower or "colder than normal" in text_lower:
                    logger.warning("Contradiction guard: LLM reported 'below normal' for positive anomaly.")
                    return True
            elif anomaly.category in (AnomalyCategory.SEVERELY_BELOW_NORMAL, AnomalyCategory.BELOW_NORMAL):
                if "warmer than normal" in text_lower or "above normal" in text_lower or "hotter than normal" in text_lower:
                    logger.warning("Contradiction guard: LLM reported 'above normal' for negative anomaly.")
                    return True

        # 3. Check trend contradiction
        if evidence.trend:
            if evidence.trend.direction == TrendDirection.INCREASING and "decreasing trend" in text_lower:
                logger.warning("Contradiction guard: LLM reported 'decreasing trend' for increasing trend.")
                return True
            elif evidence.trend.direction == TrendDirection.DECREASING and "increasing trend" in text_lower:
                logger.warning("Contradiction guard: LLM reported 'increasing trend' for decreasing trend.")
                return True

        return False

    async def explain_climate(
        self,
        evidence: ClimateEvidence,
        anomaly: Optional[ClimateAnomalyResult] = None,
    ) -> Tuple[str, str]:
        """Generates an explanation using Gemma 4:e2b with fail-safe fallback."""
        if self.llm_provider is None:
            logger.info("ClimateExplanationBridge: LLMProvider not provided; using deterministic fallback.")
            return generate_deterministic_fallback_explanation(evidence, anomaly), "deterministic_fallback"

        prompt = self._build_grounding_prompt(evidence, anomaly)
        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "You are Vayubodhak's Climate Explanation Assistant. You explain verified climate-analysis "
                    "results conversationally to the user. You are NOT the climate-data source and you are NOT the calculator. "
                    "You strictly preserve all numbers, units, baseline statuses, and uncertainties provided."
                ),
            ),
            ChatMessage(role=ChatRole.USER, content=prompt),
        ]

        try:
            response = await self.llm_provider.generate_chat_completion(
                messages=messages,
                tools=None,
                temperature=0.1,
            )

            candidate_explanation = (response.content or "").strip()
            if not candidate_explanation:
                logger.warning("ClimateExplanationBridge: Empty response from LLM; using deterministic fallback.")
                return generate_deterministic_fallback_explanation(evidence, anomaly), "deterministic_fallback"

            if self._check_contradiction(candidate_explanation, evidence, anomaly):
                logger.warning("ClimateExplanationBridge: Contradiction detected in LLM explanation; reverting to fallback.")
                return generate_deterministic_fallback_explanation(evidence, anomaly), "deterministic_fallback"

            return candidate_explanation, "gemma4:e2b"

        except Exception as e:
            logger.warning("ClimateExplanationBridge: LLM inference failed (%s); using deterministic fallback.", e)
            return generate_deterministic_fallback_explanation(evidence, anomaly), "deterministic_fallback"
