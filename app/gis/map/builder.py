"""Production-grade MapDataBuilder Engine.

Constructs frontend-independent, MapLibre GL and Leaflet compatible
declarative Map Specifications and standard GeoJSON FeatureCollections.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.gis.analysis.types import GISAnalysisResult
from app.gis.map.geojson import (
    create_feature_collection,
    create_point_feature,
    create_polygon_feature,
)
from app.gis.map.legend import build_risk_legend, build_warning_legend, build_weather_legend
from app.gis.map.styling import (
    get_administrative_boundary_paint,
    get_analytical_risk_paint,
    get_official_warning_paint,
    get_weather_point_paint,
)
from app.gis.map.types import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    MapLayerSpec,
    MapLayerType,
    MapSpecification,
    MapViewport,
)
from app.gis.map.viewport import calculate_viewport
from app.services.types import SpatialDistrictWeatherResult, SpatialWeatherPointResult, WarningIntersectionResult


class MapDataBuilder:
    """Deterministic builder converting domain GIS/weather outputs into Map Specifications."""

    @staticmethod
    def build_point_map(
        point_data: SpatialWeatherPointResult,
        analysis_result: Optional[GISAnalysisResult] = None,
        title: Optional[str] = None,
    ) -> MapSpecification:
        """Constructs a declarative map specification for a weather observation point."""
        map_id = f"map_pt_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{point_data.latitude}:{point_data.longitude}').hex[:8]}"
        
        # 1. Point Feature
        props: Dict[str, Any] = {
            "latitude": point_data.latitude,
            "longitude": point_data.longitude,
        }
        if point_data.administrative_area and point_data.administrative_area.is_resolved:
            if point_data.administrative_area.district:
                props["district"] = point_data.administrative_area.district.name
            if point_data.administrative_area.state:
                props["state"] = point_data.administrative_area.state.name

        if point_data.surface_observation:
            props["temperature_c"] = point_data.surface_observation.temperature_c
            props["precipitation_mm"] = point_data.surface_observation.precipitation_mm
            props["wind_speed_kmh"] = point_data.surface_observation.wind_speed_kmh

        pt_feat = create_point_feature(
            latitude=point_data.latitude,
            longitude=point_data.longitude,
            properties=props,
            feature_id=f"feat_{map_id}",
        )
        fc = create_feature_collection([pt_feat])

        # 2. Layer Specification
        layer = MapLayerSpec(
            id="surface_weather_point",
            name="Surface Weather Point",
            type=MapLayerType.CIRCLE,
            source_id="point_source",
            source_data=fc,
            paint=get_weather_point_paint("temperature"),
        )

        # 3. Viewport & Legend
        viewport = calculate_viewport(fc)
        legend = build_weather_legend("temperature")

        # 4. Optional Analytical Risk Overlay
        layers = [layer]
        if analysis_result:
            legend.extend(build_risk_legend())

        return MapSpecification(
            id=map_id,
            title=title or f"Weather Map — {props.get('district', 'Point Location')}",
            viewport=viewport,
            layers=layers,
            legend=legend,
            provenance=point_data.provenance,
            quality=point_data.data_quality.value if hasattr(point_data, "data_quality") else "AVAILABLE",
        )

    @staticmethod
    def build_warning_hazard_map(
        warning_result: WarningIntersectionResult,
        warning_geometry: Dict[str, Any],
        title: Optional[str] = None,
    ) -> MapSpecification:
        """Constructs a declarative map specification for an authoritative severe weather warning."""
        map_id = f"map_warn_{warning_result.alert_id.replace('-', '_').lower()}"

        # 1. Warning Hazard Polygon Feature (IMMUTABLE SEVERITY)
        warn_props = {
            "alert_id": warning_result.alert_id,
            "event": warning_result.event,
            "official_severity": warning_result.severity,  # IMMUTABLE
            "issuer": warning_result.issuer,
            "affected_districts_count": warning_result.total_affected_boundaries,
        }
        warn_feat = GeoJSONFeature(
            id=f"feat_{warning_result.alert_id}",
            geometry=warning_geometry,
            properties=warn_props,
        )
        warn_fc = create_feature_collection([warn_feat])

        warn_layer = MapLayerSpec(
            id="warning_hazard_zone",
            name=f"IMD {warning_result.severity} Warning Zone",
            type=MapLayerType.FILL,
            source_id="warning_source",
            source_data=warn_fc,
            paint=get_official_warning_paint(warning_result.severity),
        )

        # 2. Affected District Boundaries Layer
        layers = [warn_layer]
        district_features: List[GeoJSONFeature] = []

        for unit in warning_result.affected_units:
            if unit.intersection_geojson:
                d_props = {
                    "district_code": unit.boundary.code,
                    "district_name": unit.boundary.name,
                    "exposed_area_sqkm": unit.exposed_area_sqkm,
                    "exposed_area_pct": unit.exposed_area_pct,
                }
                district_features.append(
                    GeoJSONFeature(
                        id=f"feat_exposed_{unit.boundary.code}",
                        geometry=unit.intersection_geojson,
                        properties=d_props,
                    )
                )

        if district_features:
            dist_fc = create_feature_collection(district_features)
            dist_layer = MapLayerSpec(
                id="exposed_administrative_intersections",
                name="Exposed District Intersections",
                type=MapLayerType.LINE,
                source_id="exposed_districts_source",
                source_data=dist_fc,
                paint=get_administrative_boundary_paint("district"),
            )
            layers.append(dist_layer)

        # 3. Viewport & Legend
        viewport = calculate_viewport(warn_fc)
        legend = build_warning_legend(active_severity=warning_result.severity)

        return MapSpecification(
            id=map_id,
            title=title or f"Severe Weather Warning Map — {warning_result.event} ({warning_result.severity})",
            viewport=viewport,
            layers=layers,
            legend=legend,
            provenance={
                "alert_id": warning_result.alert_id,
                "issuer": warning_result.issuer,
                "dataset": "IMD OASIS CAP Alert XML",
            },
        )

    @staticmethod
    def build_analytical_risk_map(
        analysis_result: GISAnalysisResult,
        district_geometry: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
    ) -> MapSpecification:
        """Constructs a declarative map specification for B7 GIS Analysis (H x E x V)."""
        map_id = f"map_anl_{analysis_result.analysis_id.lower()}"

        layers: List[MapLayerSpec] = []
        features: List[GeoJSONFeature] = []

        # 1. District or Point Feature
        if district_geometry:
            props = {
                "district_code": analysis_result.district_code,
                "district_name": analysis_result.district_name,
                "composite_impact_score": analysis_result.impact.composite_impact_score,
                "risk_category": analysis_result.impact.risk_category.value,
                "hazard_score": analysis_result.impact.hazard_score,
                "exposure_score": analysis_result.impact.exposure_score,
                "vulnerability_score": analysis_result.impact.vulnerability_score,
            }
            feat = GeoJSONFeature(
                id=f"feat_risk_{analysis_result.district_code or 'district'}",
                geometry=district_geometry,
                properties=props,
            )
            features.append(feat)
            fc = create_feature_collection(features)
            layers.append(
                MapLayerSpec(
                    id="analytical_risk_polygon",
                    name="Operational Risk Layer (H x E x V)",
                    type=MapLayerType.FILL,
                    source_id="risk_source",
                    source_data=fc,
                    paint=get_analytical_risk_paint(analysis_result.impact.risk_category.value),
                )
            )
            viewport = calculate_viewport(fc)
        elif analysis_result.latitude and analysis_result.longitude:
            props = {
                "composite_impact_score": analysis_result.impact.composite_impact_score,
                "risk_category": analysis_result.impact.risk_category.value,
            }
            feat = create_point_feature(
                latitude=analysis_result.latitude,
                longitude=analysis_result.longitude,
                properties=props,
                feature_id=f"feat_pt_{map_id}",
            )
            features.append(feat)
            fc = create_feature_collection(features)
            layers.append(
                MapLayerSpec(
                    id="analytical_risk_point",
                    name="Operational Risk Point",
                    type=MapLayerType.CIRCLE,
                    source_id="risk_pt_source",
                    source_data=fc,
                    paint={"circle-color": "#E53E3E" if analysis_result.impact.composite_impact_score >= 7.0 else "#ECC94B", "circle-radius": 8.0},
                )
            )
            viewport = calculate_viewport(fc)
        else:
            fc = create_feature_collection([])
            viewport = MapViewport(center=[78.9629, 20.5937], zoom=5.0)

        legend = build_risk_legend()

        return MapSpecification(
            id=map_id,
            title=title or f"Operational Risk Map — {analysis_result.district_name or 'Regional Assessment'}",
            viewport=viewport,
            layers=layers,
            legend=legend,
            provenance=analysis_result.provenance,
        )
