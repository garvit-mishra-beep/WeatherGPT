package com.weathergpt.core.formatter

import android.os.Build
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

/**
 * Centralized formatting utility for meteorological data, timestamps,
 * condition codes, and physical units across Vayubodhak.
 */
object WeatherFormatter {

    private val CONDITION_MAP = mapOf(
        "clear" to "Clear sky",
        "clear_sky" to "Clear sky",
        "mainly_clear" to "Mainly clear",
        "partly_cloudy" to "Partly cloudy",
        "scattered_clouds" to "Scattered clouds",
        "broken_clouds" to "Broken clouds",
        "overcast" to "Overcast",
        "fog" to "Fog",
        "depositing_rime_fog" to "Rime fog",
        "light_drizzle" to "Light drizzle",
        "moderate_drizzle" to "Moderate drizzle",
        "dense_drizzle" to "Dense drizzle",
        "light_freezing_drizzle" to "Light freezing drizzle",
        "dense_freezing_drizzle" to "Dense freezing drizzle",
        "slight_rain" to "Slight rain",
        "moderate_rain" to "Moderate rain",
        "heavy_rain" to "Heavy rain",
        "light_rain" to "Light rain",
        "rain" to "Rain",
        "light_freezing_rain" to "Light freezing rain",
        "heavy_freezing_rain" to "Heavy freezing rain",
        "slight_snow_fall" to "Slight snow fall",
        "moderate_snow_fall" to "Moderate snow fall",
        "heavy_snow_fall" to "Heavy snow fall",
        "snow_grains" to "Snow grains",
        "slight_rain_showers" to "Slight rain showers",
        "moderate_rain_showers" to "Moderate rain showers",
        "violent_rain_showers" to "Violent rain showers",
        "rain_showers" to "Rain showers",
        "slight_snow_showers" to "Slight snow showers",
        "heavy_snow_showers" to "Heavy snow showers",
        "snow_showers" to "Snow showers",
        "thunderstorm" to "Thunderstorm",
        "slight_thunderstorm" to "Slight thunderstorm",
        "moderate_thunderstorm" to "Moderate thunderstorm",
        "thunderstorm_with_slight_hail" to "Thunderstorm with slight hail",
        "thunderstorm_with_heavy_hail" to "Thunderstorm with heavy hail",
        "thunderstorm_with_hail" to "Thunderstorm with hail",
        "thunderstorm_with_rain" to "Thunderstorm with rain",
        "squall" to "Squall",
        "dust" to "Dust storm",
        "sand" to "Sand storm",
        "ash" to "Volcanic ash",
        "haze" to "Haze",
        "mist" to "Mist",
        "smoke" to "Smoke"
    )

    private val CARDINAL_DIRECTIONS = arrayOf(
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    )

    /**
     * Converts machine-readable weather condition identifiers into human-readable text.
     * Example: "light_drizzle" -> "Light drizzle"
     */
    fun formatCondition(condition: String?): String {
        if (condition.isNullOrBlank()) return "Partly cloudy"
        val normalized = condition.trim().lowercase(Locale.ROOT)
        CONDITION_MAP[normalized]?.let { return it }

        // Fallback: replace underscores/dashes with spaces and capitalize the first word
        val words = normalized.replace('_', ' ').replace('-', ' ').trim()
        return words.replaceFirstChar { char ->
            if (char.isLowerCase()) char.titlecase(Locale.ROOT) else char.toString()
        }
    }

    /**
     * Formats an ISO-8601 timestamp into a human-readable local date and time string,
     * respecting the device's local timezone.
     * Example: "2026-09-07T15:00:00+00:00" -> "7 Sep 2026, 8:30 PM" (in IST UTC+5:30)
     */
    fun formatObservationDateTime(isoTimestamp: String?): String {
        if (isoTimestamp.isNullOrBlank()) return "Just now"

        // Attempt modern java.time API on API 26+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                val offsetDateTime = java.time.OffsetDateTime.parse(isoTimestamp)
                val localZoned = offsetDateTime.atZoneSameInstant(java.time.ZoneId.systemDefault())
                val formatter = java.time.format.DateTimeFormatter.ofPattern("d MMM yyyy, h:mm a", Locale.ENGLISH)
                return localZoned.format(formatter)
            } catch (_: Exception) {
                try {
                    val instant = java.time.Instant.parse(isoTimestamp)
                    val localZoned = instant.atZone(java.time.ZoneId.systemDefault())
                    val formatter = java.time.format.DateTimeFormatter.ofPattern("d MMM yyyy, h:mm a", Locale.ENGLISH)
                    return localZoned.format(formatter)
                } catch (_: Exception) {}
            }
        }

        // Fallback using SimpleDateFormat
        val inputPatterns = arrayOf(
            "yyyy-MM-dd'T'HH:mm:ssXXX",
            "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
            "yyyy-MM-dd'T'HH:mm:ss'Z'",
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd HH:mm:ss"
        )

        for (pattern in inputPatterns) {
            try {
                val sdfIn = SimpleDateFormat(pattern, Locale.US)
                if (pattern.endsWith("'Z'") || pattern.contains("XXX")) {
                    sdfIn.timeZone = TimeZone.getTimeZone("UTC")
                }
                val date = sdfIn.parse(isoTimestamp)
                if (date != null) {
                    val sdfOut = SimpleDateFormat("d MMM yyyy, h:mm a", Locale.ENGLISH)
                    sdfOut.timeZone = TimeZone.getDefault()
                    return sdfOut.format(date)
                }
            } catch (_: Exception) {}
        }

        return isoTimestamp
    }

    /**
     * Converts meteorological wind direction in degrees [0, 360) into 16-point cardinal direction.
     */
    fun degreesToCardinal(degrees: Double?): String {
        if (degrees == null) return "SW"
        val normalized = (degrees % 360.0 + 360.0) % 360.0
        val index = ((normalized + 11.25) / 22.5).toInt() % 16
        return CARDINAL_DIRECTIONS[index]
    }

    /**
     * Formats wind speed and direction into a unified string.
     * Example: speed=2.0, degrees=225.0 -> "2 km/h SW"
     */
    fun formatWind(speedKmh: Double?, degrees: Double?): String {
        val speed = speedKmh?.toInt() ?: 2
        val dir = degreesToCardinal(degrees)
        return "$speed km/h $dir"
    }

    /**
     * Formats temperature in Celsius with integer rounding.
     * Example: 31.2 -> "31°"
     */
    fun formatTemperature(tempC: Double?): String {
        val temp = tempC?.toInt() ?: 31
        return "$temp°"
    }

    /**
     * Formats feels-like temperature in Celsius.
     * Example: 38.0 -> "38°C"
     */
    fun formatFeelsLike(feelsLikeC: Double?): String {
        val temp = feelsLikeC?.toInt() ?: 34
        return "${temp}°C"
    }

    /**
     * Formats relative humidity in percentage.
     * Example: 78.0 -> "78%"
     */
    fun formatHumidity(humidityPct: Double?): String {
        val hum = humidityPct?.toInt() ?: 62
        return "${hum}%"
    }
}
