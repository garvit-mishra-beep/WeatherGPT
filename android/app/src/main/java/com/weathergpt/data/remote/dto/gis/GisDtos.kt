package com.weathergpt.data.remote.dto.gis

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class BoundaryUnitDto(
    @SerialName("code")
    val code: String,
    @SerialName("name")
    val name: String,
    @SerialName("level")
    val level: String,
    @SerialName("parent_code")
    val parentCode: String? = null,
    @SerialName("area_sqkm")
    val areaSqkm: Double? = null
)

@Serializable
data class LocationResolutionResponseDto(
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("is_resolved")
    val isResolved: Boolean,
    @SerialName("country")
    val country: BoundaryUnitDto? = null,
    @SerialName("state")
    val state: BoundaryUnitDto? = null,
    @SerialName("district")
    val district: BoundaryUnitDto? = null,
    @SerialName("subdistrict")
    val subdistrict: BoundaryUnitDto? = null
)

@Serializable
data class BoundaryResponseDto(
    @SerialName("id")
    val id: Int? = null,
    @SerialName("code")
    val code: String,
    @SerialName("name")
    val name: String,
    @SerialName("level")
    val level: String,
    @SerialName("parent_code")
    val parentCode: String? = null,
    @SerialName("area_sqkm")
    val areaSqkm: Double? = null,
    @SerialName("geojson")
    val geojson: JsonObject? = null
)

@Serializable
data class HazardIntersectionRequestDto(
    @SerialName("warning_geometry")
    val warningGeometry: JsonObject? = null,
    @SerialName("warning_polygon_geojson")
    val warningPolygonGeojson: JsonObject? = null,
    @SerialName("alert_id")
    val alertId: String = "WARN-CAP-001",
    @SerialName("event")
    val event: String = "Severe Weather Alert",
    @SerialName("severity")
    val severity: String = "Orange",
    @SerialName("target_level")
    val targetLevel: String = "district",
    @SerialName("exposure_layers")
    val exposureLayers: List<String> = listOf("districts")
)

@Serializable
data class AffectedBoundaryItemDto(
    @SerialName("boundary")
    val boundary: BoundaryUnitDto? = null,
    @SerialName("exposed_area_sqkm")
    val exposedAreaSqkm: Double = 0.0,
    @SerialName("exposed_area_pct")
    val exposedAreaPct: Double = 0.0
)

@Serializable
data class IntersectedDistrictItemDto(
    @SerialName("district_code")
    val districtCode: String,
    @SerialName("district_name")
    val districtName: String,
    @SerialName("state_name")
    val stateName: String? = null,
    @SerialName("exposed_area_sqkm")
    val exposedAreaSqkm: Double = 0.0,
    @SerialName("exposed_area_pct")
    val exposedAreaPct: Double = 0.0
)

@Serializable
data class HazardIntersectionResponseDto(
    @SerialName("alert_id")
    val alertId: String,
    @SerialName("event")
    val event: String,
    @SerialName("severity")
    val severity: String,
    @SerialName("total_affected_boundaries")
    val totalAffectedBoundaries: Int = 0,
    @SerialName("total_affected_area_sqkm")
    val totalAffectedAreaSqkm: Double? = null,
    @SerialName("affected_units")
    val affectedUnits: List<AffectedBoundaryItemDto> = emptyList(),
    @SerialName("intersected_districts")
    val intersectedDistricts: List<IntersectedDistrictItemDto>? = null,
    @SerialName("provenance")
    val provenance: JsonObject? = null
)

@Serializable
data class RiskAssessmentRequestDto(
    @SerialName("district_name")
    val districtName: String,
    @SerialName("precip_24h_percentile")
    val precip24hPercentile: Double = 90.0,
    @SerialName("exposure_index")
    val exposureIndex: Double = 8.0,
    @SerialName("vulnerability_index")
    val vulnerabilityIndex: Double = 7.5,
    @SerialName("hazard_type")
    val hazardType: String = "heavy_rainfall"
)

@Serializable
data class RiskAssessmentResponseDto(
    @SerialName("district")
    val district: String,
    @SerialName("hazard_type")
    val hazardType: String,
    @SerialName("hazard_index")
    val hazardIndex: Double,
    @SerialName("exposure_index")
    val exposureIndex: Double,
    @SerialName("vulnerability_index")
    val vulnerabilityIndex: Double,
    @SerialName("composite_risk_score")
    val compositeRiskScore: Double,
    @SerialName("risk_level")
    val riskLevel: String,
    @SerialName("action_priority")
    val actionPriority: String,
    @SerialName("provenance")
    val provenance: JsonObject? = null
)

@Serializable
data class GISAnalysisRequestDto(
    @SerialName("latitude")
    val latitude: Double? = null,
    @SerialName("longitude")
    val longitude: Double? = null,
    @SerialName("district_code")
    val districtCode: String? = null,
    @SerialName("observed_rain_mm")
    val observedRainMm: Double? = null,
    @SerialName("observed_wind_kmh")
    val observedWindKmh: Double? = null,
    @SerialName("observed_temp_c")
    val observedTempC: Double? = null,
    @SerialName("lead_hours")
    val leadHours: Int = 24
)

@Serializable
data class GISAnalysisResponseDto(
    @SerialName("analysis_id")
    val analysisId: String? = null,
    @SerialName("latitude")
    val latitude: Double = 0.0,
    @SerialName("longitude")
    val longitude: Double = 0.0,
    @SerialName("hazard_score")
    val hazardScore: Double = 0.0,
    @SerialName("exposure_score")
    val exposureScore: Double = 0.0,
    @SerialName("vulnerability_score")
    val vulnerabilityScore: Double = 0.0,
    @SerialName("impact_score")
    val impactScore: Double = 0.0,
    @SerialName("risk_category")
    val riskCategory: String = "LOW",
    @SerialName("actionable_guidance")
    val actionableGuidance: List<String> = emptyList(),
    @SerialName("provenance")
    val provenance: JsonObject? = null
)
