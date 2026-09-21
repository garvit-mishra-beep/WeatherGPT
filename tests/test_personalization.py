"""Comprehensive unit, policy, extraction, multilingual, and integration tests for Personalization."""

import ast
import os
import pytest

from app.contracts import (
    BrainType,
    Coordinates,
    LocationContext,
    SupportedLanguage,
    ToolCallRequest,
    ToolCallResponse,
)
from app.context.models import SessionContext
from app.personalization import (
    CROP_GROWTH_STAGE_QUESTION,
    CROP_NAME_QUESTION,
    LOCATION_QUESTION,
    AnswerExtractor,
    PersonalizationDecisionLevel,
    PersonalizationPolicy,
    PersonalizationService,
)
from app.tools import (
    CalculateIrrigationAdvisoryTool,
    ToolGateway,
    ToolRegistry,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def surat_location() -> LocationContext:
    return LocationContext(
        name="Surat",
        district="Surat",
        state="Gujarat",
        country="India",
        latitude=21.1702,
        longitude=72.8311,
    )


@pytest.fixture
def empty_session() -> SessionContext:
    return SessionContext(session_id="sess_test_01", preferred_language=SupportedLanguage.HINDI)


# ============================================================================
# 1. Zero Onboarding & Everyday Weather Policy Tests
# ============================================================================

def test_general_weather_never_asks_farmer_questions(surat_location, empty_session):
    """Verify general weather queries with location never trigger personal/farm questions."""
    service = PersonalizationService()
    decision = service.evaluate_request(
        query="What will the weather be tomorrow in Surat?",
        brain=BrainType.GENERAL,
        location=surat_location,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.NONE
    assert decision.should_ask is False


def test_missing_location_triggers_blocking_location_question(empty_session):
    """Verify weather query without location triggers mandatory location question."""
    service = PersonalizationService()
    decision = service.evaluate_request(
        query="Will it rain tomorrow?",
        brain=BrainType.GENERAL,
        location=None,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.REQUIRED
    assert decision.is_blocking is True
    assert decision.question.target_field == "location"


def test_conceptual_query_does_not_block_for_location(empty_session):
    """Verify conceptual educational queries proceed without requiring location."""
    service = PersonalizationService()
    decision = service.evaluate_request(
        query="What causes monsoon rainfall in India?",
        brain=BrainType.GENERAL,
        location=None,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.NONE


# ============================================================================
# 2. Farmer Brain Progressive Questioning Tests
# ============================================================================

def test_farmer_query_without_crop_triggers_crop_name_question(surat_location, empty_session):
    """Verify agronomic decision query without crop name prompts for crop."""
    service = PersonalizationService()
    decision = service.evaluate_request(
        query="When should I irrigate my field in Surat?",
        brain=BrainType.FARMER,
        location=surat_location,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.REQUIRED
    assert decision.question.target_field == "crop_name"


def test_farmer_query_with_crop_triggers_growth_stage_for_urea(surat_location, empty_session):
    """Verify stage-sensitive fertilizer query with known crop triggers progressive growth stage question."""
    service = PersonalizationService()
    # Query mentions wheat crop
    decision = service.evaluate_request(
        query="Should I apply urea fertilizer to my wheat crop in Surat?",
        brain=BrainType.FARMER,
        location=surat_location,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.OPTIONAL
    assert decision.is_blocking is False
    assert decision.question.target_field == "growth_stage"


def test_existing_session_context_prevents_repeated_questions(surat_location, empty_session):
    """Verify query does NOT ask for crop name or stage if already stored in session."""
    service = PersonalizationService()
    empty_session.personalization = {
        "crop_name": "Cotton",
        "growth_stage": "flowering",
    }
    decision = service.evaluate_request(
        query="Should I spray pesticide on my crop?",
        brain=BrainType.FARMER,
        location=surat_location,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.NONE


# ============================================================================
# 3. User Refusal / "I Don't Know" Handling Tests
# ============================================================================

@pytest.mark.parametrize("refusal_text", [
    "I don't know",
    "not sure",
    "skip",
    "पता नहीं",
    "मालूम नहीं",
    "জানিনা",
    "माहीत नाही",
    "ખબર નથી",
])
def test_user_refusal_is_respected_and_stored(empty_session, refusal_text):
    """Verify 'I don't know' responses are marked as declined and prevent re-asking."""
    service = PersonalizationService()
    extracted, success = service.process_answer(
        raw_answer=refusal_text,
        question=CROP_GROWTH_STAGE_QUESTION,
        session_context=empty_session,
    )

    assert success is True
    assert extracted.is_declined is True
    assert "growth_stage" in empty_session.personalization.get("_declined_fields", [])


# ============================================================================
# 4. Answer Extraction & Validation Tests
# ============================================================================

def test_growth_stage_multilingual_extraction():
    """Verify natural language stage responses in various languages map to standard stage keys."""
    extractor = AnswerExtractor()

    res_en = extractor.extract_answer("growth_stage", "It is in flowering stage.")
    assert res_en.parsed_value == "flowering"

    res_hi = extractor.extract_answer("growth_stage", "अभी फूल आने की अवस्था में है।")
    assert res_hi.parsed_value == "flowering"

    res_veg = extractor.extract_answer("growth_stage", "vegetative stage")
    assert res_veg.parsed_value == "vegetative"


def test_soil_moisture_validation_and_rejection():
    """Verify soil moisture percentages are validated and out-of-range values are rejected."""
    extractor = AnswerExtractor()

    # Valid percentage
    valid_res = extractor.extract_answer("soil_moisture_estimate_pct", "Around 35.5%")
    assert valid_res.is_valid is True
    assert valid_res.parsed_value == 35.5

    # Out of range (> 100%)
    invalid_res = extractor.extract_answer("soil_moisture_estimate_pct", "250%")
    assert invalid_res.is_valid is False
    assert "between 0% and 100%" in invalid_res.error_message


# ============================================================================
# 5. Multilingual Question Presentation Tests
# ============================================================================

@pytest.mark.parametrize("lang,expected_substring", [
    (SupportedLanguage.ENGLISH, "Which crop are you inquiring about?"),
    (SupportedLanguage.HINDI, "आप किस फसल के लिए सलाह चाहते हैं"),
    (SupportedLanguage.BENGALI, "আপনি কোন ফসলের জন্য পরামর্শ চান"),
    (SupportedLanguage.MARATHI, "तुम्हाला कोणत्या पिकासाठी सल्ला हवा आहे"),
    (SupportedLanguage.GUJARATI, "તમે કયા પાક માટે સલાહ મેળવવા માંગો છો"),
])
def test_multilingual_question_prompts(lang, expected_substring):
    """Verify personalization questions generate accurate localized prompts in 5 Indian languages."""
    service = PersonalizationService()
    prompt = service.get_question_prompt(CROP_NAME_QUESTION, lang)
    assert expected_substring in prompt


# ============================================================================
# 6. Context Update and Correction Test
# ============================================================================

def test_personalization_context_correction(empty_session):
    """Verify user correction (e.g. Wheat -> Cotton) updates active session context."""
    service = PersonalizationService()

    # Turn 1: User says Wheat
    service.process_answer("Wheat", CROP_NAME_QUESTION, empty_session)
    assert empty_session.personalization["crop_name"] == "Wheat"

    # Turn 2: User corrects to Cotton
    service.process_answer("Actually, it is Cotton", CROP_NAME_QUESTION, empty_session)
    assert "Cotton" in empty_session.personalization["crop_name"]


# ============================================================================
# 7. End-to-End Tool Integration Scenario Test
# ============================================================================

@pytest.mark.asyncio
async def test_personalization_and_tool_gateway_integration(surat_location, empty_session):
    """Verify complete flow: Question asked -> User supplies crop -> Context updated -> Tool executed."""
    service = PersonalizationService()
    registry = ToolRegistry()
    irr_tool = CalculateIrrigationAdvisoryTool()
    registry.register(irr_tool)
    gateway = ToolGateway(registry=registry)

    # 1. Initial request: "When should I irrigate?" -> Triggers Crop Name Question
    decision = service.evaluate_request(
        query="When should I irrigate?",
        brain=BrainType.FARMER,
        location=surat_location,
        session_context=empty_session,
    )
    assert decision.decision_level == PersonalizationDecisionLevel.REQUIRED
    assert decision.question.target_field == "crop_name"

    # 2. User answers: "Cotton"
    service.process_answer("Cotton", decision.question, empty_session)
    assert empty_session.personalization["crop_name"] == "Cotton"

    # 3. Re-evaluate: Now crop is known
    decision_2 = service.evaluate_request(
        query="When should I irrigate?",
        brain=BrainType.FARMER,
        location=surat_location,
        session_context=empty_session,
    )
    # No blocking questions remain
    assert decision_2.decision_level != PersonalizationDecisionLevel.REQUIRED

    # 4. Tool Execution proceeds with verified crop argument
    tool_req = ToolCallRequest(
        call_id="call_ag_01",
        tool_name="calculate_irrigation_advisory",
        requested_by_brain=BrainType.FARMER,
        arguments={
            "crop_name": empty_session.personalization["crop_name"],
            "rainfall_24h_mm": 5.0,
            "et0_mm": 4.2,
        },
    )
    resp = await gateway.execute(tool_req)
    assert resp.status == "success"
    assert resp.data["crop_name"] == "Cotton"


# ============================================================================
# 8. Architectural Purity Test
# ============================================================================

def test_personalization_package_architectural_purity():
    """Verify app/personalization/ does not import model SDKs or external weather APIs."""
    p_dir = os.path.join(os.path.dirname(__file__), "..", "app", "personalization")
    forbidden_tokens = ["vllm", "ollama", "qwen", "gemma", "openai_compatible", "open_meteo", "scipy"]

    for root, _, files in os.walk(p_dir):
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
