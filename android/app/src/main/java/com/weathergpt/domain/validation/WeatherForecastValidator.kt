package com.weathergpt.domain.validation

import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.WeatherForecast
import kotlin.math.abs

sealed class ForecastValidationResult {
    data object Valid : ForecastValidationResult()
    data class Invalid(val reason: String) : ForecastValidationResult()

    val isValid: Boolean get() = this is Valid
}

object WeatherForecastValidator {

    const val GWALIOR_LAT = 26.2183
    const val GWALIOR_LON = 78.1828
    const val LOCATION_TOLERANCE = 0.05

    fun validate(forecast: WeatherForecast?, isDemoMode: Boolean = true): ForecastValidationResult {
        if (forecast == null) {
            return ForecastValidationResult.Invalid("Forecast data is null.")
        }

        if (isDemoMode) {
            if (abs(forecast.location.latitude - GWALIOR_LAT) > LOCATION_TOLERANCE ||
                abs(forecast.location.longitude - GWALIOR_LON) > LOCATION_TOLERANCE
            ) {
                return ForecastValidationResult.Invalid("Location coordinates (${forecast.location.latitude}, ${forecast.location.longitude}) do not match Gwalior Demo location.")
            }
        }

        val daily = forecast.dailyForecast
        if (daily.isEmpty()) {
            return ForecastValidationResult.Invalid("Daily forecast dataset is empty.")
        }

        // Check for duplicate dates
        val dates = daily.map { it.date }
        if (dates.distinct().size != dates.size) {
            return ForecastValidationResult.Invalid("Duplicate dates detected in forecast.")
        }

        // Check dates are ordered
        for (i in 0 until daily.size - 1) {
            if (daily[i].date > daily[i + 1].date) {
                return ForecastValidationResult.Invalid("Forecast dates are not in chronological order: ${daily[i].date} > ${daily[i + 1].date}.")
            }
        }

        // Check daily items
        for (day in daily) {
            val dayRes = validateDailyForecast(day)
            if (dayRes is ForecastValidationResult.Invalid) {
                return dayRes
            }
        }

        // Check timestamps and source
        if (forecast.generatedAt.isBlank()) {
            return ForecastValidationResult.Invalid("generatedAt timestamp is missing.")
        }

        return ForecastValidationResult.Valid
    }

    fun validateDailyForecast(day: DailyForecast): ForecastValidationResult {
        if (day.date.isBlank()) {
            return ForecastValidationResult.Invalid("Date is blank.")
        }
        if (day.tempMinC > day.tempMaxC) {
            return ForecastValidationResult.Invalid("Invalid temperature: min (${day.tempMinC}°C) exceeds max (${day.tempMaxC}°C) on ${day.date}.")
        }
        if (day.tempMinC < -50.0 || day.tempMaxC > 60.0) {
            return ForecastValidationResult.Invalid("Temperature value out of meteorological physical limits on ${day.date}.")
        }
        if (day.precipitationSumMm < 0.0) {
            return ForecastValidationResult.Invalid("Rainfall cannot be negative: ${day.precipitationSumMm} mm on ${day.date}.")
        }
        if (day.precipitationProbabilityPct < 0.0 || day.precipitationProbabilityPct > 100.0) {
            return ForecastValidationResult.Invalid("Precipitation probability must be in 0..100: ${day.precipitationProbabilityPct}% on ${day.date}.")
        }
        if (day.windSpeedMaxKmh < 0.0) {
            return ForecastValidationResult.Invalid("Wind speed cannot be negative: ${day.windSpeedMaxKmh} km/h on ${day.date}.")
        }
        day.windGustKmh?.let {
            if (it < 0.0) return ForecastValidationResult.Invalid("Wind gust cannot be negative: $it km/h on ${day.date}.")
        }
        day.humidityPct?.let {
            if (it < 0.0 || it > 100.0) return ForecastValidationResult.Invalid("Humidity must be in 0..100: $it% on ${day.date}.")
        }
        return ForecastValidationResult.Valid
    }
}
