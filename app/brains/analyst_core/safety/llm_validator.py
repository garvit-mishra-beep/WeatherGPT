"""LLM Output Validator: Post-generation deterministic verification firewall."""

import re
from typing import Tuple, List, Optional
from app.brains.analyst_core.models.schemas import RiskLevel
from app.brains.analyst_core.models.analyst_result import AnalystResult
from app.brains.analyst_core.llm.personas import PersonaFormatter


class LLMOutputValidator:
    """Verifies that LLM explanations do not hallucinate numbers, warnings, or risk tiers.
    
    SCIENTIFIC INTEGRITY RULE:
    If the LLM text contradicts deterministic calculations, it is rejected and replaced
    by the certified deterministic explanation.
    """

    def __init__(self):
        self.formatter = PersonaFormatter()

    def validate_and_sanitize(
        self,
        candidate_text: str,
        result: AnalystResult,
        tolerance: float = 2.0,
    ) -> Tuple[bool, List[str], str]:
        """Validates candidate LLM text against AnalystResult.
        
        Returns:
            (is_valid, violation_flags, final_safe_text)
        """
        violations: List[str] = []
        lower_text = candidate_text.lower()

        # 1. Risk Tier Consistency Check
        all_risk_levels = [r.value for r in RiskLevel if r != RiskLevel.UNKNOWN]
        claimed_risks = [r for r in all_risk_levels if f"risk: {r.lower()}" in lower_text or f"risk level: {r.lower()}" in lower_text or f"**{r.lower()}**" in lower_text]

        if claimed_risks:
            expected_risk = result.risk_level.value
            for claimed in claimed_risks:
                if claimed != expected_risk:
                    violations.append(
                        f"RISK_CONTRADICTION: LLM text claimed risk level '{claimed}', but deterministic analysis computed '{expected_risk}'."
                    )

        # 2. Warning Hallucination Check
        has_official_warning_claims = any(
            phrase in lower_text
            for phrase in ["official red alert is in effect", "imd has issued an official red warning", "official cyclone warning declared"]
        )
        if has_official_warning_claims and not result.official_warnings:
            violations.append(
                "WARNING_HALLUCINATION: LLM text claimed an official alert is in effect, but no verified official alerts exist."
            )

        # 3. Numerical Plausibility Check (Rainfall & Temperature)
        ground_temps = []
        ground_rains = []
        for o in result.observations:
            if o.temperature_c is not None:
                ground_temps.append(o.temperature_c)
            if o.rainfall_mm is not None:
                ground_rains.append(o.rainfall_mm)
        for f in result.forecast:
            if f.temperature_c is not None:
                ground_temps.append(f.temperature_c)
            if f.rainfall_mm is not None:
                ground_rains.append(f.rainfall_mm)

        # Extract temperature mentions like '35°c', '42 c'
        temp_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:°c|\bc\b)", candidate_text, re.IGNORECASE)
        for t_str in temp_matches:
            val = float(t_str)
            # Skip climatological references like normal temp
            if ground_temps:
                min_t = min(ground_temps) - tolerance
                max_t = max(ground_temps) + tolerance
                # If temperature mentioned is way outside range (e.g. 60°C when actual is 25°C)
                if val < -10.0 or val > 65.0:
                    violations.append(f"UNPHYSICAL_NUMBER_HALLUCINATION: Temperature {val}°C outside plausible physical limits.")
                elif val > max_t + 15.0 or val < min_t - 15.0:
                    violations.append(f"NUMERICAL_HALLUCINATION: Temperature {val}°C not supported by observations/forecasts [{min_t:.1f}, {max_t:.1f}].")

        # Extract rainfall mentions like '150 mm'
        rain_matches = re.findall(r"(\d+(?:\.\d+)?)\s*mm\b", candidate_text, re.IGNORECASE)
        for r_str in rain_matches:
            val = float(r_str)
            if ground_rains:
                max_r = max(ground_rains) * 2.0 + 10.0
                if val > max_r + 50.0:
                    violations.append(f"NUMERICAL_HALLUCINATION: Rainfall {val} mm exceeds verified forecast/observation upper bound.")

        is_valid = len(violations) == 0

        if not is_valid:
            # Automatic fallback to deterministic certified text
            certified_text = self.formatter.format_for_persona(result)
            return False, violations, certified_text

        return True, [], candidate_text
