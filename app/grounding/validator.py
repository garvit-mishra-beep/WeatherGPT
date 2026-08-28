"""Deterministic grounding validator verifying claims against authoritative EvidencePackage."""

import logging
from typing import Any, Dict, List, Optional

from app.contracts.evidence import EvidencePackage
from app.grounding.models import (
    ClaimStatus,
    ClaimType,
    GroundedClaim,
    GroundingValidationResult,
)

logger = logging.getLogger(__name__)

# Numeric verification tolerances from docs/15_ERROR_GUARDRAILS.md
TEMP_TOLERANCE_C = 0.5
RAIN_TOLERANCE_MM = 1.0
HUMIDITY_TOLERANCE_PCT = 5.0
WIND_TOLERANCE_KMH = 5.0
PROB_TOLERANCE_PCT = 5.0


class GroundingValidator:
    """Validates extracted factual claims against an injected EvidencePackage."""

    @classmethod
    def validate_claims(
        cls,
        claims: List[GroundedClaim],
        evidence: EvidencePackage,
        response_text: str = "",
    ) -> GroundingValidationResult:
        """Cross-checks each claim against tool results, official alerts, and provenance in evidence.

        Args:
            claims: List of atomic claims extracted from generated output.
            evidence: Verified EvidencePackage received from deterministic tools.
            response_text: Full generated response text.

        Returns:
            GroundingValidationResult: Detailed validation outcome with contradiction/unsupported lists.
        """
        validated_claims: List[GroundedClaim] = []
        contradictions: List[str] = []
        unsupported: List[str] = []

        # Flatten tool results dictionary for numerical lookup
        tool_data = evidence.tool_results or {}
        provenance_sources = {p.dataset.upper() for p in evidence.provenance if p.dataset}
        provenance_authorities = {p.authority.upper() for p in evidence.provenance if p.authority}
        all_sources = provenance_sources.union(provenance_authorities)

        # Official alerts
        active_alert_levels = {a.warning_level.value.lower() for a in evidence.official_alerts}

        for claim in claims:
            # 1. Temperature Claims
            if claim.claim_type == ClaimType.TEMPERATURE:
                allowed_temps = []
                for k, v in tool_data.items():
                    if isinstance(v, (int, float)) and any(t_key in k.lower() for t_key in ["temp", "t_max", "t_min"]):
                        allowed_temps.append(float(v))
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, (int, float)) and any(t_key in sub_k.lower() for t_key in ["temp", "t_max", "t_min"]):
                                allowed_temps.append(float(sub_v))

                if not allowed_temps:
                    unsupported.append(f"Temperature claim {claim.value}°C with no temperature evidence.")
                    validated_claims.append(claim.model_copy(update={"status": ClaimStatus.UNSUPPORTED}))
                else:
                    matches = any(abs(claim.value - t) <= TEMP_TOLERANCE_C for t in allowed_temps)
                    if matches:
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))
                    else:
                        contradictions.append(
                            f"Temperature {claim.value}°C contradicts evidence values {allowed_temps} (tolerance ±{TEMP_TOLERANCE_C}°C)."
                        )
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.CONTRADICTED}))

            # 2. Rainfall Claims
            elif claim.claim_type == ClaimType.RAINFALL:
                allowed_rain = []
                for k, v in tool_data.items():
                    if isinstance(v, (int, float)) and any(r_key in k.lower() for r_key in ["rain", "precip"]):
                        allowed_rain.append(float(v))
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, (int, float)) and any(r_key in sub_k.lower() for r_key in ["rain", "precip"]):
                                allowed_rain.append(float(sub_v))

                if not allowed_rain:
                    unsupported.append(f"Rainfall claim {claim.value} mm with no rainfall evidence.")
                    validated_claims.append(claim.model_copy(update={"status": ClaimStatus.UNSUPPORTED}))
                else:
                    matches = any(abs(claim.value - r) <= RAIN_TOLERANCE_MM for r in allowed_rain)
                    if matches:
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))
                    else:
                        contradictions.append(
                            f"Rainfall {claim.value} mm contradicts evidence values {allowed_rain} (tolerance ±{RAIN_TOLERANCE_MM} mm)."
                        )
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.CONTRADICTED}))

            # 3. Humidity Claims
            elif claim.claim_type == ClaimType.HUMIDITY:
                allowed_hum = []
                for k, v in tool_data.items():
                    if isinstance(v, (int, float)) and "humid" in k.lower():
                        allowed_hum.append(float(v))
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, (int, float)) and "humid" in sub_k.lower():
                                allowed_hum.append(float(sub_v))

                if not allowed_hum:
                    unsupported.append(f"Humidity claim {claim.value}% with no humidity evidence.")
                    validated_claims.append(claim.model_copy(update={"status": ClaimStatus.UNSUPPORTED}))
                else:
                    matches = any(abs(claim.value - h) <= HUMIDITY_TOLERANCE_PCT for h in allowed_hum)
                    if matches:
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))
                    else:
                        contradictions.append(f"Humidity {claim.value}% contradicts evidence {allowed_hum}.")
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.CONTRADICTED}))

            # 4. Official Warning Level Claims
            elif claim.claim_type == ClaimType.WARNING_LEVEL:
                claimed_level = str(claim.value).lower()
                if not active_alert_levels:
                    if claimed_level != "green":
                        unsupported.append(f"Claimed official warning '{claim.value}' when no official alert exists in evidence.")
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.UNSUPPORTED}))
                    else:
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))
                else:
                    if claimed_level in active_alert_levels:
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))
                    else:
                        contradictions.append(
                            f"Claimed warning '{claim.value}' alters official alert level '{list(active_alert_levels)}'."
                        )
                        validated_claims.append(claim.model_copy(update={"status": ClaimStatus.CONTRADICTED}))

            # 5. Source Provenance Claims
            elif claim.claim_type == ClaimType.SOURCE:
                src_val = str(claim.value).upper()
                # Check official alerts source or provenance
                alert_sources = {a.source.upper() for a in evidence.official_alerts if a.source}
                valid_sources = all_sources.union(alert_sources)

                if any(src_val in s for s in valid_sources):
                    validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))
                else:
                    unsupported.append(f"Fabricated source '{claim.value}' not present in evidence provenance {list(valid_sources)}.")
                    validated_claims.append(claim.model_copy(update={"status": ClaimStatus.UNSUPPORTED}))

            else:
                validated_claims.append(claim.model_copy(update={"status": ClaimStatus.SUPPORTED}))

        is_grounded = len(contradictions) == 0 and len(unsupported) == 0

        return GroundingValidationResult(
            is_grounded=is_grounded,
            claims=validated_claims,
            contradictions=contradictions,
            unsupported_claims=unsupported,
            requires_regeneration=not is_grounded,
        )
