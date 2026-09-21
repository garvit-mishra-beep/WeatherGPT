package com.weathergpt.domain.weather

import com.weathergpt.domain.model.weather.DailyForecast
import java.util.Locale

data class TenDaySummary(
    val highestTempC: Double,
    val highestTempDate: String,
    val lowestTempC: Double,
    val lowestTempDate: String,
    val highestRainProbPct: Double,
    val highestRainProbDate: String,
    val totalExpectedRainMm: Double,
    val windiestSpeedKmh: Double,
    val windiestDate: String
)

data class RainOutlook(
    val totalExpectedRainMm: Double,
    val rainiestDate: String,
    val rainiestAmountMm: Double,
    val highestRainProbPct: Double,
    val rainyDaysCount: Int
)

data class ConditionSummary(
    val sunnyDays: Int,
    val cloudyDays: Int,
    val rainyDays: Int,
    val stormDays: Int,
    val otherDays: Int
)

data class ChartPoint(
    val dayIndex: Int,
    val label: String,
    val date: String,
    val tempMaxC: Double,
    val tempMinC: Double,
    val precipitationMm: Double,
    val precipitationProbabilityPct: Double
)

object TenDayWeatherAnalytics {

    fun computeSummary(days: List<DailyForecast>): TenDaySummary? {
        if (days.isEmpty()) return null
        val highestTempDay = days.maxByOrNull { it.tempMaxC } ?: days.first()
        val lowestTempDay = days.minByOrNull { it.tempMinC } ?: days.first()
        val highestProbDay = days.maxByOrNull { it.precipitationProbabilityPct } ?: days.first()
        val totalRain = days.sumOf { it.precipitationSumMm }
        val windiestDay = days.maxByOrNull { it.windSpeedMaxKmh } ?: days.first()

        return TenDaySummary(
            highestTempC = highestTempDay.tempMaxC,
            highestTempDate = highestTempDay.date,
            lowestTempC = lowestTempDay.tempMinC,
            lowestTempDate = lowestTempDay.date,
            highestRainProbPct = highestProbDay.precipitationProbabilityPct,
            highestRainProbDate = highestProbDay.date,
            totalExpectedRainMm = totalRain,
            windiestSpeedKmh = windiestDay.windSpeedMaxKmh,
            windiestDate = windiestDay.date
        )
    }

    fun computeRainOutlook(days: List<DailyForecast>): RainOutlook? {
        if (days.isEmpty()) return null
        val totalRain = days.sumOf { it.precipitationSumMm }
        val rainiestDay = days.maxByOrNull { it.precipitationSumMm } ?: days.first()
        val highestProb = days.maxOfOrNull { it.precipitationProbabilityPct } ?: 0.0
        val rainyCount = days.count { it.precipitationSumMm > 0.1 }

        return RainOutlook(
            totalExpectedRainMm = totalRain,
            rainiestDate = rainiestDay.date,
            rainiestAmountMm = rainiestDay.precipitationSumMm,
            highestRainProbPct = highestProb,
            rainyDaysCount = rainyCount
        )
    }

    fun computeConditions(days: List<DailyForecast>): ConditionSummary {
        var sunny = 0
        var cloudy = 0
        var rainy = 0
        var storm = 0
        var other = 0

        for (day in days) {
            val cond = day.dominantCondition.lowercase(Locale.ROOT)
            val code = day.weatherCode ?: -1
            when {
                cond.contains("thunder") || cond.contains("storm") || code in 95..99 -> storm++
                cond.contains("rain") || cond.contains("drizzle") || cond.contains("shower") || code in 51..69 || code in 80..82 -> rainy++
                cond.contains("cloud") || cond.contains("overcast") || code in 1..3 -> cloudy++
                cond.contains("clear") || cond.contains("sun") || code == 0 -> sunny++
                else -> other++
            }
        }

        return ConditionSummary(
            sunnyDays = sunny,
            cloudyDays = cloudy,
            rainyDays = rainy,
            stormDays = storm,
            otherDays = other
        )
    }

    fun buildChartPoints(days: List<DailyForecast>): List<ChartPoint> {
        return days.mapIndexed { index, day ->
            val shortLabel = try {
                val parsed = java.time.LocalDate.parse(day.date.take(10))
                "${parsed.dayOfMonth} ${parsed.month.name.take(3).lowercase().replaceFirstChar { it.uppercase() }}"
            } catch (_: Exception) {
                "D${index + 1}"
            }
            ChartPoint(
                dayIndex = index + 1,
                label = shortLabel,
                date = day.date,
                tempMaxC = day.tempMaxC,
                tempMinC = day.tempMinC,
                precipitationMm = day.precipitationSumMm,
                precipitationProbabilityPct = day.precipitationProbabilityPct
            )
        }
    }
}
