package com.weathergpt.data.repository

import com.weathergpt.core.error.AppError
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.core.network.RetrofitClientFactory
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.local.InMemoryLocalWeatherDataSource
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import com.weathergpt.domain.model.weather.WeatherForecast
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.concurrent.TimeUnit

@OptIn(ExperimentalCoroutinesApi::class)
class WeatherFallbackRepositoryTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var localDataSource: InMemoryLocalWeatherDataSource
    private lateinit var repository: WeatherGPTRepositoryImpl
    private val testDispatcher = UnconfinedTestDispatcher()
    private var isOnline = true
    private var clockMillis = 1789036800000L

    private class TestNetworkMonitor(private val onlineProvider: () -> Boolean) : NetworkMonitor {
        override val networkState: Flow<NetworkState>
            get() = MutableStateFlow(if (onlineProvider()) NetworkState.Available else NetworkState.Unavailable)
        override val isOnline: Boolean
            get() = onlineProvider()
    }

    @Before
    fun setup() {
        com.weathergpt.core.config.AppConfig.setDemoMode(false)
        mockWebServer = MockWebServer()
        mockWebServer.start()

        isOnline = true
        clockMillis = 1789036800000L
        localDataSource = InMemoryLocalWeatherDataSource(timeProvider = { clockMillis })

        val okHttpClient = OkHttpClient.Builder()
            .connectTimeout(500, TimeUnit.MILLISECONDS)
            .readTimeout(500, TimeUnit.MILLISECONDS)
            .build()

        val retrofit = RetrofitClientFactory.createRetrofit(
            okHttpClient = okHttpClient,
            baseUrl = mockWebServer.url("/").toString()
        )
        val apiService = retrofit.create(WeatherGPTApiService::class.java)

        repository = WeatherGPTRepositoryImpl(
            apiService = apiService,
            ioDispatcher = testDispatcher,
            networkMonitor = TestNetworkMonitor { isOnline },
            localWeatherDataSource = localDataSource
        )
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
        com.weathergpt.core.config.AppConfig.resetToDefault()
    }

    private fun sampleCurrentWeatherJson(lat: Double, lon: Double, temp: Double = 33.2): String {
        return """
            {
                "location": {
                    "latitude": $lat,
                    "longitude": $lon
                },
                "observation_time": "2026-09-10T12:00:00Z",
                "temperature_c": $temp,
                "feels_like_c": 35.0,
                "relative_humidity_pct": 58.0,
                "precipitation_mm": 0.0,
                "rain_intensity_category": "None",
                "wind_speed_kmh": 12.0,
                "wind_direction_deg": 180.0,
                "surface_pressure_hpa": 1010.0,
                "weather_condition": "Clear",
                "provenance": {
                    "provider": "Open-Meteo",
                    "authority": "Operational Surface Observation",
                    "quality": "VERIFIED",
                    "retrieval_timestamp": "2026-09-10T12:00:00Z"
                }
            }
        """.trimIndent()
    }

    private fun sampleForecastJson(lat: Double, lon: Double): String {
        return """
            {
                "location": {
                    "latitude": $lat,
                    "longitude": $lon
                },
                "generated_at": "2026-09-10T12:00:00Z",
                "forecast_start": "2026-09-10T00:00:00Z",
                "forecast_end": "2026-09-13T00:00:00Z",
                "daily_forecast": [
                    {
                        "date": "2026-09-10",
                        "temp_max_c": 35.0,
                        "temp_min_c": 25.0,
                        "precipitation_sum_mm": 0.0,
                        "precipitation_probability_pct": 10.0,
                        "wind_speed_max_kmh": 15.0,
                        "dominant_condition": "Sunny"
                    }
                ],
                "hourly_forecast": [
                    {
                        "time": "2026-09-10T13:00:00Z",
                        "temperature_c": 34.0,
                        "relative_humidity_pct": 55.0,
                        "precipitation_mm": 0.0,
                        "precipitation_probability_pct": 5.0,
                        "wind_speed_kmh": 11.0,
                        "condition": "Sunny"
                    }
                ],
                "provenance": {
                    "provider": "Open-Meteo",
                    "authority": "Numerical Weather Prediction",
                    "quality": "VERIFIED"
                }
            }
        """.trimIndent()
    }

    // ========================================================================
    // 1. Online Success -> Returned as LIVE and Persisted to Cache
    // ========================================================================

    @Test
    fun `successful API response is returned as LIVE and persisted to cache`() = runTest(testDispatcher) {
        val lat = 25.4484
        val lon = 78.5685
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(lat, lon, temp = 31.5)))

        val result = repository.getCurrentWeather(lat, lon)

        assertTrue(result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals(WeatherDataSourceMode.LIVE, data.sourceMode)
        assertEquals("Open-Meteo", data.provider)
        assertEquals(31.5, data.temperatureC, 0.01)

        // Verify cache was primed
        val cached = localDataSource.getCachedCurrentWeather(lat, lon)
        assertNotNull("Local cache must be populated after successful API call", cached)
        assertEquals(31.5, cached!!.temperatureC, 0.01)
    }

    // ========================================================================
    // 2. API Failure Fallback to Real Cache -> Marked as DEMO_MODE
    // ========================================================================

    @Test
    fun `API 500 error falls back to cached REAL weather marked as DEMO_MODE`() = runTest(testDispatcher) {
        val lat = 25.4484
        val lon = 78.5685

        // Step 1: Prime cache with real API response
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(lat, lon, temp = 30.0)))
        val liveResult = repository.getCurrentWeather(lat, lon)
        assertTrue(liveResult is ResultState.Success)

        // Step 2: Simulate backend 500 Server Error
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody("Internal Server Error"))
        val fallbackResult = repository.getCurrentWeather(lat, lon)

        assertTrue("Must gracefully succeed using cache", fallbackResult is ResultState.Success)
        val cachedData = (fallbackResult as ResultState.Success).data
        assertEquals("Fallback must be labeled DEMO_MODE", WeatherDataSourceMode.DEMO_MODE, cachedData.sourceMode)
        assertEquals(30.0, cachedData.temperatureC, 0.01)
        assertEquals("Open-Meteo", cachedData.provider)
        assertNotNull(cachedData.retrievedAt)
    }

    @Test
    fun `network failure falls back to cached REAL weather marked as DEMO_MODE`() = runTest(testDispatcher) {
        val lat = 25.4484
        val lon = 78.5685

        // Prime cache
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(lat, lon, temp = 29.5)))
        repository.getCurrentWeather(lat, lon)

        // Simulate offline state
        isOnline = false
        val fallbackResult = repository.getCurrentWeather(lat, lon)

        assertTrue(fallbackResult is ResultState.Success)
        val data = (fallbackResult as ResultState.Success).data
        assertEquals(WeatherDataSourceMode.DEMO_MODE, data.sourceMode)
        assertEquals(29.5, data.temperatureC, 0.01)
    }

    @Test
    fun `API timeout falls back to cached REAL weather marked as DEMO_MODE`() = runTest(testDispatcher) {
        val lat = 25.4484
        val lon = 78.5685

        // Prime cache
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(lat, lon, temp = 33.0)))
        repository.getCurrentWeather(lat, lon)

        // Enqueue socket disconnect / timeout
        mockWebServer.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val fallbackResult = repository.getCurrentWeather(lat, lon)

        assertTrue(fallbackResult is ResultState.Success)
        val data = (fallbackResult as ResultState.Success).data
        assertEquals(WeatherDataSourceMode.DEMO_MODE, data.sourceMode)
        assertEquals(33.0, data.temperatureC, 0.01)
    }

    // ========================================================================
    // 3. No Cache Available -> Honest WeatherUnavailable Error
    // ========================================================================

    @Test
    fun `API failure with NO cached data returns honest WeatherUnavailable error`() = runTest(testDispatcher) {
        val lat = 19.0760
        val lon = 72.8777 // Location never cached

        mockWebServer.enqueue(MockResponse().setResponseCode(503).setBody("Service Unavailable"))
        val result = repository.getCurrentWeather(lat, lon)

        assertTrue("Must return error when neither live nor cached data is available", result is ResultState.Error)
        val err = (result as ResultState.Error).error
        assertTrue("Error must be WeatherUnavailable", err is AppError.WeatherUnavailable)
        assertTrue(err.message.contains("Live weather is temporarily unavailable", ignoreCase = true))
    }

    // ========================================================================
    // 4. Location Isolation (Delhi Cache Never Leaks to Mumbai)
    // ========================================================================

    @Test
    fun `location isolation ensures Delhi cache is not used for Mumbai during failure`() = runTest(testDispatcher) {
        val delhiLat = 28.6139
        val delhiLon = 77.2090
        val mumbaiLat = 19.0760
        val mumbaiLon = 72.8777

        // Prime Delhi cache
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(delhiLat, delhiLon, temp = 40.0)))
        repository.getCurrentWeather(delhiLat, delhiLon)

        // Mumbai fails without having been cached
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody("Server Error"))
        val mumbaiResult = repository.getCurrentWeather(mumbaiLat, mumbaiLon)

        assertTrue("Mumbai must fail honestly rather than using Delhi cache", mumbaiResult is ResultState.Error)
        assertTrue((mumbaiResult as ResultState.Error).error is AppError.WeatherUnavailable)
    }

    // ========================================================================
    // 5. Automatic Mode Switching (DEMO -> LIVE on Reconnect)
    // ========================================================================

    @Test
    fun `successful retry switches app from DEMO_MODE back to LIVE`() = runTest(testDispatcher) {
        val lat = 25.4484
        val lon = 78.5685

        // 1. Prime cache
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(lat, lon, temp = 30.0)))
        repository.getCurrentWeather(lat, lon)

        // 2. Server fails -> Drops to DEMO_MODE
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody("Server Down"))
        val demoResult = repository.getCurrentWeather(lat, lon)
        assertTrue(demoResult is ResultState.Success)
        assertEquals(WeatherDataSourceMode.DEMO_MODE, (demoResult as ResultState.Success).data.sourceMode)

        // 3. Server recovers -> Switches back to LIVE with fresh data
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleCurrentWeatherJson(lat, lon, temp = 32.0)))
        val liveAgain = repository.getCurrentWeather(lat, lon)
        assertTrue(liveAgain is ResultState.Success)
        val freshData = (liveAgain as ResultState.Success).data
        assertEquals("Must switch back to LIVE mode", WeatherDataSourceMode.LIVE, freshData.sourceMode)
        assertEquals(32.0, freshData.temperatureC, 0.01)
    }

    // ========================================================================
    // 6. Forecast Resilience
    // ========================================================================

    @Test
    fun `forecast failure falls back to cached real forecast with DEMO_MODE`() = runTest(testDispatcher) {
        val lat = 25.4484
        val lon = 78.5685

        // 1. Prime forecast cache
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(sampleForecastJson(lat, lon)))
        val liveForecast = repository.getWeatherForecast(lat, lon, days = 3, hourly = true)
        assertTrue(liveForecast is ResultState.Success)
        assertEquals(WeatherDataSourceMode.LIVE, (liveForecast as ResultState.Success).data.sourceMode)

        // 2. Simulate API timeout on next fetch
        mockWebServer.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START))
        val fallbackForecast = repository.getWeatherForecast(lat, lon, days = 3, hourly = true)

        assertTrue(fallbackForecast is ResultState.Success)
        val cached = (fallbackForecast as ResultState.Success).data
        assertEquals(WeatherDataSourceMode.DEMO_MODE, cached.sourceMode)
        assertEquals("2026-09-10T00:00:00Z", cached.forecastStart)
        assertEquals("2026-09-13T00:00:00Z", cached.forecastEnd)
        assertEquals("Open-Meteo", cached.provider)
    }
}
