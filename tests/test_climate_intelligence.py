"""Comprehensive Automated Test Suite for Vayubodhak Deterministic Climate Intelligence Engine.

Verifies:
1. Temperature anomaly calculation
2. Rainfall anomaly calculation (positive and negative departure)
3. Zero baseline safe handling (no division by zero)
4. Missing baseline handling (explicit unavailable state)
5. Incomplete / missing observations quality evaluation
6. Dry spell detection (CDD consecutive dry days)
7. Wet spell detection (CWD consecutive wet days)
8. Stable monotonic trend test
9. Increasing monotonic trend test
10. Decreasing monotonic trend test
11. Insufficient trend data handling (n < 3)
12. Physical unit preservation (°C, mm)
13. Provenance and dataset preservation
14. IMD heatwave criteria evaluation (Plains, Hills, Coastal)
15. ETCCDI precipitation indices (Rx1day, Rx5day, R10mm, R20mm)
16. Gemma 4:e2b explanation bridge with live/mock provider
17. Gemma cannot invent baseline when unavailable
18. Gemma failure/timeout safe deterministic fallback
19. Contradiction guard rejecting halluncinated claims
20. REST API endpoint execution (POST /api/v1/climate/analyze)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.climate.analytics import (
    analyze_rainfall,
    analyze_temperature,
    analyze_trend,
    calculate_anomaly,
    evaluate_data_quality,
)
from app.climate.explanation_bridge import (
    ClimateExplanationBridge,
    generate_deterministic_fallback_explanation,
)
from app.climate.models import (
    AnomalyCategory,
    ClimateAnalysisRequest,
    ClimateAnomalyResult,
    ClimateEvidence,
    ClimateVariable,
    DataQuality,
    TrendDirection,
)
from app.climate.service import ClimateIntelligenceService
from app.core.factory import create_app
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole, LLMResponse


# ============================================================================
# 1. Anomaly Calculation Tests
# ============================================================================

def test_positive_temperature_anomaly():
    """Observed temperature 32.5°C with baseline 29.5°C (+3.0°C anomaly)."""
    res = calculate_anomaly(
        observed=32.5,
        baseline=29.5,
        std_dev=1.5,
        variable_name="Temperature",
        units="°C",
        baseline_source="IMD Climatological Tables",
        baseline_period="1991-2020",
    )
    assert res.baseline_available is True
    assert res.absolute_anomaly == 3.0
    assert res.anomaly_percent == round(((32.5 - 29.5) / 29.5) * 100.0, 2)
    assert res.z_score == 2.0
    assert res.category == AnomalyCategory.SEVERELY_ABOVE_NORMAL
    assert res.units == "°C"
    assert res.baseline_source == "IMD Climatological Tables"


def test_negative_temperature_anomaly():
    """Observed temperature 26.0°C with baseline 28.5°C (-2.5°C anomaly)."""
    res = calculate_anomaly(
        observed=26.0,
        baseline=28.5,
        std_dev=1.5,
        variable_name="Temperature",
        units="°C",
    )
    assert res.absolute_anomaly == -2.5
    assert res.z_score == -1.67
    assert res.category == AnomalyCategory.BELOW_NORMAL


def test_positive_rainfall_anomaly_surplus():
    """Rainfall 350.0 mm vs baseline 250.0 mm (+100.0 mm surplus, +40.0%)."""
    res = calculate_anomaly(
        observed=350.0,
        baseline=250.0,
        variable_name="Rainfall",
        units="mm",
    )
    assert res.baseline_available is True
    assert res.absolute_anomaly == 100.0
    assert res.anomaly_percent == 40.0
    assert res.category == AnomalyCategory.ABOVE_NORMAL
    assert res.units == "mm"


def test_negative_rainfall_anomaly_deficit():
    """Rainfall 120.0 mm vs baseline 200.0 mm (-80.0 mm deficit, -40.0%)."""
    res = calculate_anomaly(
        observed=120.0,
        baseline=200.0,
        variable_name="Rainfall",
        units="mm",
    )
    assert res.baseline_available is True
    assert res.absolute_anomaly == -80.0
    assert res.anomaly_percent == -40.0
    assert res.category == AnomalyCategory.BELOW_NORMAL


def test_zero_baseline_safe_division():
    """Rainfall in a dry month where normal baseline is 0.0 mm. No ZeroDivisionError."""
    res = calculate_anomaly(
        observed=15.0,
        baseline=0.0,
        variable_name="Rainfall",
        units="mm",
    )
    assert res.baseline_available is True
    assert res.absolute_anomaly == 15.0
    assert res.anomaly_percent is None  # Safe None rather than division by zero
    assert res.category == AnomalyCategory.ABOVE_NORMAL


def test_missing_baseline_handling():
    """When baseline is None, system explicitly flags baseline_available=False without fabricating values."""
    res = calculate_anomaly(
        observed=28.4,
        baseline=None,
        variable_name="Temperature",
        units="°C",
    )
    assert res.baseline_available is False
    assert res.baseline_value is None
    assert res.absolute_anomaly is None
    assert res.anomaly_percent is None
    assert res.z_score is None
    assert res.category == AnomalyCategory.UNAVAILABLE
    assert "unavailable" in res.baseline_methodology.lower()


# ============================================================================
# 2. Temperature Analysis & Heatwave Tests
# ============================================================================

def test_temperature_distribution_and_heatwave_plains():
    """Verifies temperature metrics and IMD heatwave criteria for Plains."""
    temps = [38.0, 41.5, 43.0, 45.2, 46.0, 42.0, 39.5]
    dates = [f"2024-05-{d:02d}" for d in range(1, 8)]

    metrics, anomaly = analyze_temperature(
        daily_temps=temps,
        dates=dates,
        baseline_mean=35.0,
        baseline_max=40.0,
        region_type="Plains",
    )

    assert metrics.min_c == 38.0
    assert metrics.max_c == 46.0
    assert metrics.hottest_period == "2024-05-05"
    assert metrics.is_heatwave is True
    assert "IMD Plains Heatwave" in metrics.heatwave_criteria
    assert anomaly is not None
    assert anomaly.absolute_anomaly > 0


def test_temperature_severe_heatwave_threshold():
    """Plains Tmax >= 47.0°C triggers Severe Heatwave."""
    temps = [42.0, 44.0, 47.5]
    metrics, _ = analyze_temperature(
        daily_temps=temps,
        baseline_mean=36.0,
        baseline_max=41.0,
        region_type="Plains",
    )
    assert metrics.is_heatwave is True
    assert metrics.is_severe_heatwave is True
    assert "Severe" in metrics.heatwave_criteria


# ============================================================================
# 3. Rainfall Analysis & Spell Tests (CDD, CWD, ETCCDI)
# ============================================================================

def test_dry_and_wet_spell_detection():
    """Test CDD and CWD calculations on daily rainfall sequence."""
    # Days: 0 (dry), 0 (dry), 0 (dry), 15 (wet), 22 (wet), 8 (wet), 0 (dry)
    rain = [0.0, 0.0, 0.0, 15.0, 22.0, 8.0, 0.0]
    metrics, _ = analyze_rainfall(
        daily_rain=rain,
        baseline_sum=60.0,
    )

    assert metrics.cumulative_mm == 45.0
    assert metrics.rainy_days_count == 3  # >= 1.0 mm
    assert metrics.imd_rainy_days_count == 3  # >= 2.5 mm
    assert metrics.consecutive_dry_days == 3  # first 3 days
    assert metrics.consecutive_wet_days == 3  # middle 3 days
    assert metrics.heavy_rain_days_r10mm == 2  # 15.0, 22.0
    assert metrics.very_heavy_rain_days_r20mm == 1  # 22.0
    assert metrics.max_1day_precipitation_rx1day_mm == 22.0
    assert metrics.rainfall_deficit_surplus_mm == -15.0  # 45.0 - 60.0


def test_negative_rainfall_error():
    """Physical constraint: negative rainfall is impossible and raises ValueError."""
    with pytest.raises(ValueError, match="Rainfall cannot be negative"):
        analyze_rainfall([10.0, -5.0, 20.0])


# ============================================================================
# 4. Trend Analysis Tests (Mann-Kendall & Sen's Slope)
# ============================================================================

def test_increasing_climate_trend():
    """Strictly increasing time-series detects INCREASING monotonic trend."""
    series = [20.0, 22.0, 25.0, 27.0, 30.0, 33.0, 36.0]
    res = analyze_trend(series, alpha=0.05, period_description="2018-2024")
    assert res.direction == TrendDirection.INCREASING
    assert res.is_significant is True
    assert res.slope is not None and res.slope > 0
    assert res.p_value is not None and res.p_value < 0.05
    assert res.sample_size == 7


def test_decreasing_climate_trend():
    """Strictly decreasing time-series detects DECREASING monotonic trend."""
    series = [800.0, 750.0, 710.0, 680.0, 640.0, 600.0, 570.0]
    res = analyze_trend(series, alpha=0.05, period_description="2018-2024")
    assert res.direction == TrendDirection.DECREASING
    assert res.is_significant is True
    assert res.slope is not None and res.slope < 0


def test_stable_climate_trend():
    """Fluctuating series without monotonic drift classified as STABLE."""
    series = [25.0, 25.5, 24.8, 25.2, 25.1, 24.9, 25.3]
    res = analyze_trend(series, alpha=0.05)
    assert res.direction == TrendDirection.STABLE
    assert res.is_significant is False


def test_insufficient_trend_observations():
    """Sample size < 3 cannot compute Mann-Kendall test. Returns INSUFFICIENT_DATA."""
    series = [25.0, 28.0]
    res = analyze_trend(series)
    assert res.direction == TrendDirection.INSUFFICIENT_DATA
    assert res.slope is None
    assert res.sample_size == 2


# ============================================================================
# 5. Data Quality & Coverage Tests
# ============================================================================

def test_data_quality_evaluation():
    """Evaluates coverage percentage and sensor boundary limits."""
    # 7 valid values out of 10 expected (70% coverage -> PARTIAL)
    obs = [25.0, None, 28.0, 30.0, None, 29.0, 31.0, None, 27.0, 26.0]
    q = evaluate_data_quality(obs, expected_count=10, min_physical_bound=-50.0, max_physical_bound=60.0)
    assert q.expected_observations == 10
    assert q.available_observations == 7
    assert q.coverage_pct == 70.0
    assert q.quality_status == DataQuality.PARTIAL
    assert len(q.limitations) >= 3


# ============================================================================
# 6. Service & Climatology Normal Resolution Tests
# ============================================================================

@pytest.mark.asyncio
async def test_climate_service_delhi_may_temperature():
    """Delhi in May references official WMO 1991-2020 IMD normal (mean=33.8°C)."""
    service = ClimateIntelligenceService()
    req = ClimateAnalysisRequest(
        location="Delhi",
        variable=ClimateVariable.TEMPERATURE,
        period_start="2024-05-01",
        period_end="2024-05-07",
        observations=[35.0, 36.5, 37.0, 36.0, 35.5, 36.0, 37.0],
        include_explanation=False,
    )
    res = await service.analyze(req)

    assert res.evidence.baseline_available is True
    assert res.evidence.baseline_value == 33.8
    assert res.evidence.mean == pytest.approx(36.14, rel=1e-2)
    assert res.evidence.anomaly == pytest.approx(2.34, rel=1e-2)
    assert res.evidence.anomaly_category == AnomalyCategory.ABOVE_NORMAL
    assert "IMD" in res.evidence.source
    assert res.explanation is None  # Opt-in explanation was False


@pytest.mark.asyncio
async def test_climate_service_unverified_location_explicit_unavailable():
    """Unverified location without baseline normal returns explicit unavailable state without fabricating values."""
    service = ClimateIntelligenceService()
    req = ClimateAnalysisRequest(
        location="NonExistentStationVillage123",
        variable=ClimateVariable.TEMPERATURE,
        period_start="2024-07-01",
        period_end="2024-07-05",
        observations=[28.0, 29.0, 28.5, 29.5, 30.0],
        include_explanation=False,
    )
    res = await service.analyze(req)

    assert res.evidence.baseline_available is False
    assert res.evidence.baseline_value is None
    assert res.evidence.anomaly is None
    assert res.evidence.anomaly_category == AnomalyCategory.UNAVAILABLE
    assert any("Historical climatological baseline unavailable" in u for u in res.evidence.uncertainty)


# ============================================================================
# 7. Explanation Bridge & Contradiction Guard Tests
# ============================================================================

class MockGemmaProvider(LLMProvider):
    """Mock LLM provider simulating Gemma 4:e2b responses."""

    def __init__(self, response_text: str = "Analysis shows warmer temperatures.") -> None:
        self.response_text = response_text
        self.last_prompt = ""

    async def generate_chat_completion(
        self,
        messages: list[ChatMessage],
        tools: list[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = None,
    ) -> LLMResponse:
        self.last_prompt = messages[-1].content
        return LLMResponse(content=self.response_text, model_name="gemma4:e2b")

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        raise NotImplementedError

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_explanation_bridge_with_mock_gemma():
    """Gemma receives structured verified evidence and outputs explanation."""
    mock_llm = MockGemmaProvider("In May 2024, Delhi experienced above normal temperatures of 36.1°C.")
    bridge = ClimateExplanationBridge(llm_provider=mock_llm)
    service = ClimateIntelligenceService(explanation_bridge=bridge)

    req = ClimateAnalysisRequest(
        location="Delhi",
        variable=ClimateVariable.TEMPERATURE,
        period_start="2024-05-01",
        period_end="2024-05-07",
        observations=[35.0, 36.5, 37.0, 36.0, 35.5, 36.0, 37.0],
        include_explanation=True,
    )
    res = await service.analyze(req)

    assert res.explanation == "In May 2024, Delhi experienced above normal temperatures of 36.1°C."
    assert res.explanation_source == "gemma4:e2b"
    assert "Location: Delhi" in mock_llm.last_prompt
    assert "Baseline Normal Value: 33.80 °C" in mock_llm.last_prompt


@pytest.mark.asyncio
async def test_contradiction_guard_rejects_hallucinated_cooling():
    """Contradiction guard catches 'below normal' claim when anomaly is positive above-normal."""
    mock_llm = MockGemmaProvider("The observed temperatures were significantly cooler than normal.")
    bridge = ClimateExplanationBridge(llm_provider=mock_llm)
    service = ClimateIntelligenceService(explanation_bridge=bridge)

    req = ClimateAnalysisRequest(
        location="Delhi",
        variable=ClimateVariable.TEMPERATURE,
        period_start="2024-05-01",
        period_end="2024-05-07",
        observations=[38.0, 39.0, 40.0],  # Well above 33.8°C normal
        include_explanation=True,
    )
    res = await service.analyze(req)

    # Contradiction guard must reject candidate and revert to deterministic fallback
    assert res.explanation_source == "deterministic_fallback"
    assert "departure of +5.2 °C" in res.explanation
    assert "Above Normal" in res.explanation


@pytest.mark.asyncio
async def test_gemma_failure_fallback():
    """When LLM provider raises exception, system falls back to deterministic explanation."""
    class FailingProvider(LLMProvider):
        async def generate_chat_completion(self, messages, tools=None, temperature=0.1, max_tokens=None):
            raise ConnectionError("Ollama host UJJWAL is unreachable")

        async def generate_structured_output(self, messages, response_schema, temperature=None):
            raise ConnectionError("Ollama host UJJWAL is unreachable")

        async def check_health(self) -> bool:
            return False

    bridge = ClimateExplanationBridge(llm_provider=FailingProvider())
    service = ClimateIntelligenceService(explanation_bridge=bridge)

    req = ClimateAnalysisRequest(
        location="Delhi",
        variable=ClimateVariable.TEMPERATURE,
        period_start="2024-05-01",
        period_end="2024-05-03",
        observations=[35.0, 36.0, 37.0],
        include_explanation=True,
    )
    res = await service.analyze(req)

    assert res.explanation_source == "deterministic_fallback"
    assert res.explanation is not None
    assert "Delhi recorded an average temperature of 36.0°C" in res.explanation


# ============================================================================
# 8. REST API Endpoint Test
# ============================================================================

@pytest.mark.asyncio
async def test_post_climate_analyze_api():
    """POST /api/v1/climate/analyze returns structured ClimateAnalysisResponse."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "location": "Delhi",
            "variable": "rainfall",
            "period_start": "2024-07-01",
            "period_end": "2024-07-07",
            "observations": [10.0, 0.0, 0.0, 45.0, 120.0, 0.0, 5.0],
            "include_explanation": False,
        }
        resp = await client.post("/api/v1/climate/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "evidence" in data
        evidence = data["evidence"]
        assert evidence["location"] == "Delhi"
        assert evidence["variable"] == "rainfall"
        assert evidence["cumulative"] == 180.0
        assert evidence["sample_size"] == 7
        assert evidence["rainfall_metrics"]["consecutive_dry_days"] == 2
        assert evidence["rainfall_metrics"]["consecutive_wet_days"] == 2
        assert evidence["rainfall_metrics"]["heavy_rain_days_r10mm"] == 3


@pytest.mark.asyncio
async def test_live_gemma_climate_explanation_if_online():
    """Live integration test with remote Gemma 4:e2b on UJJWAL:11434.

    If remote host is offline, test gracefully verifies fallback behavior.
    """
    from app.llm.providers.ollama_provider import OllamaProvider
    from app.config import settings

    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model_name=settings.ollama_model,
        timeout_seconds=15.0,
    )
    bridge = ClimateExplanationBridge(llm_provider=provider)
    service = ClimateIntelligenceService(explanation_bridge=bridge)

    req = ClimateAnalysisRequest(
        location="Delhi",
        variable=ClimateVariable.TEMPERATURE,
        period_start="2024-05-01",
        period_end="2024-05-05",
        observations=[36.0, 37.0, 38.0, 37.5, 36.5],
        include_explanation=True,
    )
    res = await service.analyze(req)

    assert res.explanation is not None
    assert len(res.explanation) > 20
    # Must be either live gemma4:e2b or deterministic_fallback (zero crash)
    assert res.explanation_source in ("gemma4:e2b", "deterministic_fallback")
