"""Comprehensive unit, evaluation, and integration tests for the Auto Router."""

import ast
import os
import pytest
from pydantic import ValidationError

from app.brains import (
    BaseBrain,
    BrainOrchestrator,
    BrainRegistry,
    BrainResolver,
)
from app.contracts import (
    AdvisoryAction,
    BrainRequest,
    BrainResponse,
    BrainType,
    DetectedLanguage,
    FinalResponseSchema,
    LocationContext,
    LocationSource,
    NormalizedRequestSchema,
    Recommendation,
    SupportedLanguage,
    TemporalType,
    TemporalWindow,
)
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.types import ChatMessage, LLMProviderError, LLMResponse, LLMTimeoutError
from app.router import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    DisambiguationRequest,
    InvalidRouterOutputError,
    LLMAutoRouter,
    RouterResult,
    RouterUnavailableError,
    RoutingClassification,
)


# ============================================================================
# Test Fixtures & Mock Providers
# ============================================================================

class MockLLMRoutingProvider(LLMProvider):
    """Custom Mock LLM Provider tailored for routing test scenarios."""

    def __init__(self, classification: RoutingClassification):
        self.classification = classification

    async def generate_chat_completion(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMResponse:
        return LLMResponse(content=self.classification.model_dump_json())

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        return self.classification

    async def check_health(self) -> bool:
        return True


class FailingLLMProvider(LLMProvider):
    """Mock LLM Provider simulating network timeout / inference crash."""

    async def generate_chat_completion(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMResponse:
        raise LLMTimeoutError("Inference timed out after 30.0s")

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        raise LLMTimeoutError("Inference timed out after 30.0s")

    async def check_health(self) -> bool:
        return False


class MockFarmerBrain(BaseBrain):
    """Mock domain brain for orchestrator integration test."""

    @property
    def brain_type(self) -> BrainType:
        return BrainType.FARMER

    async def execute(self, request: BrainRequest) -> BrainResponse:
        return BrainResponse(
            request_id=request.request_id,
            brain=BrainType.FARMER,
            final_payload=FinalResponseSchema(
                response_id=f"resp_{request.request_id}",
                session_id=request.session_id,
                brain=BrainType.FARMER,
                language=request.language,
                created_at="2026-08-29T11:30:00+05:30",
                summary="Postpone irrigation.",
                answer="Postpone irrigation due to incoming rainfall.",
                recommendation=Recommendation(
                    primary_action=AdvisoryAction.POSTPONE_IRRIGATION,
                    actions=["Do not irrigate."],
                ),
            ),
        )


@pytest.fixture
def auto_brain_request() -> BrainRequest:
    return BrainRequest(
        request_id="req_auto_001",
        session_id="sess_auto_123",
        target_brain=BrainType.AUTO,
        normalized_query="Will it rain tomorrow in Surat?",
        language=SupportedLanguage.HINDI,
        location=LocationContext(
            source=LocationSource.GPS,
            name="Surat",
            district="Surat",
            state="Gujarat",
            latitude=21.1702,
            longitude=72.8311,
        ),
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T18:30:00Z",
            end_utc="2026-08-30T18:29:59Z",
            temporal_type=TemporalType.RELATIVE_DAY,
            relative_expression="tomorrow",
        ),
    )


# ============================================================================
# 1. Explicit Brain Selection Tests (Bypass Auto Router)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "explicit_brain",
    [BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST],
)
async def test_explicit_brain_selection_bypasses_router(auto_brain_request, explicit_brain):
    """Verify explicit Brain selection immediately returns high-confidence override without calling LLM."""
    failing_llm = FailingLLMProvider()  # If LLM is called, test will fail
    router = LLMAutoRouter(llm_provider=failing_llm)

    explicit_req = auto_brain_request.model_copy(update={"target_brain": explicit_brain})
    result = await router.route(explicit_req)

    assert result.is_explicit_override is True
    assert result.selected_brain == explicit_brain
    assert result.confidence == 1.0
    assert result.confidence_level == "high"
    assert result.is_routed is True


# ============================================================================
# 2. Domain Auto Routing Tests (General, Farmer, Researcher, Analyst)
# ============================================================================

@pytest.mark.asyncio
async def test_auto_route_to_general_brain(auto_brain_request):
    """Verify General weather query classification."""
    classification = RoutingClassification(
        selected_brain=BrainType.GENERAL,
        confidence=0.95,
        intent_category="weather_forecast",
        rationale="User is asking for tomorrow's rain forecast.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(auto_brain_request)

    assert result.selected_brain == BrainType.GENERAL
    assert result.confidence == 0.95
    assert result.confidence_level == "high"
    assert result.is_routed is True
    assert result.disambiguation is None


@pytest.mark.asyncio
async def test_auto_route_to_farmer_brain(auto_brain_request):
    """Verify Farmer agronomic query classification."""
    req = auto_brain_request.model_copy(
        update={
            "normalized_query": "Should I irrigate my cotton crop tomorrow?",
            "personalization_context": {"crop": "Cotton", "farm_size_acres": 4.5},
        }
    )
    classification = RoutingClassification(
        selected_brain=BrainType.FARMER,
        confidence=0.92,
        intent_category="irrigation_scheduling",
        rationale="User is seeking agricultural irrigation advice for cotton.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(req)

    assert result.selected_brain == BrainType.FARMER
    assert result.confidence == 0.92
    assert result.confidence_level == "high"


@pytest.mark.asyncio
async def test_auto_route_to_researcher_brain(auto_brain_request):
    """Verify Researcher historical trend classification."""
    req = auto_brain_request.model_copy(
        update={"normalized_query": "What are the rainfall trends in Gujarat over the last 30 years?"}
    )
    classification = RoutingClassification(
        selected_brain=BrainType.RESEARCHER,
        confidence=0.88,
        intent_category="historical_climate_trend",
        rationale="User requests multi-decadal rainfall trend analysis.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(req)

    assert result.selected_brain == BrainType.RESEARCHER
    assert result.confidence == 0.88
    assert result.confidence_level == "high"


@pytest.mark.asyncio
async def test_auto_route_to_analyst_brain(auto_brain_request):
    """Verify Analyst hazard exposure classification."""
    req = auto_brain_request.model_copy(
        update={"normalized_query": "What is the cyclone flood risk to highway infrastructure in Surat?"}
    )
    classification = RoutingClassification(
        selected_brain=BrainType.ANALYST,
        confidence=0.90,
        intent_category="infrastructure_risk_exposure",
        rationale="User asks for spatial hazard exposure on highway assets.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(req)

    assert result.selected_brain == BrainType.ANALYST
    assert result.confidence == 0.90
    assert result.confidence_level == "high"


# ============================================================================
# 3. Ambiguity & Disambiguation Card Tests
# ============================================================================

@pytest.mark.asyncio
async def test_ambiguous_query_generates_disambiguation_card(auto_brain_request):
    """Verify low confidence / ambiguous query emits DisambiguationRequest card."""
    req = auto_brain_request.model_copy(update={"normalized_query": "Tell me about rainfall in Surat."})
    classification = RoutingClassification(
        selected_brain=BrainType.GENERAL,
        confidence=0.52,  # Low confidence (< 0.60)
        intent_category="ambiguous_rainfall_query",
        rationale="Query could be a current forecast, historical analysis, or irrigation guidance.",
        needs_clarification=True,
        competing_brains=[BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER],
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(req)

    assert result.is_routed is False
    assert result.selected_brain is None
    assert result.needs_clarification is True
    assert result.confidence_level == "low"
    assert result.disambiguation is not None
    assert result.disambiguation.type == "disambiguation_request"
    assert len(result.disambiguation.options) == 3
    assert result.disambiguation.options[0].target_brain == BrainType.GENERAL


# ============================================================================
# 4. Confidence Threshold Boundary Tests
# ============================================================================

@pytest.mark.asyncio
async def test_medium_confidence_threshold_routing(auto_brain_request):
    """Verify score between 0.60 and 0.84 results in medium confidence without disambiguation card."""
    classification = RoutingClassification(
        selected_brain=BrainType.RESEARCHER,
        confidence=0.72,
        intent_category="rainfall_comparison",
        rationale="Moderate confidence in researcher intent.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(auto_brain_request)

    assert result.selected_brain == BrainType.RESEARCHER
    assert result.confidence_level == "medium"
    assert result.needs_clarification is False
    assert result.is_routed is True


# ============================================================================
# 5. Multilingual & Code-Mixed Classification Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,expected_brain,lang",
    [
        ("Will it rain tomorrow in Pune?", BrainType.GENERAL, SupportedLanguage.ENGLISH),
        ("क्या कल सूरत में बारिश होगी?", BrainType.GENERAL, SupportedLanguage.HINDI),
        ("আগামীকাল কি বৃষ্টি হবে?", BrainType.GENERAL, SupportedLanguage.BENGALI),
        ("उद्या पाऊस पडेल का?", BrainType.GENERAL, SupportedLanguage.MARATHI),
        ("કાલે વરસાદ પડશે?", BrainType.GENERAL, SupportedLanguage.GUJARATI),
        ("Kal cotton crop ke liye irrigation karna chahiye?", BrainType.FARMER, SupportedLanguage.HINDI),
    ],
)
async def test_multilingual_and_codemixed_routing(auto_brain_request, query, expected_brain, lang):
    """Verify routing across all 5 supported Indian languages and code-mixed text."""
    req = auto_brain_request.model_copy(update={"normalized_query": query, "language": lang})
    classification = RoutingClassification(
        selected_brain=expected_brain,
        confidence=0.91,
        intent_category="multilingual_intent",
        rationale=f"Accurately resolved intent in {lang.value}.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))
    result = await router.route(req)

    assert result.selected_brain == expected_brain
    assert result.confidence_level == "high"


# ============================================================================
# 6. Context & Personalization Context Tests
# ============================================================================

@pytest.mark.asyncio
async def test_conversation_history_context_routing(auto_brain_request):
    """Verify multi-turn conversation context correctly influences the classification prompt."""
    req = auto_brain_request.model_copy(
        update={
            "normalized_query": "Should I irrigate tomorrow?",
            "conversation_history": [
                {"role": "user", "content": "My cotton crop is at flowering stage in Surat."},
                {"role": "assistant", "content": "Understood. Tracking cotton in Surat."},
            ],
        }
    )
    prompt = LLMAutoRouter(llm_provider=FailingLLMProvider())._build_classification_prompt(req)
    assert "cotton crop is at flowering stage" in prompt
    assert "Surat" in prompt


# ============================================================================
# 7. Error Handling & Safe Failure Tests
# ============================================================================

@pytest.mark.asyncio
async def test_router_llm_failure_does_not_silently_fallback(auto_brain_request):
    """Verify LLM failure raises RouterUnavailableError and NEVER falls back silently to General Brain."""
    router = LLMAutoRouter(llm_provider=FailingLLMProvider())

    with pytest.raises(RouterUnavailableError) as exc_info:
        await router.route(auto_brain_request)
    assert exc_info.value.error_code == "ROUTER_UNAVAILABLE"


# ============================================================================
# 8. End-to-End Orchestrator + Auto Router Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_orchestrator_with_auto_router_integration(auto_brain_request):
    """Verify full pipeline: BrainRequest(AUTO) -> BrainOrchestrator -> BrainResolver -> LLMAutoRouter -> MockFarmerBrain."""
    # 1. Setup Mock Router
    classification = RoutingClassification(
        selected_brain=BrainType.FARMER,
        confidence=0.93,
        intent_category="irrigation_scheduling",
        rationale="Agricultural water balance query.",
        needs_clarification=False,
    )
    router = LLMAutoRouter(llm_provider=MockLLMRoutingProvider(classification))

    # 2. Bridge router into BrainResolver
    resolver = BrainResolver(router_strategy=router.route)

    # 3. Setup BrainRegistry with Farmer Brain
    registry = BrainRegistry()
    registry.register(MockFarmerBrain())

    # 4. Execute orchestration
    orchestrator = BrainOrchestrator(registry=registry, resolver=resolver)
    response = await orchestrator.orchestrate(auto_brain_request)

    # 5. Verify resolved response
    assert isinstance(response, BrainResponse)
    assert response.brain == BrainType.FARMER
    assert response.final_payload.recommendation.primary_action == AdvisoryAction.POSTPONE_IRRIGATION


# ============================================================================
# 9. Architectural Purity & Non-Pollution Test
# ============================================================================

def test_router_package_architectural_purity():
    """Verify app/router/ does not import weather data adapters, NWP models, or GIS engines."""
    router_dir = os.path.join(os.path.dirname(__file__), "..", "app", "router")
    forbidden_tokens = ["vllm", "ollama", "qwen", "gemma", "open_meteo", "scipy", "postgis", "gfs", "fao56"]

    for filename in os.listdir(router_dir):
        if filename.endswith(".py"):
            filepath = os.path.join(router_dir, filename)
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
