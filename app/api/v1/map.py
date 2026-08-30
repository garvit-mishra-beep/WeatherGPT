"""Map-Ready Data API Router (/api/v1/map).

Provides declarative Map Specifications and standard GeoJSON layers
for MapLibre GL and Leaflet rendering on web and mobile clients.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies.providers import (
    get_gis_analysis_engine,
    get_weather_gis_service,
    get_weather_manager,
)
from app.gis.analysis.engine import GISAnalysisEngine
from app.gis.map.builder import MapDataBuilder
from app.services.types import SpatialWeatherPointResult, WarningIntersectionResult
from app.services.weather_gis import WeatherGISService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/map", tags=["Map-Ready Data & Visualizations"])


# ============================================================================
# Request Models
# ============================================================================

class WarningMapRequest(BaseModel):
    warning_geometry: Dict[str, Any] = Field(..., description="GeoJSON Polygon/MultiPolygon of hazard zone")
    alert_id: str = Field(default="WARN-CAP-001", description="Official alert identifier")
    event: str = Field(default="Severe Weather Alert", description="Event name")
    severity: str = Field(default="Orange", description="Official severity: Green, Yellow, Orange, Red")


class RiskMapRequest(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=6.0, le=38.0)
    longitude: Optional[float] = Field(default=None, ge=68.0, le=98.0)
    district_code: Optional[str] = Field(default=None)
    observed_rain_mm: Optional[float] = Field(default=None, ge=0.0)
    observed_wind_kmh: Optional[float] = Field(default=None, ge=0.0)


# ============================================================================
# Route Handlers
# ============================================================================

@router.get("/point")
async def get_point_weather_map(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (68.0 to 98.0)"),
    weather_gis_service: Optional[WeatherGISService] = Depends(get_weather_gis_service),
) -> Dict[str, Any]:
    """Generates a declarative Map Specification for a weather observation point."""
    if weather_gis_service is not None:
        pt_intel = await weather_gis_service.get_point_weather_intelligence(latitude=lat, longitude=lon)
    else:
        pt_intel = SpatialWeatherPointResult(latitude=lat, longitude=lon)

    map_spec = MapDataBuilder.build_point_map(point_data=pt_intel)
    return map_spec.model_dump()


@router.post("/warning")
async def get_warning_hazard_map(
    request: WarningMapRequest,
    weather_gis_service: Optional[WeatherGISService] = Depends(get_weather_gis_service),
) -> Dict[str, Any]:
    """Generates a declarative Map Specification for an authoritative severe weather warning polygon."""
    warn_res = None
    if weather_gis_service is not None:
        try:
            warn_res = await weather_gis_service.intersect_warning_polygon(
                warning_geometry=request.warning_geometry,
                alert_id=request.alert_id,
                event=request.event,
                severity=request.severity,
            )
        except Exception as exc:
            logger.warning("Map warning intersection query failed: %s", exc)

    if warn_res is None:
        warn_res = WarningIntersectionResult(
            alert_id=request.alert_id,
            issuer="IMD",
            event=request.event,
            severity=request.severity,
            total_affected_boundaries=0,
            affected_units=[],
        )

    map_spec = MapDataBuilder.build_warning_hazard_map(
        warning_result=warn_res,
        warning_geometry=request.warning_geometry,
    )
    return map_spec.model_dump()


@router.post("/risk")
async def get_analytical_risk_map(
    request: RiskMapRequest,
    gis_analysis_engine: Optional[GISAnalysisEngine] = Depends(get_gis_analysis_engine),
) -> Dict[str, Any]:
    """Generates a declarative Map Specification for operational H x E x V risk analysis."""
    engine = gis_analysis_engine or GISAnalysisEngine()

    lat = request.latitude or 21.1702
    lon = request.longitude or 72.8311

    anl_res = await engine.analyze_point(
        latitude=lat,
        longitude=lon,
        observed_rain_mm=request.observed_rain_mm,
        observed_wind_kmh=request.observed_wind_kmh,
    )

    map_spec = MapDataBuilder.build_analytical_risk_map(analysis_result=anl_res)
    return map_spec.model_dump()
