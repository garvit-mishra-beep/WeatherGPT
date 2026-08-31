package com.weathergpt.domain.repository

import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.model.ReadinessStatus
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.model.gis.AdministrativeBoundary
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.HazardIntersection
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import kotlinx.serialization.json.JsonObject

/**
 * Domain repository abstraction exposing all verified WeatherGPT backend operations.
 */
interface WeatherGPTRepository {

    // ========================================================================
    // 1. System
    // ========================================================================
    suspend fun checkHealth(): ResultState<HealthStatus>
    suspend fun checkReadiness(): ResultState<ReadinessStatus>

    // ========================================================================
    // 2. Chat & LLM Orchestration
    // ========================================================================
    suspend fun sendChat(query: ChatQuery): ResultState<ChatResponse>

    // ========================================================================
    // 3. Weather & Official Alerts
    // ========================================================================
    suspend fun getCurrentWeather(latitude: Double, longitude: Double): ResultState<CurrentWeather>

    suspend fun getWeatherForecast(
        latitude: Double,
        longitude: Double,
        days: Int = 3,
        hourly: Boolean = true
    ): ResultState<WeatherForecast>

    suspend fun getWeatherAlerts(
        district: String? = null,
        latitude: Double? = null,
        longitude: Double? = null
    ): ResultState<WeatherAlertsReport>

    suspend fun getWeatherIntelligence(
        latitude: Double,
        longitude: Double,
        leadHours: Int = 24,
        includeNwp: Boolean = true
    ): ResultState<WeatherIntelligence>

    // ========================================================================
    // 4. Agricultural & Farmer
    // ========================================================================
    suspend fun getIrrigationAdvisory(
        latitude: Double,
        longitude: Double,
        cropName: String,
        cropStage: String = "mid_season",
        soilType: String = "alluvial_loam",
        lastIrrigationDate: String? = null,
        forecastPrecip48hMm: Double = 0.0
    ): ResultState<IrrigationAdvisory>

    suspend fun getSprayWindowAdvisory(
        windSpeedKmh: Double,
        rainProbabilityPct: Double,
        tempC: Double = 28.0,
        relativeHumidityPct: Double = 60.0
    ): ResultState<SpraySuitability>

    // ========================================================================
    // 5. GIS & Spatial Operations
    // ========================================================================
    suspend fun getLocationHierarchy(latitude: Double, longitude: Double): ResultState<LocationHierarchy>

    suspend fun getBoundary(level: String, code: String): ResultState<AdministrativeBoundary>

    suspend fun getHazardIntersection(
        warningGeometry: JsonObject?,
        alertId: String = "WARN-CAP-001",
        event: String = "Severe Weather Alert",
        severity: String = "Orange",
        targetLevel: String = "district"
    ): ResultState<HazardIntersection>

    suspend fun getRiskAssessment(
        districtName: String,
        precip24hPercentile: Double = 90.0,
        exposureIndex: Double = 8.0,
        vulnerabilityIndex: Double = 7.5,
        hazardType: String = "heavy_rainfall"
    ): ResultState<OperationalRisk>

    suspend fun getGISAnalysis(
        latitude: Double?,
        longitude: Double?,
        districtCode: String? = null,
        observedRainMm: Double? = null,
        observedWindKmh: Double? = null,
        observedTempC: Double? = null,
        leadHours: Int = 24
    ): ResultState<GISAnalysisReport>

    // ========================================================================
    // 6. NWP Numerical Weather Prediction
    // ========================================================================
    suspend fun getGFSGridPoint(
        latitude: Double,
        longitude: Double,
        leadHours: Int = 24
    ): ResultState<NWPGridPoint>

    suspend fun getWRFGridPoint(
        latitude: Double,
        longitude: Double,
        leadHours: Int = 24
    ): ResultState<NWPGridPoint>

    suspend fun getNWPModelComparison(
        latitude: Double,
        longitude: Double,
        leadHours: Int = 24
    ): ResultState<NWPModelComparison>

    // ========================================================================
    // 7. Map-Ready Data
    // ========================================================================
    suspend fun getPointWeatherMap(latitude: Double, longitude: Double): ResultState<MapSpecification>

    suspend fun getWarningMap(
        warningGeometry: JsonObject,
        alertId: String = "WARN-CAP-001",
        event: String = "Severe Weather Alert",
        severity: String = "Orange"
    ): ResultState<MapSpecification>

    suspend fun getRiskMap(
        latitude: Double?,
        longitude: Double?,
        districtCode: String? = null,
        observedRainMm: Double? = null,
        observedWindKmh: Double? = null
    ): ResultState<MapSpecification>
}
