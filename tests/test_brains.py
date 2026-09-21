"""Comprehensive unit and integration tests for Brain Interface, Registry, Resolver, and Orchestrator."""

import ast
import os
import pytest

from app.brains import (
    AutoRoutingNotAvailableError,
    BaseBrain,
    BrainExecutionError,
    BrainNotRegisteredError,
    BrainOrchestrator,
    BrainRegistry,
    BrainResolver,
    InvalidBrainResponseError,
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
    WarningLevel,
    WeatherAlert,
)
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider


# ============================================================================
# Test Fixtures & Mock Brain Implementations
# ============================================================================

class MockGeneralBrain(BaseBrain):
    """Mock implementation of General Brain for infrastructure testing."""

    @property
    def brain_type(self) -> BrainType:
        return BrainType.GENERAL

    async def execute(self, request: BrainRequest) -> BrainResponse:
        final_payload = FinalResponseSchema(
            response_id=f"resp_{request.request_id}",
            session_id=request.session_id,
            brain=BrainType.GENERAL,
            language=request.language,
            created_at="2026-08-29T11:30:00+05:30",
            summary="Ahmedabad will experience clear skies with a maximum temperature of 32°C.",
            answer="Clear skies expected across Ahmedabad today.",
            data={"temperature_max_c": 32.0, "precipitation_mm": 0.0},
        )
        return BrainResponse(
            request_id=request.request_id,
            brain=BrainType.GENERAL,
            final_payload=final_payload,
        )


class MockFarmerBrain(BaseBrain):
    """Mock implementation of Farmer Brain for infrastructure testing."""

    @property
    def brain_type(self) -> BrainType:
        return BrainType.FARMER

    async def execute(self, request: BrainRequest) -> BrainResponse:
        final_payload = FinalResponseSchema(
            response_id=f"resp_{request.request_id}",
            session_id=request.session_id,
            brain=BrainType.FARMER,
            language=request.language,
            created_at="2026-08-29T11:30:00+05:30",
            summary="Postpone irrigation due to expected rainfall.",
            answer="Upcoming rain of 35mm exceeds crop demand.",
            data={"irrigation_action": "POSTPONE"},
            recommendation=Recommendation(
                primary_action=AdvisoryAction.POSTPONE_IRRIGATION,
                actions=["Withhold irrigation for 48 hours."],
            ),
            alert=WeatherAlert(
                source="IMD",
                level=WarningLevel.YELLOW,
                hazard_type="Heavy Rain",
                headline="Heavy Rain Alert",
                description="Heavy rain expected.",
                valid_until="2026-08-31T08:30:00+05:30",
            ),
        )
        return BrainResponse(
            request_id=request.request_id,
            brain=BrainType.FARMER,
            final_payload=final_payload,
        )


class FaultyMockBrain(BaseBrain):
    """Mock brain that raises an unhandled internal exception."""

    @property
    def brain_type(self) -> BrainType:
        return BrainType.ANALYST

    async def execute(self, request: BrainRequest) -> BrainResponse:
        raise ZeroDivisionError("Simulated internal algorithmic crash")


class InvalidOutputMockBrain(BaseBrain):
    """Mock brain that returns an invalid object violating the BrainResponse contract."""

    @property
    def brain_type(self) -> BrainType:
        return BrainType.RESEARCHER

    async def execute(self, request: BrainRequest) -> BrainResponse:
        return "not_a_brain_response"  # type: ignore


@pytest.fixture
def sample_brain_request() -> BrainRequest:
    return BrainRequest(
        request_id="req_test_001",
        session_id="sess_test_123",
        target_brain=BrainType.GENERAL,
        normalized_query="What is the weather today?",
        language=SupportedLanguage.ENGLISH,
        location=LocationContext(
            source=LocationSource.USER_QUERY,
            name="Ahmedabad",
            district="Ahmedabad",
            state="Gujarat",
            latitude=23.0225,
            longitude=72.5714,
        ),
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T00:00:00Z",
            end_utc="2026-08-29T23:59:59Z",
            temporal_type=TemporalType.CURRENT,
        ),
    )


# ============================================================================
# 1. Base Brain Interface Tests
# ============================================================================

@pytest.mark.asyncio
async def test_base_brain_implementation(sample_brain_request):
    """Verify BaseBrain subclass can be instantiated and executed cleanly."""
    brain = MockGeneralBrain()
    assert brain.brain_type == BrainType.GENERAL

    response = await brain.execute(sample_brain_request)
    assert isinstance(response, BrainResponse)
    assert response.brain == BrainType.GENERAL
    assert response.request_id == "req_test_001"
    assert response.final_payload.summary.startswith("Ahmedabad")


# ============================================================================
# 2. Brain Registry Tests
# ============================================================================

def test_brain_registry_lifecycle():
    """Verify BrainRegistry registration, lookup, duplicate handling, and unregistration."""
    registry = BrainRegistry()
    general_brain = MockGeneralBrain()
    farmer_brain = MockFarmerBrain()

    # Initial empty state
    assert registry.list_brains() == []
    assert registry.has(BrainType.GENERAL) is False

    # Register brains
    registry.register(general_brain)
    registry.register(farmer_brain)
    assert len(registry.list_brains()) == 2
    assert registry.has(BrainType.GENERAL) is True
    assert registry.has(BrainType.FARMER) is True

    # Retrieve brain
    retrieved = registry.get(BrainType.GENERAL)
    assert retrieved is general_brain

    # Duplicate registration without override should raise ValueError
    with pytest.raises(ValueError) as exc:
        registry.register(MockGeneralBrain(), override=False)
    assert "already registered" in str(exc.value)

    # Duplicate registration with override=True should succeed
    new_general = MockGeneralBrain()
    registry.register(new_general, override=True)
    assert registry.get(BrainType.GENERAL) is new_general

    # Lookup unregistered brain raises BrainNotRegisteredError
    with pytest.raises(BrainNotRegisteredError) as exc_info:
        registry.get(BrainType.RESEARCHER)
    assert exc_info.value.error_code == "BRAIN_NOT_REGISTERED"

    # Unregister brain
    unregistered = registry.unregister(BrainType.GENERAL)
    assert unregistered is new_general
    assert registry.has(BrainType.GENERAL) is False

    # Clear registry
    registry.clear()
    assert len(registry.list_brains()) == 0


# ============================================================================
# 3. Brain Resolver Tests
# ============================================================================

@pytest.mark.asyncio
async def test_brain_resolver_explicit_selection(sample_brain_request):
    """Verify BrainResolver cleanly passes explicit BrainType selections."""
    resolver = BrainResolver()

    for b_type in [BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST]:
        req = sample_brain_request.model_copy(update={"target_brain": b_type})
        resolved = await resolver.resolve(req)
        assert resolved == b_type


@pytest.mark.asyncio
async def test_brain_resolver_auto_without_router_raises_error(sample_brain_request):
    """Verify AUTO brain selection raises AutoRoutingNotAvailableError when no router is present."""
    resolver = BrainResolver(router_strategy=None)
    auto_req = sample_brain_request.model_copy(update={"target_brain": BrainType.AUTO})

    with pytest.raises(AutoRoutingNotAvailableError) as exc_info:
        await resolver.resolve(auto_req)
    assert exc_info.value.error_code == "AUTO_ROUTING_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_brain_resolver_with_injected_router_strategy(sample_brain_request):
    """Verify custom routing callable is used when injected into resolver."""
    def mock_router(req: BrainRequest) -> BrainType:
        if "crop" in req.normalized_query:
            return BrainType.FARMER
        return BrainType.GENERAL

    resolver = BrainResolver(router_strategy=mock_router)
    req = sample_brain_request.model_copy(
        update={"target_brain": BrainType.AUTO, "normalized_query": "Should I irrigate my crop?"}
    )
    resolved = await resolver.resolve(req)
    assert resolved == BrainType.FARMER


# ============================================================================
# 4. Brain Orchestrator Lifecycle & Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_brain_orchestrator_success(sample_brain_request):
    """Verify successful end-to-end orchestration flow."""
    registry = BrainRegistry()
    registry.register(MockGeneralBrain())
    registry.register(MockFarmerBrain())

    orchestrator = BrainOrchestrator(registry=registry)
    response = await orchestrator.orchestrate(sample_brain_request)

    assert isinstance(response, BrainResponse)
    assert response.brain == BrainType.GENERAL
    assert response.request_id == sample_brain_request.request_id
    assert response.final_payload.summary.startswith("Ahmedabad")


@pytest.mark.asyncio
async def test_brain_orchestrator_unregistered_brain(sample_brain_request):
    """Verify orchestrator raises BrainNotRegisteredError when target brain has no registered handler."""
    registry = BrainRegistry()  # Empty registry
    orchestrator = BrainOrchestrator(registry=registry)

    with pytest.raises(BrainNotRegisteredError) as exc_info:
        await orchestrator.orchestrate(sample_brain_request)
    assert exc_info.value.error_code == "BRAIN_NOT_REGISTERED"


@pytest.mark.asyncio
async def test_brain_orchestrator_execution_error(sample_brain_request):
    """Verify orchestrator wraps unhandled internal brain exceptions into BrainExecutionError."""
    registry = BrainRegistry()
    registry.register(FaultyMockBrain())

    orchestrator = BrainOrchestrator(registry=registry)
    req = sample_brain_request.model_copy(update={"target_brain": BrainType.ANALYST})

    with pytest.raises(BrainExecutionError) as exc_info:
        await orchestrator.orchestrate(req)
    assert exc_info.value.error_code == "BRAIN_EXECUTION_ERROR"
    assert "ZeroDivisionError" not in exc_info.value.message or "internal error" in exc_info.value.message


@pytest.mark.asyncio
async def test_brain_orchestrator_invalid_response_type(sample_brain_request):
    """Verify orchestrator raises InvalidBrainResponseError if brain emits an invalid response object."""
    registry = BrainRegistry()
    registry.register(InvalidOutputMockBrain())

    orchestrator = BrainOrchestrator(registry=registry)
    req = sample_brain_request.model_copy(update={"target_brain": BrainType.RESEARCHER})

    with pytest.raises(InvalidBrainResponseError) as exc_info:
        await orchestrator.orchestrate(req)
    assert exc_info.value.error_code == "INVALID_BRAIN_RESPONSE"


# ============================================================================
# 5. LLM Dependency Injection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_llm_provider_injection():
    """Verify LLMProvider can be injected into BaseBrain subclasses without direct model SDK coupling."""
    mock_llm: LLMProvider = MockLLMProvider(default_content="LLM synthesized advice")

    class LLMUsingBrain(BaseBrain):
        @property
        def brain_type(self) -> BrainType:
            return BrainType.GENERAL

        async def execute(self, request: BrainRequest) -> BrainResponse:
            assert self.llm_provider is not None
            # Brain can access LLMProvider through standard interface
            llm_res = await self.llm_provider.generate_chat_completion([])
            return BrainResponse(
                request_id=request.request_id,
                brain=BrainType.GENERAL,
                final_payload=FinalResponseSchema(
                    response_id=f"resp_{request.request_id}",
                    session_id=request.session_id,
                    brain=BrainType.GENERAL,
                    created_at="2026-08-29T11:30:00+05:30",
                    summary=llm_res.content or "",
                    answer=llm_res.content or "",
                ),
            )

    brain = LLMUsingBrain(llm_provider=mock_llm)
    assert brain.llm_provider is mock_llm


# ============================================================================
# 6. Complete End-to-End NormalizedRequest -> BrainResponse Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_complete_normalized_to_brain_flow():
    """Verify complete flow from NormalizedRequestSchema to BrainRequest to BrainOrchestrator to BrainResponse."""
    # 1. Setup mock normalized request
    normalized_req = NormalizedRequestSchema(
        request_id="req_int_777",
        session_id="sess_int_999",
        raw_query="Should I irrigate cotton?",
        normalized_query="Should I irrigate cotton?",
        detected_language=DetectedLanguage(code=SupportedLanguage.HINDI, script="Latin"),
        target_language=SupportedLanguage.HINDI,
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
        router_override=BrainType.FARMER,
    )

    # 2. Transform into BrainRequest
    brain_req = BrainRequest(
        request_id=normalized_req.request_id,
        session_id=normalized_req.session_id,
        target_brain=normalized_req.router_override or BrainType.GENERAL,
        normalized_query=normalized_req.normalized_query,
        language=normalized_req.target_language,
        location=normalized_req.location,
        temporal_window=normalized_req.temporal_window,
        personalization_context={"crop": "Cotton"},
    )

    # 3. Setup registry & orchestrator
    registry = BrainRegistry()
    registry.register(MockFarmerBrain())
    orchestrator = BrainOrchestrator(registry=registry)

    # 4. Execute orchestration
    brain_resp = await orchestrator.orchestrate(brain_req)

    # 5. Verify final response properties
    assert brain_resp.request_id == "req_int_777"
    assert brain_resp.brain == BrainType.FARMER
    assert brain_resp.final_payload.recommendation is not None
    assert brain_resp.final_payload.recommendation.primary_action == AdvisoryAction.POSTPONE_IRRIGATION


# ============================================================================
# 7. Architectural Purity & Non-Pollution Test
# ============================================================================

def test_brains_package_architectural_purity():
    """Verify app/brains/ does not import specific model SDKs, weather APIs, or GIS services."""
    brains_dir = os.path.join(os.path.dirname(__file__), "..", "app", "brains")
    forbidden_tokens = ["vllm", "ollama", "qwen", "gemma", "open_meteo", "scipy", "postgis", "gfs"]

    for filename in os.listdir(brains_dir):
        if filename.endswith(".py"):
            filepath = os.path.join(brains_dir, filename)
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
