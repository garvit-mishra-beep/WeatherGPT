package com.weathergpt.domain.model.weather

import kotlinx.serialization.json.JsonObject

enum class WeatherDataSourceMode {
    LIVE,
    DEMO_MODE
}

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
    val authority: String?,
    val sourceMode: WeatherDataSourceMode = WeatherDataSourceMode.LIVE,
    val retrievedAt: String? = null
) {
    val isCached: Boolean get() = sourceMode == WeatherDataSourceMode.DEMO_MODE
}

data class DailyForecast(
    val date: String,
    val tempMaxC: Double,
    val tempMinC: Double,
    val precipitationSumMm: Double,
    val precipitationProbabilityPct: Double,
    val windSpeedMaxKmh: Double,
    val dominantCondition: String,
    val tempAvgC: Double? = null,
    val feelsLikeC: Double? = null,
    val windGustKmh: Double? = null,
    val windDirectionDeg: Double? = null,
    val humidityPct: Double? = null,
    val weatherCode: Int? = null,
    val source: String? = null,
    val retrievedAt: String? = null,
    val forecastValidFrom: String? = null,
    val forecastValidUntil: String? = null
) {
    val dayName: String
        get() = try {
            java.time.LocalDate.parse(date.take(10)).dayOfWeek.name.lowercase().replaceFirstChar { it.uppercase() }
        } catch (_: Exception) {
            "Day"
        }

    val minTemperature: Double get() = tempMinC
    val maxTemperature: Double get() = tempMaxC
    val precipitationMm: Double get() = precipitationSumMm
    val precipitationProbability: Double get() = precipitationProbabilityPct
    val windSpeed: Double get() = windSpeedMaxKmh
    val condition: String get() = dominantCondition
}

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
    val provider: String?,
    val sourceMode: WeatherDataSourceMode = WeatherDataSourceMode.LIVE,
    val retrievedAt: String? = null
) {
    val isCached: Boolean get() = sourceMode == WeatherDataSourceMode.DEMO_MODE
}

enum class AlertSeverity(val colorHex: Long) {
    GREEN(0xFF16A34A),
    YELLOW(0xFFCA8A04),
    ORANGE(0xFFEA580C),
    RED(0xFFDC2626);

    companion object {
        fun fromString(value: String): AlertSeverity = when (value.uppercase()) {
            "RED" -> RED
            "ORANGE" -> ORANGE
            "YELLOW" -> YELLOW
            "GREEN" -> GREEN
            else -> YELLOW
        }
    }
}

enum class SpatialStatus {
    INSIDE,
    BUFFER,
    OUTSIDE,
    UNKNOWN;

    companion object {
        fun fromString(value: String?): SpatialStatus = when (value?.uppercase()) {
            "INSIDE" -> INSIDE
            "BUFFER" -> BUFFER
            "OUTSIDE" -> OUTSIDE
            else -> UNKNOWN
        }
    }
}

data class OfficialAlert(
    val alertId: String,
    val title: String = "",
    val hazardType: String = "Other",
    val severity: String = "YELLOW",
    val warningColor: String = severity,
    val hazard: String = hazardType,
    val issuingAgency: String = "India Meteorological Department (IMD)",
    val source: String = "Operational CAP Weather Alert Bulletin",
    val issuedAt: String = "",
    val validFrom: String = "",
    val validUntil: String = "",
    val affectedArea: String = "",
    val areaDescription: String = affectedArea,
    val headline: String = title.ifBlank { areaDescription },
    val description: String = "",
    val instructions: String? = null,
    val instructionsList: List<String> = instructions?.split("\n", ";")?.map { it.trim().removePrefix("•").trim() }?.filter { it.isNotBlank() } ?: emptyList(),
    val spatialStatus: SpatialStatus = SpatialStatus.INSIDE,
    val isOfficial: Boolean = true,
    val isActive: Boolean = true,
    val retrievedAt: String = "",
    val provenance: String = "IMD / Open-Meteo",
    val effectiveFrom: String = validFrom,
    val expiresAt: String = validUntil
) {
    val parsedSeverity: AlertSeverity
        get() = AlertSeverity.fromString(severity.ifBlank { warningColor })
}

data class WeatherAlertsReport(
    val authority: String,
    val retrievedAt: String,
    val activeAlertsCount: Int,
    val alerts: List<OfficialAlert>,
    val isCached: Boolean = false
)

data class WeatherIntelligence(
    val latitude: Double,
    val longitude: Double,
    val dataQuality: String?,
    val currentObservation: CurrentWeather?,
    val alerts: List<OfficialAlert>,
    val rawProvenance: JsonObject?
)
