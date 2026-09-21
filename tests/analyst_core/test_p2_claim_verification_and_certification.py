"""Unit tests for P2 features: Claim-level LLM verification, cryptographic response certification,
epistemic status taxonomy audit, and reproducibility tracking."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import RiskLevel, EpistemicStatus
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState, CanonicalWeatherVariable
from app.brains.analyst_core.models.risk_model import RiskScore, RiskBreakdown
from app.brains.analyst_core.models.analysis_context import AnalysisContext
from app.brains.analyst_core.safety.certifier import ResponseCertifier


def test_p2_claim_verification_passes_compliant_response():
    """P2.1: Verifies ResponseCertifier passes when claims match canonical state."""
    certifier = ResponseCertifier()
    now = datetime.utcnow()

    ctx = AnalysisContext(location_name="Gwalior")
    ctx.canonical_state = CanonicalWeatherState(
        location="Gwalior",
        target_time=now,
        temperature=CanonicalWeatherVariable(
            name="temperature",
            value=34.5,
            unit="°C",
            epistemic_status=EpistemicStatus.OBSERVED,
        ),
        rainfall=CanonicalWeatherVariable(
            name="rainfall",
            value=0.0,
            unit="mm",
            epistemic_status=EpistemicStatus.OBSERVED,
        ),
    )
    ctx.risk_score = RiskScore(
        score=25.0,
        level=RiskLevel.LOW,
        breakdown=RiskBreakdown(hazard_severity=25.0),
    )

    compliant_text = "The temperature in Gwalior is currently 34.5°C with no rainfall. Overall risk is LOW."
    is_passed, certificate = certifier.verify_and_certify(ctx, compliant_text)

    assert is_passed is True
    assert certificate.claim_verification_passed is True
    assert len(certificate.flagged_claims) == 0
    assert len(certificate.verified_claims) >= 2
    assert certificate.epistemic_audit["temperature"] == EpistemicStatus.OBSERVED
    assert len(certificate.digital_signature_sha256) == 64


def test_p2_claim_verification_flags_hallucinated_risk_and_extreme_claims():
    """P2.1: Verifies ResponseCertifier flags contradictions in risk level and extreme temperatures."""
    certifier = ResponseCertifier()
    now = datetime.utcnow()

    ctx = AnalysisContext(location_name="Delhi")
    ctx.canonical_state = CanonicalWeatherState(
        location="Delhi",
        target_time=now,
        temperature=CanonicalWeatherVariable(name="temperature", value=22.0, unit="°C"),
    )
    ctx.risk_score = RiskScore(
        score=15.0,
        level=RiskLevel.VERY_LOW,
        breakdown=RiskBreakdown(hazard_severity=15.0),
    )

    # Hallucinated risk level (claims HIGH when risk is VERY_LOW) and impossible 95°C temperature
    hallucinated_text = "Severe emergency: Risk is HIGH in Delhi. Ground temperature is 95°C with official red warning."
    is_passed, certificate = certifier.verify_and_certify(ctx, hallucinated_text)

    assert is_passed is False
    assert certificate.claim_verification_passed is False
    assert len(certificate.flagged_claims) >= 2
    assert any("mismatch" in f.lower() for f in certificate.flagged_claims)
    assert any("impossible" in f.lower() for f in certificate.flagged_claims)
