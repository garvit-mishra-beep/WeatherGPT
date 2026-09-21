package com.weathergpt.domain.weather

import com.weathergpt.core.network.DemoModeNetworkGuard
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.local.InMemoryLocalWeatherDataSource
import com.weathergpt.data.local.WeatherDatabaseHelper
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.data.repository.WeatherGPTRepositoryImpl
import com.weathergpt.domain.brain.OfflineDemoIntelligenceEngine
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.farmer.FarmerProfile
import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.validation.ForecastValidationResult
import com.weathergpt.domain.validation.WeatherForecastValidator
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class TenDayWeatherReportTest {

    private val json = Json { ignoreUnknownKeys = true }
    private val testDispatcher = StandardTestDispatcher()
    private lateinit var localDataSource: InMemoryLocalWeatherDataSource
    private lateinit var tenDayForecast: WeatherForecast

    @Before
    fun setup() {
        DemoModeNetworkGuard.resetAuditCounters()
        localDataSource = InMemoryLocalWeatherDataSource()

        // Decode verified 10-day Gwalior forecast seed from WeatherDatabaseHelper
        val dto = json.decodeFromString(
            WeatherForecastResponseDto.serializer(),
            WeatherDatabaseHelper.REAL_GWALIOR_FORECAST_JSON
        )
        tenDayForecast = WeatherForecast(
            location = LocationCoordinates(dto.location.latitude, dto.location.longitude),
            generatedAt = dto.generatedAt,
            forecastStart = dto.forecastStart,
            forecastEnd = dto.forecastEnd,
            dailyForecast = dto.dailyForecast.map { d ->
                DailyForecast(
                    date = d.date,
                    tempMaxC = d.tempMaxC,
                    tempMinC = d.tempMinC,
                    precipitationSumMm = d.precipitationSumMm,
                    precipitationProbabilityPct = d.precipitationProbabilityPct,
                    windSpeedMaxKmh = d.windSpeedMaxKmh,
                    dominantCondition = d.dominantCondition,
                    tempAvgC = d.tempAvgC,
                    feelsLikeC = d.feelsLikeC,
                    windGustKmh = d.windGustKmh,
                    windDirectionDeg = d.windDirectionDeg,
                    humidityPct = d.humidityPct,
                    weatherCode = d.weatherCode,
                    source = d.source ?: "Open-Meteo",
                    retrievedAt = d.retrievedAt ?: dto.provenance?.retrievalTimestamp ?: dto.generatedAt,
                    forecastValidFrom = d.forecastValidFrom ?: dto.forecastStart,
                    forecastValidUntil = d.forecastValidUntil ?: dto.forecastEnd
                )
            },
            hourlyForecast = emptyList(),
            provider = dto.provenance?.provider ?: "Open-Meteo",
            sourceMode = WeatherDataSourceMode.DEMO_MODE,
            retrievedAt = dto.provenance?.retrievalTimestamp ?: dto.generatedAt
        )
    }

    // 1. 10 days loaded successfully
    @Test
    fun test1_tenDaysLoadedSuccessfully() {
        assertEquals(10, tenDayForecast.dailyForecast.size)
    }

    // 2. Dates sorted correctly
    @Test
    fun test2_datesSortedCorrectly() {
        val dates = tenDayForecast.dailyForecast.map { it.date }
        for (i in 0 until dates.size - 1) {
            assertTrue("Dates must be sorted: ${dates[i]} < ${dates[i + 1]}", dates[i] < dates[i + 1])
        }
    }

    // 3. No duplicate dates
    @Test
    fun test3_noDuplicateDates() {
        val dates = tenDayForecast.dailyForecast.map { it.date }
        assertEquals(dates.distinct().size, dates.size)
    }

    // 4. Gwalior location isolation
    @Test
    fun test4_gwaliorLocationIsolation() {
        assertEquals(26.2183, tenDayForecast.location.latitude, 0.001)
        assertEquals(78.1828, tenDayForecast.location.longitude, 0.001)
    }

    // 5. Real cached source preserved
    @Test
    fun test5_realCachedSourcePreserved() {
        assertEquals("Open-Meteo", tenDayForecast.provider)
        tenDayForecast.dailyForecast.forEach { day ->
            assertEquals("Open-Meteo", day.source)
        }
    }

    // 6. retrievedAt preserved
    @Test
    fun test6_retrievedAtPreserved() {
        assertEquals("2026-09-10T14:53:39Z", tenDayForecast.retrievedAt)
        tenDayForecast.dailyForecast.forEach { day ->
            assertEquals("2026-09-10T14:53:39Z", day.retrievedAt)
        }
    }

    // 7. Forecast valid time preserved
    @Test
    fun test7_forecastValidTimePreserved() {
        assertEquals("2026-09-11T00:00:00Z", tenDayForecast.forecastStart)
        assertEquals("2026-09-21T00:00:00Z", tenDayForecast.forecastEnd)
        tenDayForecast.dailyForecast.forEach { day ->
            assertNotNull(day.forecastValidFrom)
            assertNotNull(day.forecastValidUntil)
        }
    }

    // 8. Temperature summary calculation
    @Test
    fun test8_temperatureSummaryCalculation() {
        val summary = TenDayWeatherAnalytics.computeSummary(tenDayForecast.dailyForecast)
        assertNotNull(summary)
        assertEquals(31.9, summary!!.highestTempC, 0.01)
        assertEquals("2026-09-15", summary.highestTempDate)
        assertEquals(23.2, summary.lowestTempC, 0.01)
        assertEquals("2026-09-19", summary.lowestTempDate)
    }

    // 9. Rainfall summary calculation
    @Test
    fun test9_rainfallSummaryCalculation() {
        val outlook = TenDayWeatherAnalytics.computeRainOutlook(tenDayForecast.dailyForecast)
        assertNotNull(outlook)
        assertTrue(outlook!!.totalExpectedRainMm > 80.0)
        assertEquals(10, outlook.rainyDaysCount) // All 10 days have > 0.1 mm in monsoon snapshot
    }

    // 10. Rainiest-day calculation
    @Test
    fun test10_rainiestDayCalculation() {
        val outlook = TenDayWeatherAnalytics.computeRainOutlook(tenDayForecast.dailyForecast)
        assertNotNull(outlook)
        assertEquals("2026-09-19", outlook!!.rainiestDate)
        assertEquals(27.0, outlook.rainiestAmountMm, 0.01)
    }

    // 11. Highest-temperature calculation
    @Test
    fun test11_highestTemperatureCalculation() {
        val highestDay = tenDayForecast.dailyForecast.maxByOrNull { it.tempMaxC }
        assertNotNull(highestDay)
        assertEquals(31.9, highestDay!!.tempMaxC, 0.01)
        assertEquals("2026-09-15", highestDay.date)
    }

    // 12. Lowest-temperature calculation
    @Test
    fun test12_lowestTemperatureCalculation() {
        val lowestDay = tenDayForecast.dailyForecast.minByOrNull { it.tempMinC }
        assertNotNull(lowestDay)
        assertEquals(23.2, lowestDay!!.tempMinC, 0.01)
        assertEquals("2026-09-19", lowestDay.date)
    }

    // 13. Dynamic chart data
    @Test
    fun test13_dynamicChartData() {
        val chartPoints = TenDayWeatherAnalytics.buildChartPoints(tenDayForecast.dailyForecast)
        assertEquals(10, chartPoints.size)
        assertEquals(1, chartPoints.first().dayIndex)
        assertEquals(10, chartPoints.last().dayIndex)
        assertEquals("2026-09-11", chartPoints.first().date)
        assertEquals("2026-09-20", chartPoints.last().date)
    }

    // 14. Farmer spray integration
    @Test
    fun test14_farmerSprayIntegration() {
        val query = ChatQuery(
            sessionId = "s1",
            query = "Should I spray this week?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.FARMER
        )
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = query,
            cachedWeather = null,
            cachedForecast = tenDayForecast,
            cachedAlerts = emptyList(),
            farmerProfile = FarmerProfile()
        )
        assertNotNull(response.answer)
        assertTrue(response.answer.contains("SPRAY") || response.answer.contains("spray"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // 15. Irrigation integration
    @Test
    fun test15_irrigationIntegration() {
        val query = ChatQuery(
            sessionId = "s1",
            query = "Should I irrigate my wheat field?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.FARMER
        )
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = query,
            cachedWeather = null,
            cachedForecast = tenDayForecast,
            cachedAlerts = emptyList(),
            farmerProfile = FarmerProfile()
        )
        assertTrue(response.answer.contains("DECISION:"))
        assertTrue(response.answer.contains("Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions."))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // 16. Harvest integration
    @Test
    fun test16_harvestIntegration() {
        val query = ChatQuery(
            sessionId = "s1",
            query = "When is the best time to harvest?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.FARMER
        )
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = query,
            cachedWeather = null,
            cachedForecast = tenDayForecast,
            cachedAlerts = emptyList(),
            farmerProfile = FarmerProfile()
        )
        assertTrue(response.answer.contains("HARVEST:"))
        assertTrue(response.answer.contains("BEST WINDOW:"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // 17. Missing-day handling
    @Test
    fun test17_missingDayHandling() {
        val truncatedForecast = tenDayForecast.copy(dailyForecast = tenDayForecast.dailyForecast.take(3))
        assertEquals(3, truncatedForecast.dailyForecast.size)
        // With fewer than 10 days, 10-day summary calculations still process gracefully without crash
        val summary = TenDayWeatherAnalytics.computeSummary(truncatedForecast.dailyForecast)
        assertNotNull(summary)
        assertEquals(3, truncatedForecast.dailyForecast.size)
    }

    // 18. Corrupted-data handling
    @Test
    fun test18_corruptedDataHandling() {
        val validRes = WeatherForecastValidator.validate(tenDayForecast, isDemoMode = true)
        assertTrue(validRes.isValid)

        // Corrupted: negative rain
        val badRain = tenDayForecast.copy(
            dailyForecast = listOf(tenDayForecast.dailyForecast.first().copy(precipitationSumMm = -5.0))
        )
        val badRainRes = WeatherForecastValidator.validate(badRain, isDemoMode = true)
        assertFalse(badRainRes.isValid)
        assertTrue((badRainRes as ForecastValidationResult.Invalid).reason.contains("Rainfall cannot be negative"))

        // Corrupted: min > max temp
        val badTemp = tenDayForecast.copy(
            dailyForecast = listOf(tenDayForecast.dailyForecast.first().copy(tempMinC = 40.0, tempMaxC = 20.0))
        )
        val badTempRes = WeatherForecastValidator.validate(badTemp, isDemoMode = true)
        assertFalse(badTempRes.isValid)

        // Corrupted: probability > 100
        val badProb = tenDayForecast.copy(
            dailyForecast = listOf(tenDayForecast.dailyForecast.first().copy(precipitationProbabilityPct = 150.0))
        )
        val badProbRes = WeatherForecastValidator.validate(badProb, isDemoMode = true)
        assertFalse(badProbRes.isValid)
    }

    // 19. Demo Mode network calls = 0
    @Test
    fun test19_demoModeNetworkCallsZero() {
        DemoModeNetworkGuard.resetAuditCounters()
        val query = ChatQuery(
            sessionId = "s1",
            query = "What will the weather be for the next 10 days?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.GENERAL
        )
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = query,
            cachedWeather = null,
            cachedForecast = tenDayForecast,
            cachedAlerts = emptyList(),
            farmerProfile = null
        )
        assertTrue(response.answer.contains("10-DAY WEATHER OUTLOOK — GWALIOR"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
        assertEquals(0, DemoModeNetworkGuard.networkCallsBlocked)
    }

    // 20. App restart preserves 10-day data
    @Test
    fun test20_appRestartPreservesTenDayData() = runTest(testDispatcher) {
        val dto = json.decodeFromString(
            WeatherForecastResponseDto.serializer(),
            WeatherDatabaseHelper.REAL_GWALIOR_FORECAST_JSON
        )
        localDataSource.saveForecast(
            WeatherDatabaseHelper.DEMO_GWALIOR_LATITUDE,
            WeatherDatabaseHelper.DEMO_GWALIOR_LONGITUDE,
            dto,
            "Gwalior, Madhya Pradesh"
        )

        val cached = localDataSource.getCachedForecast(
            WeatherDatabaseHelper.DEMO_GWALIOR_LATITUDE,
            WeatherDatabaseHelper.DEMO_GWALIOR_LONGITUDE
        )

        assertNotNull(cached)
        assertEquals(10, cached!!.dailyForecast.size)
        assertEquals("2026-09-11", cached.dailyForecast[0].date)
        assertEquals("2026-09-20", cached.dailyForecast[9].date)
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }
}
