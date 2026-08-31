package com.weathergpt.domain.model.gis

import kotlinx.serialization.json.JsonObject

data class BoundaryUnit(
    val code: String,
    val name: String,
    val level: String,
    val parentCode: String?,
    val areaSqkm: Double?
)

data class LocationHierarchy(
    val latitude: Double,
    val longitude: Double,
    val isResolved: Boolean,
    val country: BoundaryUnit?,
    val state: BoundaryUnit?,
    val district: BoundaryUnit?,
    val subdistrict: BoundaryUnit?
)

data class AdministrativeBoundary(
    val code: String,
    val name: String,
    val level: String,
    val parentCode: String?,
    val areaSqkm: Double?,
    val rawGeoJson: JsonObject?
)

data class AffectedBoundary(
    val boundary: BoundaryUnit?,
    val exposedAreaSqkm: Double,
    val exposedAreaPct: Double
)

data class HazardIntersection(
    val alertId: String,
    val event: String,
    val severity: String,
    val totalAffectedBoundaries: Int,
    val totalAffectedAreaSqkm: Double?,
    val affectedUnits: List<AffectedBoundary>
)

data class OperationalRisk(
    val district: String,
    val hazardType: String,
    val hazardIndex: Double,
    val exposureIndex: Double,
    val vulnerabilityIndex: Double,
    val compositeRiskScore: Double,
    val riskLevel: String,
    val actionPriority: String
)

data class GISAnalysisReport(
    val analysisId: String?,
    val latitude: Double,
    val longitude: Double,
    val hazardScore: Double,
    val exposureScore: Double,
    val vulnerabilityScore: Double,
    val impactScore: Double,
    val riskCategory: String,
    val actionableGuidance: List<String>
)
