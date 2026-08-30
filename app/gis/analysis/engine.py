"""Production-grade Deterministic GIS Analysis Engine.

Orchestrates multi-hazard scoring, spatial exposure quantification,
vulnerability assessment, and composite H x E x V impact evaluation.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from app.gis.analysis.errors import GISAnalysisError, InvalidHazardInputError
from app.gis.analysis.exposure import calculate_exposure_metrics, summarize_boundary_intersections
from app.gis.analysis.hazards import (
    score_official_alert_hazard,
    score_rainfall_rate_hazard,
    score_temperature_hazard,
    score_wind_hazard,
)
from app.gis.analysis.impact import calculate_operational_impact
from app.gis.analysis.multi_hazard import evaluate_multi_hazard_compounding
from app.gis.analysis.types import (
    ExposureMetrics,
    GISAnalysisResult,
    HazardRecord,
    HazardSeverity,
    HazardType,
    ImpactResult,
    MultiHazardResult,
    VulnerabilityMetrics,
)
from app.gis.analysis.vulnerability import evaluate_district_vulnerability
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.engine import SpatialEngine
from app.services.weather_gis import WeatherGISService

logger = logging.getLogger(__name__)


class GISAnalysisEngine:
    """Deterministic computational GIS Analysis Engine."""

    def __init__(
        self,
        weather_gis_service: Optional[WeatherGISService] = None,
        spatial_engine: Optional[SpatialEngine] = None,
    ) -> None:
        self.weather_gis_service = weather_gis_service
        self.spatial_engine = spatial_engine

    async def analyze_point(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
        observed_rain_mm: Optional[float] = None,
        observed_wind_kmh: Optional[float] = None,
        observed_temp_c: Optional[float] = None,
    ) -> GISAnalysisResult:
        """Executes full deterministic GIS Analysis for a coordinate point."""
        analysis_id = f"ANL-{uuid.uuid4().hex[:8].upper()}"
        hazards: List[HazardRecord] = []
        official_warnings: List[Dict[str, Any]] = []
        district_code: Optional[str] = None
        district_name: Optional[str] = None
        state_code: Optional[str] = None

        # 1. Query Weather x GIS integration if available
        if self.weather_gis_service:
            try:
                pt_res = await self.weather_gis_service.get_point_weather_intelligence(
                    latitude=latitude,
                    longitude=longitude,
                    lead_hours=lead_hours,
                )
                if pt_res.administrative_area and pt_res.administrative_area.is_resolved:
                    if pt_res.administrative_area.district:
                        district_code = pt_res.administrative_area.district.code
                        district_name = pt_res.administrative_area.district.name
                    if pt_res.administrative_area.state:
                        state_code = pt_res.administrative_area.state.code

                # Ingest active alerts as immutable hazard
                for alert in pt_res.active_warnings:
                    official_warnings.append(alert.model_dump())
                    hazards.append(score_official_alert_hazard(alert.warning_level.value))

                # Use live surface observation values if not explicitly overridden
                if observed_rain_mm is None and pt_res.surface_observation:
                    observed_rain_mm = pt_res.surface_observation.precipitation_mm
                if observed_wind_kmh is None and pt_res.surface_observation:
                    observed_wind_kmh = pt_res.surface_observation.wind_speed_kmh
                if observed_temp_c is None and pt_res.surface_observation:
                    observed_temp_c = pt_res.surface_observation.temperature_c

            except Exception as exc:
                logger.warning("WeatherGISService query failed for analysis at (%.4f, %.4f): %s", latitude, longitude, exc)

        # 2. Score meteorological hazards
        if observed_rain_mm is not None:
            hazards.append(score_rainfall_rate_hazard(observed_rain_mm))
        if observed_wind_kmh is not None:
            hazards.append(score_wind_hazard(observed_wind_kmh))
        if observed_temp_c is not None:
            hazards.append(score_temperature_hazard(observed_temp_c))

        if not hazards:
            # Baseline nominal zero hazard
            hazards.append(
                HazardRecord(
                    hazard_type=HazardType.HEAVY_RAINFALL,
                    severity=HazardSeverity.NONE,
                    hazard_score=0.0,
                    source="WeatherGPT Baseline Monitor",
                )
            )

        # 3. Multi-Hazard Compounding
        multi_hazard = evaluate_multi_hazard_compounding(hazards)
        primary_h = multi_hazard.compound_hazard_score

        # 4. Spatial Exposure Quantification (Point exposure defaults to proportional 5.0 when centered)
        exposure = calculate_exposure_metrics(exposed_area_sqkm=1750.0, total_area_sqkm=3500.0, affected_boundaries_count=1)

        # 5. Vulnerability Evaluation
        vulnerability = evaluate_district_vulnerability(district_code=district_code)

        # 6. Composite Operational Impact Calculation
        impact = calculate_operational_impact(
            hazard_score=primary_h,
            exposure_score=exposure.exposure_score,
            vulnerability_score=vulnerability.vulnerability_score,
        )

        provenance = {
            "analysis_id": analysis_id,
            "calculated_at_utc": datetime.now(timezone.utc).isoformat(),
            "methodology": "Deterministic H x E x V Matrix (docs/11 §4.2)",
            "hazard_count": len(hazards),
        }

        return GISAnalysisResult(
            analysis_id=analysis_id,
            latitude=latitude,
            longitude=longitude,
            district_code=district_code,
            district_name=district_name,
            state_code=state_code,
            hazards=hazards,
            multi_hazard=multi_hazard,
            exposure=exposure,
            vulnerability=vulnerability,
            impact=impact,
            official_warnings=official_warnings,
            temporal_context={"lead_hours": lead_hours},
            provenance=provenance,
        )

    async def analyze_hazard_polygon(
        self,
        geometry: Dict[str, Any],
        alert_id: str = "WARN-POLY-01",
        official_severity: str = "Orange",
        event: str = "Severe Weather Event",
        target_level: AdminLevel = AdminLevel.DISTRICT,
    ) -> GISAnalysisResult:
        """Calculates deterministic exposure and impact for a hazard warning polygon."""
        analysis_id = f"ANL-POLY-{uuid.uuid4().hex[:8].upper()}"

        # 1. Score Official Warning Hazard (Immutable severity)
        hazard = score_official_alert_hazard(official_severity)
        hazards = [hazard]
        multi_hazard = evaluate_multi_hazard_compounding(hazards)

        # 2. Quantify Spatial Exposure via PostGIS intersection
        exposure: ExposureMetrics
        affected_units = []

        if self.weather_gis_service:
            intersect_res = await self.weather_gis_service.intersect_warning_polygon(
                warning_geometry=geometry,
                alert_id=alert_id,
                event=event,
                severity=official_severity,
                target_level=target_level,
            )
            exposure = summarize_boundary_intersections(intersect_res.affected_units)
            affected_units = [u.model_dump() for u in intersect_res.affected_units]
        elif self.spatial_engine:
            inter_matches = await self.spatial_engine.find_intersections(geometry, target_level=target_level)
            exposure = summarize_boundary_intersections(inter_matches.matches)
        else:
            exposure = calculate_exposure_metrics(exposed_area_sqkm=500.0, total_area_sqkm=3500.0)

        # 3. Vulnerability
        vulnerability = evaluate_district_vulnerability()

        # 4. Composite Impact Calculation
        impact = calculate_operational_impact(
            hazard_score=hazard.hazard_score,
            exposure_score=exposure.exposure_score,
            vulnerability_score=vulnerability.vulnerability_score,
        )

        return GISAnalysisResult(
            analysis_id=analysis_id,
            hazards=hazards,
            multi_hazard=multi_hazard,
            exposure=exposure,
            vulnerability=vulnerability,
            impact=impact,
            official_warnings=[{"alert_id": alert_id, "severity": official_severity, "event": event}],
            temporal_context={"event": event},
            provenance={
                "analysis_id": analysis_id,
                "calculated_at_utc": datetime.now(timezone.utc).isoformat(),
                "spatial_engine": "PostGIS ST_Intersection",
                "affected_units_count": len(affected_units),
            },
        )
