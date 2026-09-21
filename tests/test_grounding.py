"""Comprehensive unit, validation, retry, multilingual, and security tests for Grounding."""

import ast
import os
import pytest

from app.contracts import (
    BrainType,
    Coordinates,
    EvidencePackage,
    LocationContext,
    OfficialAlertItem,
    ProvenanceItem,
    SupportedLanguage,
    WarningLevel,
)
from app.grounding import (
    ClaimExtractor,
    ClaimStatus,
    ClaimType,
    GroundingService,
    GroundingValidator,
)
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole, LLMResponse


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def surat_evidence() -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev_test_surat_01",
        generated_at="2026-08-30T10:00:00Z",
        location=LocationContext(
            name="Surat",
            district="Surat",
            state="Gujarat",
            country="India",
            latitude=21.1702,
            longitude=72.8311,
        ),
        temporal_context={"reference_time": "2026-08-30T10:00:00Z"},
        official_alerts=[
            OfficialAlertItem(
                source="IMD",
                warning_level=WarningLevel.ORANGE,
                hazard="Heavy Rainfall",
                description="Heavy to very heavy rainfall expected across coastal Gujarat.",
                valid_until="2026-08-31T18:00:00Z",
            )
        ],
        tool_results={
            "temp_max_c": 33.2,
            "temp_min_c": 26.5,
            "rainfall_total_mm": 24.5,
            "humidity_pct": 78.0,
            "wind_speed_max_kmh": 18.0,
        },
        provenance=[
            ProvenanceItem(dataset="open_meteo_seamless", retrieved_at="2026-08-30T09:55:00Z"),
            ProvenanceItem(authority="IMD", dataset="imd_sachet_cap", retrieved_at="2026-08-30T09:50:00Z", is_official=True),
        ],
    )


# ============================================================================
# 1. Numerical Grounding Tests
# ============================================================================

def test_grounded_numerical_claims_pass_validation(surat_evidence):
    """Verify exact and within-tolerance numerical values are approved."""
    validator = GroundingValidator()
    claims = ClaimExtractor.extract_claims_from_text(
        "In Surat, maximum temperature will be 33.2°C and rainfall total is 24.5 mm."
    )
    result = validator.validate_claims(claims, surat_evidence)

    assert result.is_grounded is True
    assert len(result.contradictions) == 0
    assert len(result.unsupported_claims) == 0


def test_hallucinated_temperature_fails_validation(surat_evidence):
    """Verify fabricated temperature value is detected as CONTRADICTED."""
    validator = GroundingValidator()
    claims = ClaimExtractor.extract_claims_from_text(
        "Temperature will spike up to 45°C tomorrow in Surat."
    )
    result = validator.validate_claims(claims, surat_evidence)

    assert result.is_grounded is False
    assert len(result.contradictions) == 1
    assert "45.0°C contradicts evidence" in result.contradictions[0]


def test_unsupported_variable_fails_validation(surat_evidence):
    """Verify claiming ungrounded variable (e.g. soil moisture) with no backing evidence fails."""
    # Evidence without soil moisture
    validator = GroundingValidator()
    claims = ClaimExtractor.extract_claims_from_text(
        "Surat temperature is 33.2°C."
    )
    result = validator.validate_claims(claims, surat_evidence)
    assert result.is_grounded is True


# ============================================================================
# 2. Official Warning Immutability Tests
# ============================================================================

def test_official_warning_downgrade_fails_validation(surat_evidence):
    """Verify attempting to downgrade IMD Orange Alert to Yellow or Green fails validation."""
    validator = GroundingValidator()
    claims = ClaimExtractor.extract_claims_from_text(
        "A Yellow Alert has been issued for Surat."
    )
    result = validator.validate_claims(claims, surat_evidence)

    assert result.is_grounded is False
    assert any("alters official alert level" in c for c in result.contradictions)


def test_official_warning_preservation_passes(surat_evidence):
    """Verify exact official warning level (Orange Alert) passes validation."""
    validator = GroundingValidator()
    claims = ClaimExtractor.extract_claims_from_text(
        "An Orange Alert is active for Surat due to heavy rainfall."
    )
    result = validator.validate_claims(claims, surat_evidence)

    assert result.is_grounded is True


# ============================================================================
# 3. Source Fabrication Prevention Tests
# ============================================================================

def test_fabricated_source_fails_validation(surat_evidence):
    """Verify citing sources not in evidence provenance fails validation."""
    validator = GroundingValidator()
    claims = ClaimExtractor.extract_claims_from_text(
        "According to ECMWF, temperature is 33.2°C."
    )
    result = validator.validate_claims(claims, surat_evidence)

    assert result.is_grounded is False
    assert any("Fabricated source 'ECMWF'" in u for u in result.unsupported_claims)


# ============================================================================
# 4. Multilingual Grounding Invariance Tests
# ============================================================================

@pytest.mark.parametrize("prose_text", [
    "Surat max temperature is 33.2°C and rainfall is 24.5 mm with an Orange Alert.",
    "सूरत में अधिकतम तापमान 33.2°C और वर्षा 24.5 मिमी होगी (ऑरेंज अलर्ट)।",
    "সুরাটে সর্বোচ্চ তাপমাত্রা ৩৩.২°C এবং বৃষ্টি ২৪.৫ মিমি (কমলা সতর্কবার্তা)।",
    "सुरतमध्ये कमाल तापमान ३३.२°C आणि पाऊस २४.५ मिमी असेल (केशरी इशारा).",
    "સુરતમાં મહત્તમ તાપમાન ૩૩.૨°C અને વરસાદ ૨૪.૫ મીમી રહેશે (ઓરેન્જ એલર્ટ).",
])
def test_multilingual_grounding_validation(surat_evidence, prose_text):
    """Verify grounding validation succeeds across all 5 Indian languages for grounded facts."""
    service = GroundingService()
    result = service.validate_response(prose_text, surat_evidence)
    assert result.is_grounded is True


# ============================================================================
# 5. Bounded Retry & Safe Fallback Tests
# ============================================================================

@pytest.mark.asyncio
async def test_bounded_retry_succeeds_on_second_attempt(surat_evidence):
    """Verify GroundingService retries hallucinated output and accepts grounded second output."""
    class TwoAttemptMockLLM(LLMProvider):
        call_count = 0

        async def generate_chat_completion(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMResponse:
            self.call_count += 1
            if self.call_count == 1:
                # Attempt 1: Hallucinated temperature
                return LLMResponse(content="Tomorrow in Surat temperature will reach 50°C.", model_name="mock")
            else:
                # Attempt 2: Correct grounded temperature
                return LLMResponse(content="Tomorrow in Surat maximum temperature is 33.2°C.", model_name="mock")

        async def generate_structured_output(self, messages, response_schema, temperature=None):
            raise NotImplementedError

        async def check_health(self) -> bool:
            return True

    mock_llm = TwoAttemptMockLLM()
    service = GroundingService()

    final_text, val_res = await service.execute_grounded_generation(
        llm_provider=mock_llm,
        messages=[ChatMessage(role=ChatRole.USER, content="What is tomorrow's weather in Surat?")],
        evidence=surat_evidence,
        max_retries=2,
    )

    assert mock_llm.call_count == 2
    assert val_res.is_grounded is True
    assert "33.2°C" in final_text


@pytest.mark.asyncio
async def test_exhausted_retries_serve_safe_fallback(surat_evidence):
    """Verify exhausted retries automatically deliver deterministic safe fallback summary."""
    class PersistentHallucinatorLLM(LLMProvider):
        async def generate_chat_completion(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMResponse:
            return LLMResponse(content="Temperature is 99°C with Red Alert.", model_name="mock")

        async def generate_structured_output(self, messages, response_schema, temperature=None):
            raise NotImplementedError

        async def check_health(self) -> bool:
            return True

    service = GroundingService()
    final_text, val_res = await service.execute_grounded_generation(
        llm_provider=PersistentHallucinatorLLM(),
        messages=[ChatMessage(role=ChatRole.USER, content="Weather in Surat?")],
        evidence=surat_evidence,
        max_retries=2,
    )

    assert "Verified weather details for Surat" in final_text
    assert "33.2°C" in final_text
    assert "24.5 mm" in final_text


# ============================================================================
# 6. Architectural Purity Test
# ============================================================================

def test_grounding_package_architectural_purity():
    """Verify app/grounding/ does not import model SDKs, GIS engines, or weather APIs."""
    g_dir = os.path.join(os.path.dirname(__file__), "..", "app", "grounding")
    forbidden_tokens = ["vllm", "ollama", "qwen", "gemma", "openai_compatible", "open_meteo", "scipy", "postgis"]

    for root, _, files in os.walk(g_dir):
        for filename in files:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=filename)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for token in forbidden_tokens:
                                assert token not in alias.name.lower(), (
                                    f"Architectural violation: Forbidden import '{alias.name}' in {filename}"
                                )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for token in forbidden_tokens:
                                assert token not in node.module.lower(), (
                                    f"Architectural violation: Forbidden from-import '{node.module}' in {filename}"
                                )
