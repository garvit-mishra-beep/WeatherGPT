package com.weathergpt.domain.model.weather

import kotlinx.serialization.json.JsonObject

data class LocationCoordinates(
    val latitude: Double,
    val longitude: Double
)

data class CurrentWeather(
    val location: LocationCoordinates,
    val observationTime: String,
    val temperatureC: Double,
    val feelsLikeC: Double,
    val relativeHumidityPct: Double,
    val precipitationMm: Double,
    val rainIntensityCategory: String,
    val windSpeedKmh: Double,
    val windDirectionDeg: Double,
    val surfacePressureHpa: Double,
    val weatherCondition: String,
    val provider: String?,
    val authority: String?
)

data class DailyForecast(
    val date: String,
    val tempMaxC: Double,
    val tempMinC: Double,
    val precipitationSumMm: Double,
    val precipitationProbabilityPct: Double,
    val windSpeedMaxKmh: Double,
    val dominantCondition: String
)

data class HourlyForecast(
    val time: String,
    val temperatureC: Double,
    val relativeHumidityPct: Double,
    val precipitationMm: Double,
    val precipitationProbabilityPct: Double,
    val windSpeedKmh: Double,
    val condition: String
)

data class WeatherForecast(
    val location: LocationCoordinates,
    val generatedAt: String,
    val forecastStart: String,
    val forecastEnd: String,
    val dailyForecast: List<DailyForecast>,
    val hourlyForecast: List<HourlyForecast>?,
    val provider: String?
)

data class OfficialAlert(
    val alertId: String,
    val warningColor: String, // Green, Yellow, Orange, Red (Immutable)
    val hazard: String,
    val severity: String,
    val areaDescription: String,
    val headline: String,
    val description: String,
    val effectiveFrom: String,
    val expiresAt: String,
    val instructions: String?
)

data class WeatherAlertsReport(
    val authority: String,
    val retrievedAt: String,
    val activeAlertsCount: Int,
    val alerts: List<OfficialAlert>
)

data class WeatherIntelligence(
    val latitude: Double,
    val longitude: Double,
    val dataQuality: String?,
    val currentObservation: CurrentWeather?,
    val alerts: List<OfficialAlert>,
    val rawProvenance: JsonObject?
)
