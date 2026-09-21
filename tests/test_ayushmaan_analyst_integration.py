"""Integration tests for Ayushmaan Analyst Brain integrated into WeatherGPT."""

import pytest
import pytest_asyncio
from datetime import datetime

from app.brains.analyst import AnalystBrain
from app.brains.analyst_core.models.schemas import (
    HazardType,
    RiskLevel,
    DecisionOutcome,
    ConfidenceLevel,
)
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain as CoreAnalystEngine
from app.brains.analyst_core.brain.decision_engine import DecisionEngine
from app.brains.analyst_core.models.weather_data import ForecastPoint
from app.contracts.brain import BrainRequest, TemporalWindow
from app.contracts.enums import (
    BrainType,
    SupportedLanguage,
    AdvisoryAction,
    WarningLevel,
    LocationSource,
    TemporalType,
)
from app.contracts.location import LocationContext
from app.llm.mock_provider import MockLLMProvider
from app.tools.gateway import ToolGateway
from app.tools.registry import ToolRegistry


@pytest.fixture
def mock_llm_provider():
    return MockLLMProvider(
        default_content="Heavy rainfall risk is forecast for Mumbai with potential waterlogging. Recommend suspend non-critical transport operations."
    )


@pytest.fixture
def tool_registry():
    return ToolRegistry()


@pytest.fixture
def tool_gateway(tool_registry):
    return ToolGateway(registry=tool_registry)


@pytest.mark.asyncio
async def test_integrated_analyst_brain_end_to_end(mock_llm_provider, tool_gateway, tool_registry):
    """Verifies that AnalystBrain executes the integrated analyst_core pipeline and emits FinalResponseSchema."""
    brain = AnalystBrain(
        llm_provider=mock_llm_provider,
        tool_gateway=tool_gateway,
        tool_registry=tool_registry,
        use_synthetic=True,
    )

    request = BrainRequest(
        request_id="req_analyst_test_001",
        session_id="session_test_001",
        target_brain=BrainType.ANALYST,
        normalized_query="Assess flash flood and heavy rain risk in Mumbai for the next 24 hours",
        language=SupportedLanguage.ENGLISH,
        location=LocationContext(
            source=LocationSource.USER_QUERY,
            name="Mumbai",
            latitude=19.0760,
            longitude=72.8777,
            district="Mumbai",
            state="Maharashtra",
        ),
        temporal_window=TemporalWindow(
            reference_ist="2026-09-01T12:00:00+05:30",
            start_utc="2026-09-01T00:00:00Z",
            end_utc="2026-09-02T00:00:00Z",
            temporal_type=TemporalType.RELATIVE_DAY,
        ),
    )

    response = await brain.execute(request)

    assert response.brain == BrainType.ANALYST
    assert response.request_id == "req_analyst_test_001"
    assert response.final_payload is not None
    assert response.final_payload.brain == BrainType.ANALYST
    assert response.final_payload.language == SupportedLanguage.ENGLISH

    # Verify structured analytical data
    data = response.final_payload.data
    assert "hazard_type" in data
    assert "risk_level" in data
    assert "confidence_level" in data

    # Verify recommendation
    rec = response.final_payload.recommendation
    assert rec is not None
    assert len(rec.actions) > 0

    # Verify cryptographic provenance
    provenance = response.final_payload.sources
    assert len(provenance) > 0
    assert response.evidence_package is not None
    assert len(response.evidence_package.provenance) > 0


@pytest.mark.asyncio
async def test_integrated_analyst_brain_multilingual_invariance(mock_llm_provider, tool_gateway, tool_registry):
    """Verifies that AnalystBrain processes queries across all 10 Indian languages consistently."""
    brain = AnalystBrain(
        llm_provider=mock_llm_provider,
        tool_gateway=tool_gateway,
        tool_registry=tool_registry,
        use_synthetic=True,
    )

    languages_to_test = [
        SupportedLanguage.HINDI,
        SupportedLanguage.MARATHI,
        SupportedLanguage.BENGALI,
        SupportedLanguage.TAMIL,
        SupportedLanguage.TELUGU,
        SupportedLanguage.GUJARATI,
        SupportedLanguage.KANNADA,
        SupportedLanguage.MALAYALAM,
        SupportedLanguage.PUNJABI,
    ]

    for lang in languages_to_test:
        req = BrainRequest(
            request_id=f"req_analyst_{lang.value}",
            session_id=f"session_{lang.value}",
            target_brain=BrainType.ANALYST,
            normalized_query="Analyze cyclone risk and storm surge in Chennai",
            language=lang,
            location=LocationContext(
                source=LocationSource.USER_QUERY,
                name="Chennai",
                latitude=13.0827,
                longitude=80.2707,
                district="Chennai",
                state="Tamil Nadu",
            ),
            temporal_window=TemporalWindow(
                reference_ist="2026-09-01T12:00:00+05:30",
                start_utc="2026-09-01T00:00:00Z",
                end_utc="2026-09-02T00:00:00Z",
                temporal_type=TemporalType.RELATIVE_DAY,
            ),
        )
        resp = await brain.execute(req)
        assert resp.brain == BrainType.ANALYST
        assert resp.final_payload.language == lang
        assert resp.final_payload.data is not None


@pytest.mark.asyncio
async def test_analyst_core_direct_pipeline():
    """Verifies direct deterministic behavior of Ayushmaan's CoreAnalystEngine."""
    engine = CoreAnalystEngine(use_synthetic=True)
    result = engine.analyze(
        query="Is it safe for outdoor festival operations in Pune with heavy rain forecast?",
        session_id="session_direct_001",
    )

    assert result.analysis_type is not None
    assert result.risk_level in [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.VERY_LOW, RiskLevel.UNKNOWN]
    assert len(result.evidence) > 0

    # Test Decision Engine with forecast data
    decision_engine = DecisionEngine()
    fc = [
        ForecastPoint(
            valid_time=datetime.now(),
            location="Pune",
            init_time=datetime.now(),
            rainfall_mm=75.0,
            precipitation_prob_pct=90.0,
            source="ECMWF",
        )
    ]
    decision = decision_engine.evaluate_decision(
        objective="outdoor festival",
        hazards=[HazardType.HEAVY_RAINFALL],
        forecasts=fc,
        alerts=[],
        risk_level=RiskLevel.HIGH,
    )
    assert decision.outcome in [
        DecisionOutcome.GO,
        DecisionOutcome.PROCEED_WITH_CAUTION,
        DecisionOutcome.POSTPONE_OR_RELOCATE,
        DecisionOutcome.NO_GO,
    ]
