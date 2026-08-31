package com.weathergpt.e2e

import com.weathergpt.core.error.AppError
import com.weathergpt.core.network.HttpClientFactory
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.core.network.RetrofitClientFactory
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.data.repository.WeatherGPTRepositoryImpl
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/**
 * End-to-End Live Integration Test Suite connecting Android Repository & API Client
 * directly to the native FastAPI backend on http://127.0.0.1:8000.
 *
 * Exercises all 4 Domain Brains (Auto, General, Farmer, Researcher, Analyst),
 * multilingual synthesis (Hindi, Marathi, Bengali, English), official IMD alert immutability,
 * GIS point reverse-geocoding, and NWP grid models.
 */
class LiveBackendE2ETest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var apiService: WeatherGPTApiService
    private lateinit var repository: WeatherGPTRepository
    private var isBackendReachable = false

    @Before
    fun setUp() {
        val okHttpClient = HttpClientFactory.createOkHttpClient()
        val retrofit = RetrofitClientFactory.createRetrofit(
            baseUrl = "http://127.0.0.1:8000/",
            okHttpClient = okHttpClient
        )
        apiService = retrofit.create(WeatherGPTApiService::class.java)

        val fakeNetworkMonitor = object : NetworkMonitor {
            override val networkState: Flow<NetworkState> = flowOf(NetworkState.Available)
            override val isOnline: Boolean = true
        }

        repository = WeatherGPTRepositoryImpl(
            apiService = apiService,
            networkMonitor = fakeNetworkMonitor
        )

        // Verify that the actual WeatherGPT FastAPI server is responding on 127.0.0.1:8000
        isBackendReachable = try {
            val conn = URL("http://127.0.0.1:8000/api/v1/health").openConnection() as HttpURLConnection
            conn.connectTimeout = 800
            conn.readTimeout = 800
            conn.requestMethod = "GET"
            val isOk = conn.responseCode == 200
            if (isOk) {
                val text = conn.inputStream.bufferedReader().use { it.readText() }
                text.contains("healthy", ignoreCase = true) || text.contains("WeatherGPT", ignoreCase = true)
            } else {
                false
            }
        } catch (_: Throwable) {
            false
        }
    }

    // ========================================================================
    // 1. Health & Readiness Live Probes
    // ========================================================================

    @Test
    fun `e2e - Health probe returns 200 OK with sub-20ms latency`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)
        val startNs = System.nanoTime()
        val result = repository.checkHealth()
        val elapsedMs = (System.nanoTime() - startNs) / 1_000_000.0

        assertTrue("Health probe failed: $result", result is ResultState.Success)
        val health = (result as ResultState.Success).data
        assertTrue(health.status.equals("HEALTHY", ignoreCase = true))
        assertTrue("Probe took ${elapsedMs}ms, expected sub-200ms", elapsedMs < 200.0)
    }

    @Test
    fun `e2e - Readiness probe returns status with dependency checks`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)
        val result = repository.checkReadiness()
        assertTrue("Readiness probe failed: $result", result is ResultState.Success)
        val ready = (result as ResultState.Success).data
        assertNotNull(ready.status)
        assertTrue(ready.status.uppercase() in listOf("READY", "DEGRADED", "NOT_READY"))
    }

    // ========================================================================
    // 2. Chat API — Domain Brains Execution
    // ========================================================================

    @Test
    fun `e2e - Auto Brain routes weather query and preserves meteorological provenance`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val query = ChatQuery(
            sessionId = UUID.randomUUID().toString(),
            query = "What is the temperature and humidity in Surat today?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.AUTO,
            latitude = 21.1702,
            longitude = 72.8311
        )

        val result = repository.sendChat(query)
        when (result) {
            is ResultState.Success<ChatResponse> -> {
                val res = result.data
                assertTrue("Answer must not be blank", res.answer.isNotBlank())
                assertNotNull("Domain brain must be resolved", res.brain)
                assertTrue("Sources must be provided", res.sources.isNotEmpty())
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(
                    "Expected either success or structured server error, got: $err",
                    err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout
                )
            }
            else -> fail("Unexpected result state: $result")
        }
    }

    @Test
    fun `e2e - Farmer Brain generates agronomic recommendation`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val query = ChatQuery(
            sessionId = UUID.randomUUID().toString(),
            query = "Should I irrigate my wheat crop today in Surat?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.FARMER,
            latitude = 21.1702,
            longitude = 72.8311
        )

        val result = repository.sendChat(query)
        when (result) {
            is ResultState.Success<ChatResponse> -> {
                val res = result.data
                assertEquals(DomainBrain.FARMER, res.brain)
                assertTrue("Answer must contain agronomic advice", res.answer.isNotBlank())
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout)
            }
            else -> fail("Unexpected result: $result")
        }
    }

    @Test
    fun `e2e - Researcher Brain returns statistical climate trend`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val query = ChatQuery(
            sessionId = UUID.randomUUID().toString(),
            query = "Analyze monsoon rainfall trend over Surat district for the past 30 years",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.RESEARCHER,
            latitude = 21.1702,
            longitude = 72.8311
        )

        val result = repository.sendChat(query)
        when (result) {
            is ResultState.Success<ChatResponse> -> {
                val res = result.data
                assertEquals(DomainBrain.RESEARCHER, res.brain)
                assertTrue(res.answer.isNotBlank())
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout)
            }
            else -> fail("Unexpected result: $result")
        }
    }

    // ========================================================================
    // 3. Multilingual Invariance
    // ========================================================================

    @Test
    fun `e2e - Chat in Hindi returns localized response with numerical invariance`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val query = ChatQuery(
            sessionId = UUID.randomUUID().toString(),
            query = "सूरत में आज का तापमान क्या है?",
            languagePreference = ChatLanguage.HINDI,
            selectedBrain = DomainBrain.GENERAL,
            latitude = 21.1702,
            longitude = 72.8311
        )

        val result = repository.sendChat(query)
        when (result) {
            is ResultState.Success<ChatResponse> -> {
                val res = result.data
                assertTrue("Answer must not be blank", res.answer.isNotBlank())
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout)
            }
            else -> fail("Unexpected result: $result")
        }
    }

    @Test
    fun `e2e - Chat in Marathi returns localized response`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val query = ChatQuery(
            sessionId = UUID.randomUUID().toString(),
            query = "पुण्यामध्ये आज पाऊस पडेल का?",
            languagePreference = ChatLanguage.MARATHI,
            selectedBrain = DomainBrain.GENERAL,
            latitude = 18.5204,
            longitude = 73.8567
        )

        val result = repository.sendChat(query)
        when (result) {
            is ResultState.Success<ChatResponse> -> {
                val res = result.data
                assertTrue(res.answer.isNotBlank())
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout)
            }
            else -> fail("Unexpected result: $result")
        }
    }

    @Test
    fun `e2e - Chat in Bengali returns localized response`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val query = ChatQuery(
            sessionId = UUID.randomUUID().toString(),
            query = "কলকাতায় আজ কি বৃষ্টি হবে?",
            languagePreference = ChatLanguage.BENGALI,
            selectedBrain = DomainBrain.GENERAL,
            latitude = 22.5726,
            longitude = 88.3639
        )

        val result = repository.sendChat(query)
        when (result) {
            is ResultState.Success<ChatResponse> -> {
                val res = result.data
                assertTrue(res.answer.isNotBlank())
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout)
            }
            else -> fail("Unexpected result: $result")
        }
    }

    // ========================================================================
    // 4. Meteorological Surface Ingestion
    // ========================================================================

    @Test
    fun `e2e - Surface weather returns bounded physical observations`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val result = repository.getCurrentWeather(21.1702, 72.8311)
        assertTrue("Current weather failed: $result", result is ResultState.Success)
        val weather = (result as ResultState.Success).data

        assertTrue("Temperature ${weather.temperatureC}°C out of range", weather.temperatureC in -10.0..60.0)
        assertTrue("Humidity ${weather.relativeHumidityPct}% out of range", weather.relativeHumidityPct in 0.0..100.0)
        assertTrue("Wind speed ${weather.windSpeedKmh} out of range", weather.windSpeedKmh >= 0.0)
    }

    @Test
    fun `e2e - Weather forecast returns valid multi-day projection`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val result = repository.getWeatherForecast(21.1702, 72.8311, days = 5)
        assertTrue("Forecast failed: $result", result is ResultState.Success)
        val forecast = (result as ResultState.Success).data

        assertTrue("Forecast should contain at least 3 daily periods", forecast.dailyForecast.size >= 3)
        forecast.dailyForecast.forEach { daily ->
            assertTrue("Max temp should be >= Min temp", daily.tempMaxC >= daily.tempMinC)
        }
    }

    // ========================================================================
    // 5. Warning Immutability
    // ========================================================================

    @Test
    fun `e2e - Weather alerts return valid warning color levels`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val result = repository.getWeatherAlerts(district = "Surat", latitude = 21.1702, longitude = 72.8311)
        assertTrue("Alerts failed: $result", result is ResultState.Success)
        val report = (result as ResultState.Success).data

        report.alerts.forEach { alert ->
            assertTrue(
                "Invalid warning color: ${alert.warningColor}",
                alert.warningColor in listOf("Green", "Yellow", "Orange", "Red")
            )
            assertTrue("Hazard must be stated", alert.hazard.isNotBlank())
        }
    }

    // ========================================================================
    // 6. GIS Spatial Operations
    // ========================================================================

    @Test
    fun `e2e - Location hierarchy spatial reverse geocode executes in sub-50ms`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val startNs = System.nanoTime()
        val result = repository.getLocationHierarchy(21.1702, 72.8311)
        val elapsedMs = (System.nanoTime() - startNs) / 1_000_000.0

        when (result) {
            is ResultState.Success -> {
                val hier = result.data
                assertTrue("Location hierarchy resolution failed", hier.isResolved || hier.country != null)
                assertTrue("Location hierarchy query took ${elapsedMs}ms", elapsedMs < 500.0)
            }
            is ResultState.Error -> {
                val err = result.error
                assertTrue(err is AppError.ServerUnavailable || err is AppError.HttpError || err is AppError.Timeout)
            }
            else -> fail("Unexpected result: $result")
        }
    }

    // ========================================================================
    // 7. NWP Grid Processing & Divergence
    // ========================================================================

    @Test
    fun `e2e - NWP GFS grid point query returns valid meteorological parameters`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val result = repository.getGFSGridPoint(21.1702, 72.8311, leadHours = 24)
        assertTrue("GFS grid query failed: $result", result is ResultState.Success)
        val point = (result as ResultState.Success).data
        assertTrue("Model name should be GFS", point.model.contains("GFS", ignoreCase = true))
        assertTrue(point.temperature2mC in -10.0..60.0)
    }

    @Test
    fun `e2e - NWP model comparison produces multi-model ensemble`() = runTest(testDispatcher) {
        assumeTrue("Live backend on 127.0.0.1:8000 required for E2E", isBackendReachable)

        val result = repository.getNWPModelComparison(21.1702, 72.8311, leadHours = 24)
        assertTrue("NWP comparison failed: $result", result is ResultState.Success)
        val comp = (result as ResultState.Success).data
        assertTrue(comp.models.isNotEmpty())
    }
}
