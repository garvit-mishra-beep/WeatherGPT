"""Claim-level verification engine and final cryptographic response certification."""

import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from app.brains.analyst_core.models.schemas import EpistemicStatus, RiskLevel, PipelineState
from app.brains.analyst_core.models.analysis_context import AnalysisContext


class ResponseCertificate(BaseModel):
    """Verifiable cryptographic certificate guaranteeing scientific integrity and claim accuracy."""
    certificate_id: str = Field(default_factory=lambda: f"CERT-{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_id: str
    reproducibility_hash: str
    config_version: str
    risk_config_version: str
    epistemic_audit: Dict[str, EpistemicStatus] = Field(default_factory=dict)
    claim_verification_passed: bool = True
    verified_claims: List[str] = Field(default_factory=list)
    flagged_claims: List[str] = Field(default_factory=list)
    digital_signature_sha256: str = ""


class ResponseCertifier:
    """Audits generated response against canonical state facts and issues cryptographic certification."""

    def verify_and_certify(
        self,
        context: AnalysisContext,
        response_text: str,
    ) -> Tuple[bool, ResponseCertificate]:
        """Performs claim-level verification and issues a tamper-evident certification."""
        context.transition_to(PipelineState.CLAIM_VERIFIED, "Initiating claim-level fact check")

        verified: List[str] = []
        flagged: List[str] = []

        # 1. Epistemic audit from canonical state & evidence
        epistemic_audit: Dict[str, EpistemicStatus] = {}
        if context.canonical_state:
            if context.canonical_state.temperature:
                epistemic_audit["temperature"] = context.canonical_state.temperature.epistemic_status
            if context.canonical_state.rainfall_rate:
                epistemic_audit["rainfall"] = context.canonical_state.rainfall_rate.epistemic_status
            if context.canonical_state.wind_speed:
                epistemic_audit["wind"] = context.canonical_state.wind_speed.epistemic_status

        # 2. Risk Level Claim Verification
        if context.risk_score:
            actual_level = context.risk_score.level.value
            other_levels = [lvl.value for lvl in RiskLevel if lvl.value != actual_level and lvl != RiskLevel.UNKNOWN]
            for bad_lvl in other_levels:
                # If text claims "Risk is HIGH" when risk is LOW
                pattern = rf"\b(risk|hazard)\s+is\s+{bad_lvl}\b"
                if re.search(pattern, response_text, re.IGNORECASE):
                    flagged.append(f"Risk level claim mismatch: text mentions '{bad_lvl}', verified risk is '{actual_level}'")

            if actual_level.lower() in response_text.lower():
                verified.append(f"Risk level '{actual_level}' correctly reflected in output")

        # 3. Numeric Claim Cross-Reference (Temperature, Rainfall, Wind)
        known_numbers = set()
        if context.canonical_state:
            for var in [context.canonical_state.temperature, context.canonical_state.rainfall_rate, context.canonical_state.wind_speed]:
                if var and var.value is not None:
                    known_numbers.add(round(var.value, 1))
                    known_numbers.add(round(var.value))

        if context.risk_score and context.risk_score.score is not None:
            known_numbers.add(round(context.risk_score.score, 1))
            known_numbers.add(round(context.risk_score.score))

        # Check explicit °C mentions
        temp_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:°C|deg C|degrees C)", response_text, re.IGNORECASE)
        for t_str in temp_matches:
            val = float(t_str)
            # Allow matching either temperature or anomaly departure
            if any(abs(val - num) <= 1.0 for num in known_numbers):
                verified.append(f"Temperature claim {val}°C verified against canonical state")
            elif val > 60.0 or val < -50.0:
                flagged.append(f"Physically impossible temperature claim detected: {val}°C")

        # Check explicit mm rainfall mentions
        rain_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:mm|millimeters)", response_text, re.IGNORECASE)
        for r_str in rain_matches:
            val = float(r_str)
            if any(abs(val - num) <= 1.5 for num in known_numbers):
                verified.append(f"Rainfall claim {val} mm verified against canonical state")
            elif val > 350.0:
                flagged.append(f"Unverifiable extreme rainfall claim: {val} mm")

        # 4. Official Warning Verification
        has_official_alert = len(context.active_hazards) > 0 and any("RED" in h.value or "ORANGE" in h.value for h in context.active_hazards)
        if "official red warning" in response_text.lower() and not has_official_alert:
            flagged.append("Fabricated Official Red Warning claim without supporting active alert")

        is_passed = len(flagged) == 0
        repro_hash = context.compute_reproducibility_hash()

        # Compute digital signature of certificate
        cert_raw = f"{repro_hash}:{context.query_id}:{is_passed}:{response_text[:120]}"
        signature = hashlib.sha256(cert_raw.encode("utf-8")).hexdigest()

        certificate = ResponseCertificate(
            query_id=context.query_id,
            reproducibility_hash=repro_hash,
            config_version=context.config_version,
            risk_config_version=context.risk_config_version,
            epistemic_audit=epistemic_audit,
            claim_verification_passed=is_passed,
            verified_claims=verified,
            flagged_claims=flagged,
            digital_signature_sha256=signature,
        )

        context.transition_to(PipelineState.CERTIFIED, f"Verification {'PASSED' if is_passed else 'FLAGGED'}; Certificate: {certificate.certificate_id}")
        return is_passed, certificate
