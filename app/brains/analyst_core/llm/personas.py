"""Persona-based formatting templates for General User, Analyst, and Emergency Manager."""

from typing import List, Dict, Any
from app.brains.analyst_core.models.schemas import Persona, RiskLevel, ConfidenceLevel
from app.brains.analyst_core.models.analyst_result import AnalystResult


class PersonaFormatter:
    """Formats structured AnalystResult into calibrated persona-specific responses."""

    def format_for_persona(
        self,
        result: AnalystResult,
        persona: Persona = Persona.ANALYST,
        language: str = "en",
    ) -> str:
        """Renders natural language explanation based on target user persona and language."""
        if result.is_clarification_needed and result.clarification_prompt:
            return result.clarification_prompt

        if persona == Persona.GENERAL_USER:
            return self._format_general_user(result, language)
        elif persona == Persona.EMERGENCY_MANAGER:
            return self._format_emergency_manager(result, language)
        else:
            return self._format_analyst(result, language)

    def _format_general_user(self, res: AnalystResult, lang: str) -> str:
        """Clean, accessible explanation without dense technical jargon."""
        loc = res.location or "the specified area"
        risk = res.risk_level.value
        findings = res.recommendation or "No severe weather disruptions are expected."

        impact_text = ""
        if res.potential_impacts:
            lead = res.potential_impacts[0]
            impact_text = f"\n**Possible Impact:** {lead.potential_impact}"

        warnings_text = ""
        if res.official_warnings:
            w = res.official_warnings[0]
            warnings_text = f"\n**Official Alert:** {w.headline} issued by {w.issuing_authority}."

        conf_text = f"Confidence: {res.confidence.value.capitalize()}"

        if lang == "hi":
            return (
                f"### {loc} के लिए मौसम विश्लेषण\n\n"
                f"- **मौसम की स्थिति:** {res.time_period}\n"
                f"- **जोखिम स्तर:** {risk}\n"
                f"- **सिफारिश:** {findings}\n"
                f"{warnings_text}\n"
                f"{impact_text}\n\n"
                f"*विश्वसनीयता: {res.confidence.value}*"
            )

        return (
            f"### Weather Assessment for {loc}\n\n"
            f"**Situation:** Weather analysis for {res.time_period}.\n"
            f"**Risk Level:** **{risk}**\n"
            f"**Recommendation:** {findings}\n"
            f"{warnings_text}"
            f"{impact_text}\n\n"
            f"*Forecast confidence is {res.confidence.value.lower()}. Please check official advisories for real-time updates.*"
        )

    def _format_emergency_manager(self, res: AnalystResult, lang: str) -> str:
        """Prioritizes Hazard, Severity, Geographic Area, Timing, Exposure, Actions."""
        loc = res.location or "Area of Operation"
        hazards_str = ", ".join(h.value for h in res.hazards)

        actions = "\n".join(f"- {a}" for a in res.monitoring_advice) if res.monitoring_advice else "- Maintain standard surveillance."

        impacts = "\n".join(f"- **{i.sector.upper()}**: {i.potential_impact} (Severity: {i.severity})" for i in res.potential_impacts)
        if not impacts:
            impacts = "- None reported above operational concern thresholds."

        warning_block = ""
        if res.official_warnings:
            w = res.official_warnings[0]
            warning_block = (
                f"> **MANDATORY OFFICIAL ADVISORY ({w.issuing_authority})**\n"
                f"> **Severity:** {w.severity.value}\n"
                f"> **Headline:** {w.headline}\n"
                f"> **Valid:** {w.valid_from} to {w.valid_to}\n\n"
            )

        return (
            f"## [EMERGENCY MANAGEMENT BRIEFING] {loc.upper()}\n\n"
            f"{warning_block}"
            f"- **PRIMARY HAZARDS:** {hazards_str}\n"
            f"- **OVERALL RISK TIER:** **{res.risk_level.value}** "
            f"({'Score: ' + str(res.risk_score.score) + '/100' if res.risk_score and res.risk_score.score is not None else 'Unquantified'})\n"
            f"- **TEMPORAL WINDOW:** {res.time_period}\n"
            f"- **DATA CONFIDENCE:** {res.confidence.value}\n\n"
            f"### Sector Vulnerability & Potential Impacts\n{impacts}\n\n"
            f"### Operational Directives & Monitoring\n{actions}\n\n"
            f"**Primary Action:** {res.recommendation}"
        )

    def _format_analyst(self, res: AnalystResult, lang: str) -> str:
        """Complete 8-part structured technical response with metrics and provenance."""
        loc = res.location or "Target Location"
        hazards_str = ", ".join(h.value for h in res.hazards)

        # 1. Situation
        situation = f"Synoptic evaluation for {loc} covering temporal horizon: {res.time_period}."

        # 2. Key Findings
        findings = []
        if res.hazards and res.hazards != ["NONE"]:
            findings.append(f"Identified hazard signatures: {hazards_str}")
        if res.observations:
            obs = min(res.observations, key=lambda o: abs((o.timestamp - res.created_at).total_seconds()))
            findings.append(
                f"Station observation ({obs.source}): Temp {obs.temperature_c}°C, "
                f"Rainfall {obs.rainfall_mm} mm, Wind {obs.wind_speed_kmh} km/h."
            )
        if res.forecast:
            f_lead = min(res.forecast, key=lambda f: abs((f.valid_time - res.created_at).total_seconds()))
            findings.append(
                f"NWP Model output ({f_lead.model_name}): Peak precipitation probability {f_lead.precipitation_prob_pct}%."
            )

        findings_str = "\n".join(f"- {f}" for f in findings) if findings else "- Nominal atmospheric baseline parameters."

        # 3. Risk Level & Breakdown
        risk_str = f"**{res.risk_level.value}**"
        if res.risk_score and res.risk_score.score is not None:
            bd = res.risk_score.breakdown
            exp_str = f"{bd.exposure_score:.1f}" if bd.exposure_score is not None else "Unspecified"
            vuln_str = f"{bd.vulnerability_score:.1f}" if bd.vulnerability_score is not None else "Unspecified"
            bounds_str = f" [{res.risk_score.score_min}-{res.risk_score.score_max}]" if res.risk_score.score_min is not None else ""
            risk_str += (
                f" (Score: {res.risk_score.score}/100{bounds_str} | Hazard: {bd.hazard_severity:.1f}, "
                f"Exposure: {exp_str}, Vulnerability: {vuln_str})"
            )

        # 4. Evidence
        ev_lines = []
        for ev in res.evidence[:4]:
            ev_lines.append(f"- **[{ev.data_type.value}] {ev.source}**: {ev.result} (Method: {ev.method})")
        ev_str = "\n".join(ev_lines) if ev_lines else "- Direct in-situ and NWP telemetry records."

        # 5. Potential Impact
        impact_lines = []
        for imp in res.potential_impacts:
            impact_lines.append(f"- **{imp.sector.title()}**: {imp.potential_impact} *(Potential, verified_actual={imp.verified_actual})*")
        impact_str = "\n".join(impact_lines) if impact_lines else "- No severe sector-level impacts flagged above baseline."

        # 6. Recommendation
        rec = res.recommendation or "Maintain standard meteorological monitoring."

        # 7. Uncertainty & Limitations
        unc_lines = []
        for u in res.uncertainty:
            unc_lines.append(f"- **{u.source}** ({u.magnitude}): {u.description}")
        for lim in res.limitations[:2]:
            unc_lines.append(f"- *Limitation*: {lim}")
        unc_str = "\n".join(unc_lines) if unc_lines else "- Normal instrument measurement tolerances."

        # 8. Source & Data Information
        sources = list({ev.source for ev in res.evidence}) if res.evidence else ["Calibrated Meteorological Services"]
        source_str = f"Data Providers: {', '.join(sources)} | Freshness Status: {res.data_freshness_status}"

        # Decision support if present
        ds_block = ""
        if res.decision_support:
            ds_block = (
                f"\n### Decision Assessment ({res.decision_support.objective.title()})\n"
                f"- **Verdict:** **{res.decision_support.outcome.value}**\n"
                f"- **Rationale:** {res.decision_support.justification}\n"
            )

        return (
            f"## Weather Intelligence Analysis: {loc}\n\n"
            f"### 1. Situation\n{situation}\n\n"
            f"### 2. Key Findings\n{findings_str}\n\n"
            f"### 3. Risk Level\n{risk_str}\n\n"
            f"### 4. Evidence\n{ev_str}\n\n"
            f"### 5. Potential Impact\n{impact_str}\n\n"
            f"{ds_block}"
            f"### 6. Operational Recommendations\n{rec}\n\n"
            f"### 7. Uncertainty & Limitations\n{unc_str}\n\n"
            f"### 8. Data Provenance & Freshness\n{source_str}\n"
        )
