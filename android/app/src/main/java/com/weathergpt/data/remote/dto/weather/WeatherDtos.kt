package com.weathergpt.data.remote.dto.weather

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class LocationCoordDto(
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double
)

@Serializable
data class WeatherProvenanceDto(
    @SerialName("provider")
    val provider: String? = null,
    @SerialName("authority")
    val authority: String? = null,
    @SerialName("quality")
    val quality: String? = null,
    @SerialName("retrieval_timestamp")
    val retrievalTimestamp: String? = null
)

@Serializable
data class CurrentWeatherResponseDto(
    @SerialName("location")
    val location: LocationCoordDto,
    @SerialName("observation_time")
    val observationTime: String,
    @SerialName("temperature_c")
    val temperatureC: Double,
    @SerialName("feels_like_c")
    val feelsLikeC: Double,
    @SerialName("relative_humidity_pct")
    val relativeHumidityPct: Double,
    @SerialName("precipitation_mm")
    val precipitationMm: Double,
    @SerialName("rain_intensity_category")
    val rainIntensityCategory: String,
    @SerialName("wind_speed_kmh")
    val windSpeedKmh: Double,
    @SerialName("wind_direction_deg")
    val windDirectionDeg: Double,
    @SerialName("surface_pressure_hpa")
    val surfacePressureHpa: Double,
    @SerialName("weather_condition")
    val weatherCondition: String,
    @SerialName("provenance")
    val provenance: WeatherProvenanceDto? = null
)

@Serializable
data class DailyForecastDto(
    @SerialName("date")
    val date: String,
    @SerialName("temp_max_c")
    val tempMaxC: Double,
    @SerialName("temp_min_c")
    val tempMinC: Double,
    @SerialName("precipitation_sum_mm")
    val precipitationSumMm: Double,
    @SerialName("precipitation_probability_pct")
    val precipitationProbabilityPct: Double,
    @SerialName("wind_speed_max_kmh")
    val windSpeedMaxKmh: Double,
    @SerialName("dominant_condition")
    val dominantCondition: String
)

@Serializable
data class HourlyForecastDto(
    @SerialName("time")
    val time: String,
    @SerialName("temperature_c")
    val temperatureC: Double,
    @SerialName("relative_humidity_pct")
    val relativeHumidityPct: Double,
    @SerialName("precipitation_mm")
    val precipitationMm: Double,
    @SerialName("precipitation_probability_pct")
    val precipitationProbabilityPct: Double,
    @SerialName("wind_speed_kmh")
    val windSpeedKmh: Double,
    @SerialName("condition")
    val condition: String
)

@Serializable
data class WeatherForecastResponseDto(
    @SerialName("location")
    val location: LocationCoordDto,
    @SerialName("generated_at")
    val generatedAt: String,
    @SerialName("forecast_start")
    val forecastStart: String,
    @SerialName("forecast_end")
    val forecastEnd: String,
    @SerialName("daily_forecast")
    val dailyForecast: List<DailyForecastDto> = emptyList(),
    @SerialName("hourly_forecast")
    val hourlyForecast: List<HourlyForecastDto>? = null,
    @SerialName("provenance")
    val provenance: WeatherProvenanceDto? = null
)

@Serializable
data class OfficialAlertItemDto(
    @SerialName("alert_id")
    val alertId: String,
    @SerialName("warning_color")
    val warningColor: String, // "Green", "Yellow", "Orange", "Red"
    @SerialName("hazard")
    val hazard: String,
    @SerialName("severity")
    val severity: String,
    @SerialName("area_description")
    val areaDescription: String,
    @SerialName("headline")
    val headline: String,
    @SerialName("description")
    val description: String,
    @SerialName("effective_from")
    val effectiveFrom: String,
    @SerialName("expires_at")
    val expiresAt: String,
    @SerialName("instructions")
    val instructions: String? = null
)

@Serializable
data class WeatherAlertsResponseDto(
    @SerialName("authority")
    val authority: String = "India Meteorological Department (IMD)",
    @SerialName("retrieved_at")
    val retrievedAt: String,
    @SerialName("active_alerts_count")
    val activeAlertsCount: Int,
    @SerialName("alerts")
    val alerts: List<OfficialAlertItemDto> = emptyList()
)

@Serializable
data class WeatherIntelligenceResponseDto(
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("data_quality")
    val dataQuality: String? = null,
    @SerialName("current_observation")
    val currentObservation: CurrentWeatherResponseDto? = null,
    @SerialName("alerts")
    val alerts: List<OfficialAlertItemDto>? = null,
    @SerialName("provenance")
    val provenance: JsonObject? = null,
    @SerialName("message")
    val message: String? = null,
    @SerialName("error")
    val error: String? = null
)
