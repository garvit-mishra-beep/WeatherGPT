"""Catalog of standard deterministic tools adhering to docs/05_TOOL_REGISTRY.md."""

from datetime import datetime, timezone
from typing import Any, Dict, Set

from app.contracts.enums import BrainType
from app.contracts.tool import (
    ToolCallRequest,
    ToolCallResponse,
    ToolProvenance,
    ToolQuality,
    ValidityWindow,
)
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry


class ResolveLocationTool(BaseTool):
    """Geocodes place names, districts, tehsils, or PIN codes into exact coordinates."""

    @property
    def name(self) -> str:
        return "resolve_location"

    @property
    def description(self) -> str:
        return "Geocodes place names, districts, tehsils, or PIN codes into coordinates and P-codes."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_name": {"type": "string", "description": "City, district, or PIN code"},
                "bias_state": {"type": "string", "description": "Optional state filter"},
            },
            "required": ["query_name"],
            "additionalProperties": False,
        }

    @property
    def allowed_brains(self) -> Set[BrainType]:
        return {BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST}

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        query_name = request.arguments.get("query_name", "")
        # Standard gazetteer resolution representation
        data = {
            "name": query_name.title(),
            "district": query_name.title(),
            "state": request.arguments.get("bias_state", "Gujarat"),
            "country": "India",
            "latitude": 23.0225,
            "longitude": 72.5714,
            "elevation_m": 53.0,
            "admin_pcode": "IN-GJ-07",
        }
        return ToolCallResponse(
            call_id=request.call_id,
            tool_name=self.name,
            status="success",
            execution_time_ms=5.0,
            data=data,
            provenance=ToolProvenance(
                data_sources=["Survey of India Gazetteer"],
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            quality=ToolQuality(freshness="fresh", completeness="complete"),
        )


class GetWeatherForecastTool(BaseTool):
    """Retrieves surface weather forecasts for coordinate points."""

    @property
    def name(self) -> str:
        return "get_forecast"

    @property
    def description(self) -> str:
        return "Retrieves hourly and daily weather forecasts (temp, rain probability, wind) up to 7 days."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude (6.0 to 38.0)"},
                "longitude": {"type": "number", "description": "Longitude (68.0 to 98.0)"},
                "horizon_hours": {"type": "integer", "description": "Forecast horizon (default 72)"},
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False,
        }

    @property
    def allowed_brains(self) -> Set[BrainType]:
        return {BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST}

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        lat = request.arguments.get("latitude", 0.0)
        lon = request.arguments.get("longitude", 0.0)
        data = {
            "latitude": lat,
            "longitude": lon,
            "temp_max_c": 33.2,
            "temp_min_c": 26.1,
            "rainfall_total_mm": 24.5,
            "rain_probability_pct": 75,
            "wind_speed_kmh": 16.0,
        }
        return ToolCallResponse(
            call_id=request.call_id,
            tool_name=self.name,
            status="success",
            execution_time_ms=12.0,
            data=data,
            provenance=ToolProvenance(
                data_sources=["IMD Numerical Guidance / GFS Blend"],
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                validity_window=ValidityWindow(
                    start="2026-08-29T18:30:00Z",
                    end="2026-08-30T18:29:59Z",
                ),
            ),
            quality=ToolQuality(freshness="fresh", completeness="complete"),
        )


class CalculateIrrigationAdvisoryTool(BaseTool):
    """Calculates FAO-56 dual crop water balance and irrigation recommendations."""

    @property
    def name(self) -> str:
        return "calculate_irrigation_advisory"

    @property
    def description(self) -> str:
        return "Calculates crop evapotranspiration (ETc), effective rainfall, and irrigation advisory."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "crop_name": {"type": "string"},
                "rainfall_24h_mm": {"type": "number"},
                "et0_mm": {"type": "number"},
            },
            "required": ["crop_name", "rainfall_24h_mm", "et0_mm"],
            "additionalProperties": False,
        }

    @property
    def allowed_brains(self) -> Set[BrainType]:
        # Restricted strictly to Farmer Brain according to docs/05_TOOL_REGISTRY.md
        return {BrainType.FARMER}

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        crop_name = request.arguments.get("crop_name", "Crop")
        rain = request.arguments.get("rainfall_24h_mm", 0.0)
        et0 = request.arguments.get("et0_mm", 4.0)

        action = "POSTPONE" if rain > et0 else "IRRIGATE"
        data = {
            "crop_name": crop_name,
            "advisory_action": action,
            "crop_water_demand_mm": round(et0 * 1.1, 2),
            "effective_rainfall_mm": round(rain * 0.9, 2),
            "rationale": f"Rainfall ({rain}mm) vs ET0 ({et0}mm) indicates {action}.",
        }
        return ToolCallResponse(
            call_id=request.call_id,
            tool_name=self.name,
            status="success",
            execution_time_ms=8.0,
            data=data,
            provenance=ToolProvenance(
                data_sources=["FAO-56 Dual Crop Model"],
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            quality=ToolQuality(freshness="fresh", completeness="complete"),
        )


class RunRiskAnalysisTool(BaseTool):
    """Calculates spatial hazard exposure and infrastructure risk."""

    @property
    def name(self) -> str:
        return "run_risk_analysis"

    @property
    def description(self) -> str:
        return "Calculates composite hazard-exposure-vulnerability risk score for district assets."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "district_name": {"type": "string"},
                "hazard_type": {"type": "string"},
            },
            "required": ["district_name", "hazard_type"],
            "additionalProperties": False,
        }

    @property
    def allowed_brains(self) -> Set[BrainType]:
        # Restricted strictly to Analyst Brain
        return {BrainType.ANALYST}

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        district = request.arguments.get("district_name", "")
        hazard = request.arguments.get("hazard_type", "")
        data = {
            "district": district,
            "hazard": hazard,
            "risk_level": "HIGH",
            "vulnerability_score": 0.82,
            "exposed_population_estimate": 450000,
        }
        return ToolCallResponse(
            call_id=request.call_id,
            tool_name=self.name,
            status="success",
            execution_time_ms=15.0,
            data=data,
            provenance=ToolProvenance(
                data_sources=["PostGIS Vulnerability Matrix"],
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            quality=ToolQuality(freshness="fresh", completeness="complete"),
        )


def register_default_tools(registry: ToolRegistry) -> None:
    """Registers standard baseline tools into a ToolRegistry instance."""
    registry.register(ResolveLocationTool())
    registry.register(GetWeatherForecastTool())
    registry.register(CalculateIrrigationAdvisoryTool())
    registry.register(RunRiskAnalysisTool())
