package com.weathergpt.domain.brain

import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.network.DemoModeNetworkGuard
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.farmer.FarmerProfile
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import com.weathergpt.domain.model.weather.WeatherForecast
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class OfflineDemoQuestionsTest {

    private val originalDemoMode = AppConfig.isDemoMode

    private val sampleGwaliorWeather = CurrentWeather(
        location = LocationCoordinates(26.2183, 78.1828),
        observationTime = "2026-09-10T14:30:00Z",
        temperatureC = 29.5,
        feelsLikeC = 32.0,
        relativeHumidityPct = 65.0,
        precipitationMm = 0.0,
        rainIntensityCategory = "None",
        windSpeedKmh = 12.0,
        windDirectionDeg = 110.0,
        surfacePressureHpa = 1008.0,
        weatherCondition = "Partly Cloudy",
        provider = "Open-Meteo",
        authority = "Open-Meteo",
        sourceMode = WeatherDataSourceMode.DEMO_MODE,
        retrievedAt = "2026-09-10T14:53:39Z"
    )

    private val sampleGwaliorForecast = WeatherForecast(
        location = LocationCoordinates(26.2183, 78.1828),
        generatedAt = "2026-09-10T14:53:39Z",
        forecastStart = "2026-09-10T00:00:00Z",
        forecastEnd = "2026-09-12T00:00:00Z",
        dailyForecast = listOf(
            DailyForecast(
                date = "2026-09-10",
                tempMaxC = 34.0,
                tempMinC = 25.0,
                precipitationSumMm = 0.0,
                precipitationProbabilityPct = 10.0,
                windSpeedMaxKmh = 14.0,
                dominantCondition = "Clear"
            ),
            DailyForecast(
                date = "2026-09-11",
                tempMaxC = 33.5,
                tempMinC = 24.5,
                precipitationSumMm = 0.2,
                precipitationProbabilityPct = 15.0,
                windSpeedMaxKmh = 16.0,
                dominantCondition = "Partly Cloudy"
            )
        ),
        hourlyForecast = emptyList(),
        provider = "Open-Meteo",
        sourceMode = WeatherDataSourceMode.DEMO_MODE,
        retrievedAt = "2026-09-10T14:53:39Z"
    )

    private val sampleAlerts: List<OfficialAlert> = emptyList()

    private val sampleFarmerProfile = FarmerProfile(
        fullName = "Ramesh Patel",
        crop = "Wheat",
        cropStage = "Vegetative",
        farmArea = 2.5,
        areaUnit = "hectare",
        soilType = "Alluvial",
        irrigationType = "Drip"
    )

    @Before
    fun setup() {
        AppConfig.isDemoMode = true
        DemoModeNetworkGuard.resetAuditCounters()
    }

    @After
    fun tearDown() {
        AppConfig.isDemoMode = originalDemoMode
        DemoModeNetworkGuard.resetAuditCounters()
    }

    @Test
    fun `question bank contains exactly 20 demo questions with 5 per brain`() {
        assertEquals(20, OfflineDemoIntelligenceEngine.DEMO_QUESTION_BANK.size)
        assertEquals(5, OfflineDemoIntelligenceEngine.DEMO_QUESTION_BANK.count { it.brain == DomainBrain.GENERAL })
        assertEquals(5, OfflineDemoIntelligenceEngine.DEMO_QUESTION_BANK.count { it.brain == DomainBrain.FARMER })
        assertEquals(5, OfflineDemoIntelligenceEngine.DEMO_QUESTION_BANK.count { it.brain == DomainBrain.RESEARCHER })
        assertEquals(5, OfflineDemoIntelligenceEngine.DEMO_QUESTION_BANK.count { it.brain == DomainBrain.ANALYST })
    }

    // ========================================================================
    // Brain 1 — General Questions
    // ========================================================================

    @Test
    fun `G1 - What is the weather in Gwalior today`() {
        val q = "What is the weather in Gwalior today?"
        assertEquals(DomainBrain.GENERAL, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.AUTO),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("Gwalior"))
        assertTrue(response.answer.contains("VERDICT"))
        assertTrue(response.answer.contains("WHAT WE KNOW"))
        assertTrue(response.answer.contains("WHAT IT MEANS"))
        assertTrue(response.answer.contains("WHAT YOU SHOULD DO"))
        assertTrue(response.answer.contains("CONFIDENCE"))
        assertTrue(response.answer.contains("WHY"))
        assertTrue(response.answer.contains("SOURCE"))
        assertTrue(response.answer.contains("OPERATIONAL STATUS") || response.answer.contains("DEMO MODE"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `G2 - What will the weather be like tomorrow`() {
        val q = "What will the weather be like tomorrow?"
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.GENERAL),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("tomorrow") || response.answer.contains("Tomorrow"))
        assertTrue(response.answer.contains("WHAT WE KNOW"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `G3 - Will it rain today`() {
        val q = "Will it rain today?"
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.GENERAL),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("Rain is") || response.answer.contains("rain"))
        assertTrue(response.answer.contains("CONFIDENCE"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `G4 - Is the weather suitable for going outside`() {
        val q = "Is the weather suitable for going outside?"
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.GENERAL),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("ACTIVITY:"))
        assertTrue(response.answer.contains("WHAT YOU SHOULD DO"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `G5 - Why are you showing Demo Mode`() {
        val q = "Why are you showing Demo Mode?"
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.GENERAL),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("offline") || response.answer.contains("Offline"))
        assertTrue(response.answer.contains("SQLite") || response.answer.contains("local"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // ========================================================================
    // Brain 2 — Farmer Questions
    // ========================================================================

    @Test
    fun `F1 - Should I spray my crop today`() {
        val q = "Should I spray my crop today?"
        assertEquals(DomainBrain.FARMER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.FARMER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("VERDICT: GO") || response.answer.contains("POSTPONE") || response.answer.contains("NO_GO"))
        assertTrue(response.answer.contains("Wheat"))
        assertNotNull(OfflineDemoIntelligenceEngine.lastEvaluatedNirnayCard)
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `F2 - Should I irrigate my wheat field`() {
        val q = "Should I irrigate my wheat field?"
        assertEquals(DomainBrain.FARMER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.FARMER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("IRRIGATE") || response.answer.contains("IRRIGATION"))
        assertTrue(response.answer.contains("ET0") || response.answer.contains("ETc"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `F3 - When is the best time to harvest`() {
        val q = "When is the best time to harvest?"
        assertEquals(DomainBrain.FARMER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.FARMER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("HARVEST:"))
        assertTrue(response.answer.contains("BEST WINDOW:"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `F4 - Should I sow my crop today`() {
        val q = "Should I sow my crop today?"
        assertEquals(DomainBrain.FARMER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.FARMER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("SOWING:") || response.answer.contains("sow"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `F5 - What is the biggest weather risk to my crop`() {
        val q = "What is the biggest weather risk to my crop?"
        assertEquals(DomainBrain.FARMER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.FARMER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("TOP RISK:"))
        assertTrue(response.answer.contains("SEVERITY:"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // ========================================================================
    // Brain 3 — Researcher / Climate Questions
    // ========================================================================

    @Test
    fun `R1 - Is today temperature above normal`() {
        val q = "Is today's temperature above normal?"
        assertEquals(DomainBrain.RESEARCHER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.RESEARCHER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("Observed:") || response.answer.contains("observed"))
        assertTrue(response.answer.contains("Normal:") || response.answer.contains("normal"))
        assertTrue(response.answer.contains("Anomaly:") || response.answer.contains("anomaly"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `R2 - How much rainfall has occurred compared with normal`() {
        val q = "How much rainfall has occurred compared with normal?"
        assertEquals(DomainBrain.RESEARCHER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.RESEARCHER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("Observed rainfall:"))
        assertTrue(response.answer.contains("Normal rainfall:"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `R3 - Is there a heatwave condition`() {
        val q = "Is there a heatwave condition?"
        assertEquals(DomainBrain.RESEARCHER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.RESEARCHER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("HEATWAVE") || response.answer.contains("heatwave"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `R4 - Is rainfall increasing or decreasing`() {
        val q = "Is rainfall increasing or decreasing?"
        assertEquals(DomainBrain.RESEARCHER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.RESEARCHER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("Mann-Kendall") || response.answer.contains("trend") || response.answer.contains("Insufficient"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `R5 - How unusual is this rainfall event`() {
        val q = "How unusual is this rainfall event?"
        assertEquals(DomainBrain.RESEARCHER, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.RESEARCHER),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("Event rainfall:") || response.answer.contains("rainfall"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // ========================================================================
    // Brain 4 — Analyst / Hazard Questions
    // ========================================================================

    @Test
    fun `A1 - Is there a flood risk for Gwalior`() {
        val q = "Is there a flood risk for Gwalior?"
        assertEquals(DomainBrain.ANALYST, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.ANALYST),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("FLOOD RISK:"))
        assertTrue(response.answer.contains("Hazard:"))
        assertTrue(response.answer.contains("Exposure:"))
        assertTrue(response.answer.contains("Vulnerability:"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `A2 - Are there any severe weather alerts affecting my location`() {
        val q = "Are there any severe weather alerts affecting my location?"
        assertEquals(DomainBrain.ANALYST, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.ANALYST),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("OFFICIAL ALERT") || response.answer.contains("Official warning updates are unavailable in Offline Demo Mode."))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `A3 - Why is the risk high`() {
        val q = "Why is the risk high?"
        assertEquals(DomainBrain.ANALYST, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.ANALYST),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("RISK DRIVERS:") || response.answer.contains("Risk"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `A4 - Which risk should I worry about first`() {
        val q = "Which risk should I worry about first?"
        assertEquals(DomainBrain.ANALYST, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.ANALYST),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("PRIORITY #1"))
        assertTrue(response.answer.contains("SEVERITY:"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `A5 - What should I do if the weather changes suddenly`() {
        val q = "What should I do if the weather changes suddenly?"
        assertEquals(DomainBrain.ANALYST, OfflineDemoIntelligenceEngine.routeBrain(q, DomainBrain.AUTO))

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.ANALYST),
            cachedWeather = sampleGwaliorWeather,
            cachedForecast = sampleGwaliorForecast,
            cachedAlerts = sampleAlerts,
            farmerProfile = sampleFarmerProfile
        )

        assertTrue(response.answer.contains("CONTINGENCY DECISION") || response.answer.contains("CURRENT:"))
        assertTrue(response.answer.contains("IF"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    // ========================================================================
    // Honest Fallback / Data Limitation Verification (Zero Hallucination)
    // ========================================================================

    @Test
    fun `graceful data limitation when weather data is missing`() {
        val q = "What is the weather in Gwalior today?"
        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = ChatQuery(sessionId = "s1", query = q, languagePreference = ChatLanguage.ENGLISH, selectedBrain = DomainBrain.GENERAL),
            cachedWeather = null,
            cachedForecast = null,
            cachedAlerts = emptyList(),
            farmerProfile = null
        )

        assertTrue(response.answer.contains("DATA LIMITATION"))
        assertTrue(response.answer.contains("unavailable in local SQLite cache"))
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }
}
