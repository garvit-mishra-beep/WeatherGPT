"""Weather × GIS Integration Service.

Jointly overlays operational weather observations, GFS/ECMWF NWP fields,
IMD/CAP severe weather warnings, and PostGIS administrative boundaries.

Adheres strictly to docs/09_GIS_SPEC.md, docs/08_NWP_SPEC.md, and docs/07_WEATHER_DATA_SPEC.md.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union

from app.adapters.models import NormalizedOfficialAlert, NormalizedWeatherObservation
from app.adapters.strategy import WeatherProviderManager
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.engine import SpatialEngine
from app.gis.spatial.types import BoundaryMatch, PointContainmentResult
from app.nwp.engine import NWPEngine
from app.nwp.types import (
    AggregationMethod,
    InterpolationMethod,
    ModelDivergenceResult,
    NWPModelType,
    NWPPointResult,
    NWPPolygonResult,
)
from app.services.errors import (
    WeatherGISDataUnavailableError,
    WeatherGISError,
    WeatherGISLocationError,
)
from app.services.types import (
    DataQualityStatus,
    GeographicGranularity,
    SpatialDistrictWeatherResult,
    SpatialWeatherPointResult,
    WarningIntersectionResult,
)

logger = logging.getLogger(__name__)


class WeatherGISService:
    """Deterministic service for combined Spatial Weather, NWP, and Hazard Intelligence."""

    def __init__(
        self,
        spatial_engine: SpatialEngine,
        nwp_engine: Optional[NWPEngine] = None,
        weather_manager: Optional[WeatherProviderManager] = None,
    ) -> None:
        self.spatial_engine = spatial_engine
        self.nwp_engine = nwp_engine or NWPEngine()
        self.weather_manager = weather_manager or WeatherProviderManager()

    async def get_point_weather_intelligence(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
        variable: str = "TMP:2m",
        include_nwp: bool = True,
        include_warnings: bool = True,
        include_divergence: bool = True,
    ) -> SpatialWeatherPointResult:
        """Assembles unified spatial weather intelligence for a geographic coordinate.

        Combines:
        1. Administrative Boundary Resolution (Country -> State -> District -> SubDistrict)
        2. Surface Weather Observations (Temperature, Rain, Wind, Humidity, Pressure)
        3. 2D Bilinear NWP Grid Point Extraction (GFS 0.25°)
        4. Multi-Model Spread & Relative Divergence Ratio (GFS vs. ECMWF)
        5. Authoritative IMD / CAP Warnings (with immutable severity)
        """
        # 1. Resolve administrative location via PostGIS Spatial Engine
        admin_area: Optional[PointContainmentResult] = None
        try:
            admin_area = await self.spatial_engine.resolve_point(latitude, longitude)
        except Exception as exc:
            logger.warning("SpatialEngine resolution failed for (%.4f, %.4f): %s", latitude, longitude, exc)

        # 2. Surface Weather Observation
        obs: Optional[NormalizedWeatherObservation] = None
        try:
            obs = await self.weather_manager.get_current_weather(latitude, longitude)
        except Exception as exc:
            logger.warning("WeatherProviderManager observation failed for (%.4f, %.4f): %s", latitude, longitude, exc)

        # 3. NWP Grid Point Extraction
        nwp_point: Optional[NWPPointResult] = None
        if include_nwp:
            try:
                nwp_point = self.nwp_engine.extract_point(
                    latitude=latitude,
                    longitude=longitude,
                    variable=variable,
                    model=NWPModelType.GFS_0P25,
                    lead_hours=lead_hours,
                    method=InterpolationMethod.BILINEAR,
                )
            except Exception as exc:
                logger.warning("NWPEngine point extraction failed for (%.4f, %.4f): %s", latitude, longitude, exc)

        # 4. Multi-Model Divergence (GFS vs ECMWF)
        divergence_res: Optional[ModelDivergenceResult] = None
        if include_divergence:
            try:
                divergence_res = self.nwp_engine.analyze_divergence(
                    latitude=latitude,
                    longitude=longitude,
                    variable="APCP:surface",
                    lead_hours=lead_hours,
                )
            except Exception as exc:
                logger.warning("NWPEngine divergence calculation failed for (%.4f, %.4f): %s", latitude, longitude, exc)

        # 5. Active IMD / CAP Alerts
        active_alerts: List[NormalizedOfficialAlert] = []
        if include_warnings:
            try:
                active_alerts = await self.weather_manager.get_active_alerts(latitude, longitude)
            except Exception as exc:
                logger.warning("WeatherProviderManager alerts query failed: %s", exc)

        # Evaluate composite data status
        has_obs = obs is not None
        has_nwp = nwp_point is not None
        has_admin = admin_area is not None and admin_area.is_resolved

        if has_obs and has_nwp and has_admin:
            status = DataQualityStatus.AVAILABLE
        elif has_obs or has_nwp or has_admin:
            status = DataQualityStatus.PARTIAL
        else:
            status = DataQualityStatus.UNAVAILABLE

        provenance: Dict[str, Any] = {
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "spatial": "PostGIS Administrative Boundaries (Survey of India / Census)",
                "surface_weather": obs.provider if obs else "unavailable",
                "nwp_model": nwp_point.provenance.model_name if nwp_point else "unavailable",
                "warnings": "IMD OASIS CAP Alert Feed",
            },
        }

        return SpatialWeatherPointResult(
            latitude=latitude,
            longitude=longitude,
            granularity=GeographicGranularity.POINT,
            status=status,
            administrative_area=admin_area,
            surface_observation=obs,
            nwp_point=nwp_point,
            model_divergence=divergence_res,
            active_warnings=active_alerts,
            provenance=provenance,
        )

    async def get_district_weather_intelligence(
        self,
        district_code: str,
        lead_hours: int = 24,
        variable: str = "APCP:surface",
        aggregation_method: AggregationMethod = AggregationMethod.MEAN,
    ) -> SpatialDistrictWeatherResult:
        """Assembles district-level aggregated weather intelligence with zonal NWP extraction."""
        district = await self.spatial_engine.lookup_boundary(district_code, level=AdminLevel.DISTRICT)
        if not district:
            raise WeatherGISLocationError(f"District code '{district_code}' not found in administrative database")

        c_lat = district.centroid_lat or 21.17
        c_lon = district.centroid_lon or 72.83

        # 1. Surface weather for centroid
        obs: Optional[NormalizedWeatherObservation] = None
        try:
            obs = await self.weather_manager.get_current_weather(c_lat, c_lon)
        except Exception as exc:
            logger.warning("Surface weather query failed for district %s centroid: %s", district_code, exc)

        # 2. Zonal NWP aggregation over district bounding geometry
        nwp_zonal: Optional[NWPPolygonResult] = None
        try:
            # Synthetic polygon approximation from centroid if raw DB geometry is not returned
            box_poly = {
                "type": "Polygon",
                "coordinates": [
                    [
                        [c_lon - 0.25, c_lat - 0.25],
                        [c_lon + 0.25, c_lat - 0.25],
                        [c_lon + 0.25, c_lat + 0.25],
                        [c_lon - 0.25, c_lat + 0.25],
                        [c_lon - 0.25, c_lat - 0.25],
                    ]
                ],
            }
            nwp_zonal = self.nwp_engine.extract_polygon(
                geometry=box_poly,
                variable=variable,
                model=NWPModelType.GFS_0P25,
                lead_hours=lead_hours,
                aggregation_method=aggregation_method,
                geometry_id=district.code,
            )
        except Exception as exc:
            logger.warning("NWP zonal aggregation failed for district %s: %s", district_code, exc)

        # 3. Active warnings for centroid
        active_alerts: List[NormalizedOfficialAlert] = []
        try:
            active_alerts = await self.weather_manager.get_active_alerts(c_lat, c_lon)
        except Exception as exc:
            logger.warning("Alerts query failed for district %s: %s", district_code, exc)

        status = DataQualityStatus.AVAILABLE if (obs is not None and nwp_zonal is not None) else DataQualityStatus.PARTIAL

        return SpatialDistrictWeatherResult(
            district_code=district.code,
            district_name=district.name,
            state_code=district.parent_code,
            granularity=GeographicGranularity.DISTRICT,
            status=status,
            centroid_lat=c_lat,
            centroid_lon=c_lon,
            surface_weather=obs,
            nwp_zonal_aggregation=nwp_zonal,
            active_warnings=active_alerts,
            provenance={
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                "district": district.name,
                "nwp_aggregation": aggregation_method.value,
            },
        )

    async def intersect_warning_polygon(
        self,
        warning_geometry: Dict[str, Any],
        alert_id: str,
        issuer: str = "India Meteorological Department",
        event: str = "Severe Weather Warning",
        severity: str = "Orange",
        effective_utc: Optional[str] = None,
        expires_utc: Optional[str] = None,
        target_level: AdminLevel = AdminLevel.DISTRICT,
    ) -> WarningIntersectionResult:
        """Overlays an active IMD / CAP severe weather warning polygon with PostGIS administrative boundaries.

        Calculates affected units, exposed area in km², percentage overlap, and preserves
        immutable official severity levels.
        """
        inter_res = await self.spatial_engine.find_intersections(
            geometry=warning_geometry,
            target_level=target_level,
            include_geojson=True,
        )

        return WarningIntersectionResult(
            alert_id=alert_id,
            issuer=issuer,
            event=event,
            severity=severity,
            effective_utc=effective_utc,
            expires_utc=expires_utc,
            target_level=target_level,
            total_affected_boundaries=inter_res.total_intersections,
            affected_units=inter_res.matches,
            provenance={
                "spatial_engine": "PostGIS ST_Intersects & ST_Intersection (EPSG:4326)",
                "calculation": "Geodesic Area (km² & % Overlap)",
                "official_authority": "IMD / NDMA Sachet CAP",
            },
        )
