package com.weathergpt.domain.usecase

import com.weathergpt.core.result.ResultState
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
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.serialization.json.JsonObject

class SendChatMessageUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(query: ChatQuery): ResultState<ChatResponse> =
        repository.sendChat(query)
}

class GetCurrentWeatherUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(latitude: Double, longitude: Double): ResultState<CurrentWeather> =
        repository.getCurrentWeather(latitude, longitude)
}

class GetWeatherForecastUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        latitude: Double,
        longitude: Double,
        days: Int = 3,
        hourly: Boolean = true
    ): ResultState<WeatherForecast> =
        repository.getWeatherForecast(latitude, longitude, days, hourly)
}

class GetWeatherAlertsUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        district: String? = null,
        latitude: Double? = null,
        longitude: Double? = null
    ): ResultState<WeatherAlertsReport> =
        repository.getWeatherAlerts(district, latitude, longitude)
}

class GetIrrigationAdvisoryUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        latitude: Double,
        longitude: Double,
        cropName: String,
        cropStage: String = "mid_season",
        soilType: String = "alluvial_loam",
        lastIrrigationDate: String? = null,
        forecastPrecip48hMm: Double = 0.0
    ): ResultState<IrrigationAdvisory> =
        repository.getIrrigationAdvisory(latitude, longitude, cropName, cropStage, soilType, lastIrrigationDate, forecastPrecip48hMm)
}

class GetSprayWindowUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        windSpeedKmh: Double,
        rainProbabilityPct: Double,
        tempC: Double = 28.0,
        relativeHumidityPct: Double = 60.0
    ): ResultState<SpraySuitability> =
        repository.getSprayWindowAdvisory(windSpeedKmh, rainProbabilityPct, tempC, relativeHumidityPct)
}

class GetLocationHierarchyUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(latitude: Double, longitude: Double): ResultState<LocationHierarchy> =
        repository.getLocationHierarchy(latitude, longitude)
}

class GetBoundaryUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(level: String, code: String): ResultState<AdministrativeBoundary> =
        repository.getBoundary(level, code)
}

class GetHazardIntersectionUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        warningGeometry: JsonObject?,
        alertId: String,
        event: String,
        severity: String,
        targetLevel: String = "district"
    ): ResultState<HazardIntersection> =
        repository.getHazardIntersection(warningGeometry, alertId, event, severity, targetLevel)
}

class GetRiskAssessmentUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        districtName: String,
        precip24hPercentile: Double,
        exposureIndex: Double,
        vulnerabilityIndex: Double,
        hazardType: String = "rain_wind"
    ): ResultState<OperationalRisk> =
        repository.getRiskAssessment(districtName, precip24hPercentile, exposureIndex, vulnerabilityIndex, hazardType)
}

class GetGISAnalysisUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        latitude: Double?,
        longitude: Double?,
        districtCode: String? = null,
        observedRainMm: Double? = null,
        observedWindKmh: Double? = null,
        observedTempC: Double? = null,
        leadHours: Int = 24
    ): ResultState<GISAnalysisReport> =
        repository.getGISAnalysis(latitude, longitude, districtCode, observedRainMm, observedWindKmh, observedTempC, leadHours)
}

class GetGFSGridPointUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        latitude: Double,
        longitude: Double,
        leadHours: Int = 24
    ): ResultState<NWPGridPoint> =
        repository.getGFSGridPoint(latitude, longitude, leadHours)
}

class GetPointWeatherMapUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(latitude: Double, longitude: Double): ResultState<MapSpecification> =
        repository.getPointWeatherMap(latitude, longitude)
}

class GetWarningMapUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        warningGeometry: JsonObject,
        alertId: String = "WARN-CAP-001",
        event: String = "Severe Weather Alert",
        severity: String = "Orange"
    ): ResultState<MapSpecification> =
        repository.getWarningMap(warningGeometry, alertId, event, severity)
}

class GetRiskMapUseCase(private val repository: WeatherGPTRepository) {
    suspend operator fun invoke(
        latitude: Double? = null,
        longitude: Double? = null,
        districtCode: String? = null,
        observedRainMm: Double? = null,
        observedWindKmh: Double? = null
    ): ResultState<MapSpecification> =
        repository.getRiskMap(latitude, longitude, districtCode, observedRainMm, observedWindKmh)
}
