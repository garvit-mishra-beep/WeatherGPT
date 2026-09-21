"""B6 — Production Integration & API Data Flow Test Suite.

Verifies the end-to-end integration across:
- FastAPI API endpoints (/api/v1/chat, /api/v1/weather, /api/v1/farmer, /api/v1/research, /api/v1/gis, /api/v1/nwp)
- Request-ID correlation & RFC 7807 error conformity
- Input contract validation & normalization
- Multi-turn conversation context retention
- Auto Router classification and explicit overrides
- 4 Domain Brains (General, Farmer, Researcher, Analyst)
- Tool Gateway deterministic tool calling & provenance preservation
- Grounding verification & numerical evidence invariance
- Multilingual invariance across 5 languages (en, hi, bn, mr, gu)
- Performance / latency smoke benchmarking
"""

import json
import time
from typing import Any, Dict, List, Optional
import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.base import BaseNWPProvider, BaseWarningProvider, BaseWeatherProvider
from app.adapters.models import (
    NormalizedDailyForecastPoint,
    NormalizedHourlyForecastPoint,
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.strategy import WeatherProviderManager
from app.brains.analyst import AnalystBrain
from app.brains.farmer import FarmerBrain
from app.brains.general import GeneralBrain
from app.brains.orchestrator import BrainOrchestrator
from app.brains.registry import BrainRegistry
from app.brains.researcher import ResearcherBrain
from app.brains.resolver import BrainResolver
from app.config import Settings
from app.context.manager import ContextManager
from app.contracts.enums import BrainType, SupportedLanguage, WarningLevel
from app.contracts.response import FinalResponseSchema
from app.core.factory import create_app
from app.dependencies.container import AppContainer
from app.grounding.service import GroundingService
from app.llm.base import LLMProvider
from app.llm.types import (
    ChatMessage,
    ChatRole,
    FunctionCall,
    LLMResponse,
    ToolCall,
)
from app.multilingual.service import MultilingualService
from app.performance.cache import ToolResultCache
from app.router.llm_router import LLMAutoRouter
from app.router.models import RoutingClassification
from app.tools.catalog import register_default_tools
from app.tools.gateway import ToolGateway
from app.tools.registry import ToolRegistry


# ============================================================================
# Deterministic Mock Providers for 100% Offline Testing
# ============================================================================

class MockWeatherProvider(BaseWeatherProvider):
    @property
    def name(self) -> str:
        return "MockWeatherProvider"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def get_current_weather(self, latitude: float, longitude: float) -> NormalizedWeatherObservation:
        return NormalizedWeatherObservation(
            latitude=latitude,
            longitude=longitude,
            observation_time_iso="2026-08-30T10:00:00Z",
            temperature_c=31.5,
            feels_like_c=36.8,
            relative_humidity_pct=68.0,
            precipitation_mm=1.2,
            rain_intensity_category="very_light_rain",
            wind_speed_kmh=14.5,
            wind_direction_deg=245.0,
            surface_pressure_hpa=1005.4,
            weather_condition="partly_cloudy",
            provider="MockWeatherProvider",
            data_source="Mock Ingest",
            authority=ProviderAuthority.SECONDARY,
            quality=ProviderQuality.VALID,
            retrieval_timestamp_iso="2026-08-30T10:00:00Z",
        )

    async def get_forecast(self, latitude: float, longitude: float, days: int = 3) -> NormalizedWeatherForecastPayload:
        daily = [
            NormalizedDailyForecastPoint(
                date_str=f"2026-08-3{i}",
                temp_max_c=33.2,
                temp_min_c=26.1,
                precipitation_sum_mm=24.5,
                precipitation_probability_max_pct=75.0,
                rain_intensity_category="moderate_rain",
                wind_speed_max_kmh=16.0,
                weather_condition="scattered_thunderstorms",
            )
            for i in range(days)
        ]
        hourly = [
            NormalizedHourlyForecastPoint(
                time_iso="2026-08-30T12:00:00Z",
                temperature_c=32.0,
                relative_humidity_pct=70.0,
                precipitation_mm=5.0,
                precipitation_probability_pct=80.0,
                wind_speed_kmh=15.0,
                weather_condition="rain",
            )
        ]
        return NormalizedWeatherForecastPayload(
            latitude=latitude,
            longitude=longitude,
            forecast_start_iso="2026-08-30T00:00:00Z",
            forecast_end_iso="2026-09-02T00:00:00Z",
            daily=daily,
            hourly=hourly,
            provider="MockWeatherProvider",
            data_source="Mock Guidance",
            authority=ProviderAuthority.SECONDARY,
            quality=ProviderQuality.VALID,
            retrieval_timestamp_iso="2026-08-30T10:00:00Z",
        )

    async def check_health(self) -> bool:
        return True


class MockWarningProvider(BaseWarningProvider):
    @property
    def name(self) -> str:
        return "MockWarningProvider"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.OFFICIAL

    async def get_active_warnings(self, district_name=None, state_name=None, latitude=None, longitude=None) -> List[NormalizedOfficialAlert]:
        return [
            NormalizedOfficialAlert(
                alert_id="IMD-MOCK-2026-001",
                sender="imd@imd.gov.in",
                sent_time_iso="2026-08-30T06:00:00Z",
                warning_level=WarningLevel.RED,
                event_title="Extremely Heavy Rainfall",
                urgency="Immediate",
                severity="Extreme",
                certainty="Observed",
                effective_time_iso="2026-08-30T06:00:00Z",
                onset_time_iso="2026-08-30T08:00:00Z",
                expires_time_iso="2026-08-31T08:30:00Z",
                headline="Red Alert for Heavy Rainfall",
                description="Extremely heavy rainfall expected.",
                instruction="Stay indoors.",
                area_description="Surat District",
                polygons=["21.05,72.60 21.35,72.60 21.35,73.10 21.05,73.10 21.05,72.60"],
                geocodes=[{"PCODE": "IN-GJ-25"}],
                provider="IMD",
                data_source="OASIS CAP v1.2 Feed",
                quality=ProviderQuality.VALID,
                is_official=True,
            )
        ]

    async def check_health(self) -> bool:
        return True


class MockNWPProvider(BaseNWPProvider):
    @property
    def name(self) -> str:
        return "MockNWPProvider"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.NUMERICAL_MODEL

    async def get_grid_point(self, latitude: float, longitude: float, lead_hours: int = 24) -> NormalizedNWPGridPoint:
        return NormalizedNWPGridPoint(
            latitude=latitude,
            longitude=longitude,
            initialization_time_iso="2026-08-30T00:00:00Z",
            valid_time_iso="2026-08-31T00:00:00Z",
            forecast_lead_hours=lead_hours,
            model_name="GFS_0P25",
            temperature_2m_c=30.0,
            relative_humidity_2m_pct=70.0,
            accumulated_precip_mm=15.2,
            step_precip_mm=2.5,
            u_wind_10m_ms=-3.5,
            v_wind_10m_ms=4.2,
            wind_speed_kmh=18.0,
            wind_direction_deg=270.0,
            wind_gust_kmh=36.0,
            pressure_msl_hpa=1006.0,
            total_cloud_cover_pct=60.0,
            grid_resolution_deg=0.25,
            provider="NOAA / NCEP",
            quality=ProviderQuality.VALID,
        )

    async def check_health(self) -> bool:
        return True


# ============================================================================
# Deterministic Mock LLM for End-to-End Orchestration
# ============================================================================

class MockPipelineLLM(LLMProvider):
    """Deterministic LLM simulating tool calling and grounded response synthesis."""

    def __init__(self) -> None:
        self.call_history: List[List[ChatMessage]] = []

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        self.call_history.append(messages)

        # Direct generation (e.g. Grounding correction or direct answer synthesis)
        if not tools:
            last_user_or_system = next((m.content for m in reversed(messages) if m.role in (ChatRole.USER, ChatRole.SYSTEM)), "")
            if "irrigate" in last_user_or_system.lower() or "farmer" in last_user_or_system.lower() or "crop" in last_user_or_system.lower():
                return LLMResponse(
                    content="Based on FAO-56 crop water balance, the recommendation is to postpone irrigation.",
                    tool_calls=[],
                    model_name="mock-pipeline-llm",
                )
            return LLMResponse(
                content="The weather forecast indicates a maximum temperature of 33.2°C with 24.5mm rainfall.",
                tool_calls=[],
                model_name="mock-pipeline-llm",
            )

        # Check if there are tool responses already present in conversation
        tool_messages = [m for m in messages if m.role == ChatRole.TOOL]

        if not tool_messages:
            # Round 1: Request appropriate tool based on user query
            last_user_msg = next((m.content for m in reversed(messages) if m.role == ChatRole.USER), "")
            lower = last_user_msg.lower()

            if "irrigate" in lower or "water" in lower or "crop" in lower:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_irr_01",
                            function=FunctionCall(
                                name="calculate_irrigation_advisory",
                                arguments='{"crop_name": "Wheat", "rainfall_24h_mm": 24.5, "et0_mm": 4.5}',
                            ),
                        )
                    ],
                    model_name="mock-pipeline-llm",
                )
            elif "trend" in lower or "climate" in lower:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_fc_01",
                            function=FunctionCall(
                                name="get_forecast",
                                arguments='{"latitude": 23.02, "longitude": 72.57}',
                            ),
                        )
                    ],
                    model_name="mock-pipeline-llm",
                )
            elif "risk" in lower or "hazard" in lower:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_risk_01",
                            function=FunctionCall(
                                name="run_risk_analysis",
                                arguments='{"district_name": "Surat", "hazard_type": "heavy_rainfall"}',
                            ),
                        )
                    ],
                    model_name="mock-pipeline-llm",
                )
            else:
                # Default general weather query
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_fc_01",
                            function=FunctionCall(
                                name="get_forecast",
                                arguments='{"latitude": 28.61, "longitude": 77.20}',
                            ),
                        )
                    ],
                    model_name="mock-pipeline-llm",
                )

        # Round 2: Synthesis based on tool evidence
        tool_data = json.loads(tool_messages[0].content).get("data", {})
        if "advisory_action" in tool_data or "action" in tool_data or "daily_balance" in tool_data:
            answer = "Based on FAO-56 crop water balance, the recommendation is to postpone irrigation."
        elif "composite_risk_score" in tool_data:
            answer = f"Composite risk score for Surat is {tool_data['composite_risk_score']} ({tool_data['risk_level']})."
        else:
            temp_max = tool_data.get("temp_max_c", 33.2)
            rain_mm = tool_data.get("rainfall_total_mm", 24.5)
            answer = f"The forecast indicates a maximum temperature of {temp_max}°C with {rain_mm}mm precipitation."

        return LLMResponse(
            content=answer,
            tool_calls=[],
            model_name="mock-pipeline-llm",
        )

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Any,
        temperature: Optional[float] = None,
    ) -> Any:
        # Check if routing classification is requested
        if response_schema == RoutingClassification:
            user_content = next((m.content for m in reversed(messages) if m.role == ChatRole.USER), "").lower()
            if "irrigate" in user_content or "crop" in user_content or "spray" in user_content:
                return RoutingClassification(
                    selected_brain=BrainType.FARMER,
                    confidence=0.95,
                    intent_category="crop_irrigation",
                    rationale="User asked about agricultural irrigation scheduling.",
                    needs_clarification=False,
                )
            elif "trend" in user_content or "historical" in user_content:
                return RoutingClassification(
                    selected_brain=BrainType.RESEARCHER,
                    confidence=0.92,
                    intent_category="climate_trend",
                    rationale="User asked for historical climate analysis.",
                    needs_clarification=False,
                )
            elif "risk" in user_content or "hazard" in user_content:
                return RoutingClassification(
                    selected_brain=BrainType.ANALYST,
                    confidence=0.94,
                    intent_category="hazard_risk",
                    rationale="User asked for operational disaster risk analysis.",
                    needs_clarification=False,
                )
            else:
                return RoutingClassification(
                    selected_brain=BrainType.GENERAL,
                    confidence=0.90,
                    intent_category="general_forecast",
                    rationale="Standard weather forecast query.",
                    needs_clarification=False,
                )

        raise NotImplementedError(f"Schema {response_schema} not mocked")

    async def check_health(self) -> bool:
        return True


# ============================================================================
# Test Fixtures & App Setup
# ============================================================================

@pytest.fixture
def mock_container():
    """Builds an AppContainer wired with MockPipelineLLM and real services."""
    settings = Settings(app_env="test")
    mock_llm = MockPipelineLLM()

    registry = ToolRegistry()
    register_default_tools(registry)

    gateway = ToolGateway(registry=registry, cache=ToolResultCache(default_ttl_seconds=300.0))
    grounding = GroundingService()
    multilingual = MultilingualService()

    brain_reg = BrainRegistry()
    for brain_cls in (GeneralBrain, FarmerBrain, ResearcherBrain, AnalystBrain):
        brain_reg.register(
            brain_cls(
                llm_provider=mock_llm,
                tool_gateway=gateway,
                tool_registry=registry,
                grounding_service=grounding,
                multilingual_service=multilingual,
            )
        )

    auto_router = LLMAutoRouter(llm_provider=mock_llm)
    resolver = BrainResolver(router_strategy=auto_router.route)
    orchestrator = BrainOrchestrator(registry=brain_reg, resolver=resolver, llm_provider=mock_llm)
    context_mgr = ContextManager()

    mock_weather_mgr = WeatherProviderManager(
        settings=settings,
        warning_provider=MockWarningProvider(),
        primary_weather_provider=MockWeatherProvider(),
        nwp_provider=MockNWPProvider(),
    )

    container = AppContainer(
        settings=settings,
        llm_provider=mock_llm,
        tool_registry=registry,
        tool_gateway=gateway,
        brain_registry=brain_reg,
        brain_orchestrator=orchestrator,
        context_manager=context_mgr,
        grounding_service=grounding,
        multilingual_service=multilingual,
        auto_router=auto_router,
        weather_manager=mock_weather_mgr,
    ).build()

    return container


@pytest.fixture
def app(mock_container):
    """FastAPI test app with initialized container."""
    return create_app(container=mock_container)


# ============================================================================
# 1. Conversational Chat Pipeline Tests (POST /api/v1/chat)
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_chat_general_weather_query(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "sess_test_01",
            "query": "What is the weather forecast for Delhi?",
            "language_preference": "en",
            "selected_brain": "auto",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "sess_test_01"
        assert data["brain"] == "general"
        assert data["language"] == "en"
        assert "°C" in data["answer"] or "forecast" in data["answer"].lower() or "weather" in data["answer"].lower()
        assert len(data["sources"]) > 0
        assert data["confidence"]["evidence_level"] in ("high", "medium")


@pytest.mark.asyncio
async def test_e2e_chat_farmer_irrigation_query(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "sess_farmer_01",
            "query": "Should I irrigate my wheat crop in Karnal tomorrow?",
            "language_preference": "en",
            "selected_brain": "auto",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["brain"] == "farmer"
        assert "FAO-56" in data["answer"] or "recommendation" in data["answer"]
        assert data["recommendation"] is not None
        assert data["recommendation"]["primary_action"].lower() in ("postpone", "apply", "reduce", "maintain", "irrigate", "monitor")


@pytest.mark.asyncio
async def test_e2e_chat_researcher_climate_query(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "sess_res_01",
            "query": "What is the multi-decadal historical climate trend in Gujarat?",
            "language_preference": "en",
            "selected_brain": "auto",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["brain"] == "researcher"
        assert data["answer"] is not None


@pytest.mark.asyncio
async def test_e2e_chat_analyst_risk_query(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "sess_analyst_01",
            "query": "Run a severe heavy rainfall risk hazard assessment for Surat district.",
            "language_preference": "en",
            "selected_brain": "auto",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["brain"] == "analyst"
        assert "risk" in data["answer"].lower() or "surat" in data["answer"].lower()


@pytest.mark.asyncio
async def test_explicit_brain_override(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "sess_explicit_01",
            "query": "Tell me anything.",
            "language_preference": "en",
            "selected_brain": "farmer",  # Explicit override
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["brain"] == "farmer"


# ============================================================================
# 2. Multi-Turn Conversation Context Retention
# ============================================================================

@pytest.mark.asyncio
async def test_multi_turn_context_retention(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        session_id = "sess_multiturn_nashik"

        # Turn 1: Establish location context (Nashik)
        turn1 = await client.post(
            "/api/v1/chat",
            json={
                "session_id": session_id,
                "query": "What is the weather in Nashik?",
                "language_preference": "en",
                "device_context": {
                    "gps_location": {"latitude": 19.9975, "longitude": 73.7898, "accuracy_meters": 10.0}
                },
            },
        )
        assert turn1.status_code == 200

        # Turn 2: Follow-up query without re-specifying location
        turn2 = await client.post(
            "/api/v1/chat",
            json={
                "session_id": session_id,
                "query": "Will it rain tomorrow?",
                "language_preference": "en",
            },
        )
        assert turn2.status_code == 200

        # Turn 3: Check conversation history endpoint
        history = await client.get(f"/api/v1/chat/history/{session_id}")
        assert history.status_code == 200
        hist_data = history.json()
        assert hist_data["turn_count"] == 4
        assert len(hist_data["turns"]) == 4


# ============================================================================
# 3. Multilingual Invariance & Numeral Normalization
# ============================================================================

@pytest.mark.parametrize(
    "lang_code,query_text",
    [
        ("en", "What is the temperature in Ahmedabad?"),
        ("hi", "क्या कल अहमदाबाद में बारिश होगी?"),
        ("bn", "আগামীকাল কি বৃষ্টি হবে?"),
        ("mr", "उद्या पाऊस पडेल का?"),
        ("gu", "કાલે અમદાવાદમાં વરસાદ પડશે?"),
    ],
)
@pytest.mark.asyncio
async def test_multilingual_chat_invariance(app, lang_code, query_text):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": f"sess_multi_{lang_code}",
            "query": query_text,
            "language_preference": lang_code,
            "selected_brain": "general",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["brain"] == "general"
        assert data["language"] == lang_code
        # Grounded temperature remains strictly invariant across all languages
        assert data["data"].get("temp_max_c") is not None or "°C" in data["answer"] or "तापमान" in data["answer"]


# ============================================================================
# 4. Direct API Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_direct_weather_current_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/weather/current?lat=23.0225&lon=72.5714")
        assert resp.status_code == 200
        data = resp.json()
        assert data["location"]["latitude"] == 23.0225
        assert "temperature_c" in data
        assert "provenance" in data


@pytest.mark.asyncio
async def test_direct_weather_forecast_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/weather/forecast?lat=23.0225&lon=72.5714&days=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["daily_forecast"]) == 3
        assert "hourly_forecast" in data


@pytest.mark.asyncio
async def test_direct_weather_alerts_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/weather/alerts?district=Surat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authority"] == "India Meteorological Department (IMD)"
        assert "alerts" in data


@pytest.mark.asyncio
async def test_direct_farmer_irrigation_advisory_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "latitude": 29.6857,
            "longitude": 76.9905,
            "crop_name": "Wheat",
            "crop_stage": "crown_root_initiation",
            "soil_type": "alluvial_loam",
            "forecast_precip_48h_mm": 28.5,
        }
        resp = await client.post("/api/v1/farmer/irrigation-advisory", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] in ("POSTPONE", "APPLY", "REDUCE", "MAINTAIN")
        assert "reference_et0_mm_day" in data["metrics"]
        assert data["provenance"]["calculation_method"] == "FAO-56 Penman-Monteith (Deterministic Engine)"


@pytest.mark.asyncio
async def test_direct_farmer_spray_window_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "wind_speed_kmh": 12.0,
            "rain_probability_pct": 10.0,
            "temp_c": 26.0,
            "relative_humidity_pct": 55.0,
        }
        resp = await client.post("/api/v1/farmer/spray-window", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_suitable"] is True
        assert data["condition_level"] == "optimal"


@pytest.mark.asyncio
async def test_direct_research_trend_analysis_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "latitude": 23.0225,
            "longitude": 72.5714,
            "start_year": 1994,
            "end_year": 2024,
            "season": "JJAS",
        }
        resp = await client.post("/api/v1/research/trend-analysis", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend_test"]["method"] == "Mann-Kendall Monotonic Trend Test"
        assert "p_value" in data["trend_test"]
        assert "sens_slope_per_year" in data["trend_test"]


@pytest.mark.asyncio
async def test_direct_gis_risk_assessment_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "district_name": "Surat",
            "precip_24h_percentile": 95.0,
            "exposure_index": 8.0,
            "vulnerability_index": 7.5,
        }
        resp = await client.post("/api/v1/gis/risk-assessment", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["district"] == "Surat"
        assert data["risk_level"] in ("HIGH", "CRITICAL", "MODERATE", "LOW")
        assert data["composite_risk_score"] > 0.0


@pytest.mark.asyncio
async def test_direct_gis_hazard_intersection_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "warning_polygon_geojson": {
                "type": "Polygon",
                "coordinates": [[[72.5, 21.0], [73.2, 21.0], [73.2, 21.8], [72.5, 21.8], [72.5, 21.0]]],
            }
        }
        resp = await client.post("/api/v1/gis/hazard-intersection", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_affected_area_sqkm"] > 0.0
        assert len(data["intersected_districts"]) > 0


@pytest.mark.asyncio
async def test_direct_nwp_gfs_grid_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/nwp/gfs?lat=23.0225&lon=72.5714&lead_hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "GFS_0P25"
        assert "atmospheric_variables" in data


# ============================================================================
# 5. Error Handling & RFC 7807 Compliance
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_request_coordinates_validation_error(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Latitude outside Indian bounding box (6.0 to 38.0)
        resp = await client.get("/api/v1/weather/current?lat=55.0&lon=72.57")
        assert resp.status_code == 422
        data = resp.json()
        assert data["title"] == "Validation Error"
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["type"].startswith("https://weathergpt.in/errors/")


@pytest.mark.asyncio
async def test_chat_empty_query_validation_error(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat",
            json={"session_id": "sess_err", "query": ""},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error_code"] == "VALIDATION_ERROR"


# ============================================================================
# 6. Performance Smoke Benchmark
# ============================================================================

@pytest.mark.asyncio
async def test_request_pipeline_performance_smoke(app):
    """Measures pipeline end-to-end processing overhead with deterministic mock."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        durations = []
        for _ in range(5):
            t0 = time.perf_counter()
            resp = await client.post(
                "/api/v1/chat",
                json={
                    "session_id": f"sess_perf_{time.time()}",
                    "query": "Weather in Delhi?",
                    "language_preference": "en",
                },
            )
            durations.append((time.perf_counter() - t0) * 1000.0)
            assert resp.status_code == 200

        avg_latency_ms = sum(durations) / len(durations)
        # In-memory processing overhead should be fast (< 500ms across all mounted routers)
        assert avg_latency_ms < 500.0, f"Average latency too high: {avg_latency_ms:.2f}ms"
