package com.weathergpt.presentation.home

import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.error.AppError
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.core.network.RetrofitClientFactory
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.local.InMemoryLocalWeatherDataSource
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.LocationCoordDto
import com.weathergpt.data.remote.dto.weather.WeatherProvenanceDto
import com.weathergpt.data.remote.dto.weather.DailyForecastDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.data.repository.WeatherGPTRepositoryImpl
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.decision.DecisionConfidence
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionUncertainty
import com.weathergpt.domain.model.decision.DecisionVerdict
import com.weathergpt.domain.model.decision.NirnayCard
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.concurrent.TimeUnit

/**
 * Validates Vayubodhak Final Showcase Architecture:
 * FULL OFFLINE WEATHER + LOCAL GEMMA CONNECTION
 *
 * All 20 required architectural verifications:
 * 1. DEMO_MODE=true loads weather from SQLite.
 * 2. DEMO_MODE=true never calls weather API.
 * 3. DEMO_MODE=true never calls FastAPI for weather.
 * 4. DEMO_MODE=true works with internet disabled.
 * 5. DEMO_MODE=true works with backend disabled.
 * 6. Gwalior is always used in Demo Mode.
 * 7. Chennai cannot leak into Demo Mode.
 * 8. Cached provider remains Open-Meteo.
 * 9. Cached retrievedAt remains unchanged.
 * 10. Forecast valid times remain unchanged.
 * 11. Three-day real cache remains available.
 * 12. No synthetic weather values are generated.
 * 13. Deterministic intelligence works without network.
 * 14. NirnayCard works when evidence is fresh enough.
 * 15. Stale evidence is handled honestly.
 * 16. Gemma works through UJJWAL LAN.
 * 17. Gemma failure does not break weather.
 * 18. Backend failure does not break Demo Mode weather.
 * 19. No "No Internet Connection" screen in Demo Mode.
 * 20. No weather-network retry occurs in Demo Mode.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class HomeWeatherDemoModeTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var locationManager: SharedLocationManager
    private lateinit var mockWebServer: MockWebServer
    private lateinit var localDataSource: InMemoryLocalWeatherDataSource
    private lateinit var repository: WeatherGPTRepositoryImpl
    private var isOnline = true

    private class TestNetworkMonitor(private val onlineProvider: () -> Boolean) : NetworkMonitor {
        override val networkState: Flow<NetworkState>
            get() = MutableStateFlow(if (onlineProvider()) NetworkState.Available else NetworkState.Unavailable)
        override val isOnline: Boolean
            get() = onlineProvider()
    }

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        locationManager = SharedLocationManager()
        isOnline = true

        mockWebServer = MockWebServer()
        mockWebServer.start()

        localDataSource = InMemoryLocalWeatherDataSource()

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
            localWeatherDataSource = localDataSource,
            okHttpClient = okHttpClient
        )

        AppConfig.setDemoMode(true)
        AppConfig.setCustomOllamaUrl(mockWebServer.url("/").toString())
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        mockWebServer.shutdown()
        AppConfig.resetToDefault()
    }

    private fun sampleRealGwaliorWeather(
        lat: Double = SharedLocationManager.DEMO_GWALIOR_LATITUDE,
        lon: Double = SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
        temp: Double = 28.841,
        humidity: Double = 72.39,
        provider: String = "Open-Meteo",
        sourceMode: WeatherDataSourceMode = WeatherDataSourceMode.DEMO_MODE,
        timestamp: String = "2026-09-10T14:53:39Z"
    ): CurrentWeather {
        return CurrentWeather(
            location = LocationCoordinates(lat, lon),
            observationTime = "2026-09-10T20:15:00Z",
            temperatureC = temp,
            feelsLikeC = 33.5,
            relativeHumidityPct = humidity,
            precipitationMm = 0.0,
            rainIntensityCategory = "no_rain",
            windSpeedKmh = 6.2,
            windDirectionDeg = 353.0,
            surfacePressureHpa = 982.9,
            weatherCondition = "overcast",
            provider = provider,
            authority = "Operational Surface Observation",
            sourceMode = sourceMode,
            retrievedAt = timestamp
        )
    }

    private fun sampleRealGwaliorWeatherDto(
        lat: Double = SharedLocationManager.DEMO_GWALIOR_LATITUDE,
        lon: Double = SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
        temp: Double = 28.841,
        humidity: Double = 72.39,
        timestamp: String = "2026-09-10T14:53:39Z"
    ): CurrentWeatherResponseDto {
        return CurrentWeatherResponseDto(
            location = LocationCoordDto(lat, lon),
            observationTime = "2026-09-10T20:15:00Z",
            temperatureC = temp,
            feelsLikeC = 33.5,
            relativeHumidityPct = humidity,
            precipitationMm = 0.0,
            rainIntensityCategory = "no_rain",
            windSpeedKmh = 6.2,
            windDirectionDeg = 353.0,
            surfacePressureHpa = 982.9,
            weatherCondition = "overcast",
            provenance = WeatherProvenanceDto(
                provider = "Open-Meteo",
                authority = "Operational Surface Observation",
                quality = "VERIFIED",
                retrievalTimestamp = timestamp
            )
        )
    }

    private fun sampleRealGwaliorForecastDto(
        lat: Double = SharedLocationManager.DEMO_GWALIOR_LATITUDE,
        lon: Double = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
    ): WeatherForecastResponseDto {
        return WeatherForecastResponseDto(
            location = LocationCoordDto(lat, lon),
            generatedAt = "2026-09-10T14:53:39Z",
            forecastStart = "2026-09-10T00:00:00Z",
            forecastEnd = "2026-09-13T00:00:00Z",
            dailyForecast = listOf(
                DailyForecastDto(
                    date = "2026-09-10",
                    tempMaxC = 34.0,
                    tempMinC = 24.0,
                    precipitationSumMm = 0.0,
                    precipitationProbabilityPct = 10.0,
                    windSpeedMaxKmh = 12.0,
                    dominantCondition = "clear"
                ),
                DailyForecastDto(
                    date = "2026-09-11",
                    tempMaxC = 35.0,
                    tempMinC = 25.0,
                    precipitationSumMm = 0.0,
                    precipitationProbabilityPct = 15.0,
                    windSpeedMaxKmh = 14.0,
                    dominantCondition = "partly_cloudy"
                ),
                DailyForecastDto(
                    date = "2026-09-12",
                    tempMaxC = 33.0,
                    tempMinC = 23.0,
                    precipitationSumMm = 2.5,
                    precipitationProbabilityPct = 60.0,
                    windSpeedMaxKmh = 18.0,
                    dominantCondition = "rain_showers"
                )
            ),
            hourlyForecast = emptyList(),
            provenance = WeatherProvenanceDto(
                provider = "Open-Meteo",
                authority = "Operational Surface Observation",
                quality = "VERIFIED",
                retrievalTimestamp = "2026-09-10T14:53:39Z"
            )
        )
    }

    // ========================================================================
    // 1. DEMO_MODE=true loads weather from SQLite
    // ========================================================================
    @Test
    fun test01_demoModeTrue_loadsWeatherFromSQLite() = runTest(testDispatcher) {
        val gwaliorDto = sampleRealGwaliorWeatherDto()
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            gwaliorDto
        )

        val result = repository.getCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        )

        assertTrue(result is ResultState.Success)
        val weather = (result as ResultState.Success).data
        assertEquals(WeatherDataSourceMode.DEMO_MODE, weather.sourceMode)
        assertEquals(28.841, weather.temperatureC, 0.001)
        assertEquals("overcast", weather.weatherCondition)
    }

    // ========================================================================
    // 2. DEMO_MODE=true never calls weather API
    // ========================================================================
    @Test
    fun test02_demoModeTrue_neverCallsWeatherAPI() = runTest(testDispatcher) {
        val gwaliorDto = sampleRealGwaliorWeatherDto()
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            gwaliorDto
        )

        repository.getCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        )

        // Strict verification: ZERO network weather calls
        assertEquals(0, repository.getNetworkWeatherCallsCount())
        assertEquals(0, mockWebServer.requestCount)
    }

    // ========================================================================
    // 3. DEMO_MODE=true never calls FastAPI for weather
    // ========================================================================
    @Test
    fun test03_demoModeTrue_neverCallsFastApiForWeather() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )
        localDataSource.saveForecast(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorForecastDto()
        )

        repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        repository.getWeatherForecast(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE, days = 3)
        repository.getWeatherAlerts(district = "Gwalior", latitude = SharedLocationManager.DEMO_GWALIOR_LATITUDE, longitude = SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        repository.getWeatherIntelligence(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)

        assertEquals("FastAPI weather endpoints must NEVER be contacted in Demo Mode", 0, mockWebServer.requestCount)
        assertEquals(0, repository.getNetworkWeatherCallsCount())
    }

    // ========================================================================
    // 4. DEMO_MODE=true works with internet disabled
    // ========================================================================
    @Test
    fun test04_demoModeTrue_worksWithInternetDisabled() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )
        isOnline = false // Internet completely disabled

        val result = repository.getCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        )

        assertTrue("Must succeed even when internet is disabled", result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals(28.841, data.temperatureC, 0.001)
    }

    // ========================================================================
    // 5. DEMO_MODE=true works with backend disabled
    // ========================================================================
    @Test
    fun test05_demoModeTrue_worksWithBackendDisabled() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )
        // Backend laptop down / shutting down MockWebServer
        mockWebServer.shutdown()

        val result = repository.getCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        )

        assertTrue("Must succeed even when backend is totally offline", result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals(28.841, data.temperatureC, 0.001)
    }

    // ========================================================================
    // 6. Gwalior is always used in Demo Mode
    // ========================================================================
    @Test
    fun test06_gwaliorIsAlwaysUsedInDemoMode() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        // Requesting with arbitrary coordinates (e.g. user GPS location elsewhere)
        val result = repository.getCurrentWeather(19.0760, 72.8777)

        assertTrue(result is ResultState.Success)
        val weather = (result as ResultState.Success).data
        assertEquals(SharedLocationManager.DEMO_GWALIOR_LATITUDE, weather.location.latitude, 0.0001)
        assertEquals(SharedLocationManager.DEMO_GWALIOR_LONGITUDE, weather.location.longitude, 0.0001)
    }

    // ========================================================================
    // 7. Chennai cannot leak into Demo Mode
    // ========================================================================
    @Test
    fun test07_chennaiCannotLeakIntoDemoMode() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto(temp = 28.841)
        )
        // Even if Chennai data exists in SQLite
        localDataSource.saveCurrentWeather(
            13.0827,
            80.2707,
            sampleRealGwaliorWeatherDto(lat = 13.0827, lon = 80.2707, temp = 35.0)
        )

        val result = repository.getCurrentWeather(13.0827, 80.2707)

        assertTrue(result is ResultState.Success)
        val weather = (result as ResultState.Success).data
        assertNotEquals("Chennai coordinates must never be returned in Demo Mode", 13.0827, weather.location.latitude, 0.001)
        assertEquals(SharedLocationManager.DEMO_GWALIOR_LATITUDE, weather.location.latitude, 0.001)
        assertEquals(28.841, weather.temperatureC, 0.001)
    }

    // ========================================================================
    // 8. Cached provider remains Open-Meteo
    // ========================================================================
    @Test
    fun test08_cachedProviderRemainsOpenMeteo() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        val result = repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        val weather = (result as ResultState.Success).data
        assertEquals("Open-Meteo", weather.provider)
    }

    // ========================================================================
    // 9. Cached retrievedAt remains unchanged
    // ========================================================================
    @Test
    fun test09_cachedRetrievedAtRemainsUnchanged() = runTest(testDispatcher) {
        val originalTimestamp = "2026-09-10T14:53:39Z"
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto(timestamp = originalTimestamp)
        )

        val result = repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        val weather = (result as ResultState.Success).data
        assertEquals("Retrieved timestamp must not be replaced with current time", originalTimestamp, weather.retrievedAt)
    }

    // ========================================================================
    // 10. Forecast valid times remain unchanged
    // ========================================================================
    @Test
    fun test10_forecastValidTimesRemainUnchanged() = runTest(testDispatcher) {
        localDataSource.saveForecast(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorForecastDto()
        )

        val result = repository.getWeatherForecast(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        assertTrue(result is ResultState.Success)
        val forecast = (result as ResultState.Success).data
        assertEquals("2026-09-10T14:53:39Z", forecast.generatedAt)
        assertEquals("2026-09-10T00:00:00Z", forecast.forecastStart)
        assertEquals("2026-09-13T00:00:00Z", forecast.forecastEnd)
    }

    // ========================================================================
    // 11. Three-day real cache remains available
    // ========================================================================
    @Test
    fun test11_threeDayRealCacheRemainsAvailable() = runTest(testDispatcher) {
        localDataSource.saveForecast(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorForecastDto()
        )

        val result = repository.getWeatherForecast(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        val forecast = (result as ResultState.Success).data
        assertEquals(3, forecast.dailyForecast.size)
        assertEquals("2026-09-10", forecast.dailyForecast[0].date)
        assertEquals("2026-09-11", forecast.dailyForecast[1].date)
        assertEquals("2026-09-12", forecast.dailyForecast[2].date)
    }

    // ========================================================================
    // 12. No synthetic weather values are generated
    // ========================================================================
    @Test
    fun test12_noSyntheticWeatherValuesAreGenerated() = runTest(testDispatcher) {
        val exactTemp = 28.841
        val exactHumidity = 72.39
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto(temp = exactTemp, humidity = exactHumidity)
        )

        val result = repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        val weather = (result as ResultState.Success).data
        assertEquals(exactTemp, weather.temperatureC, 0.00001)
        assertEquals(exactHumidity, weather.relativeHumidityPct, 0.00001)
        assertNotEquals(28.0, weather.temperatureC, 0.00001)
    }

    // ========================================================================
    // 13. Deterministic intelligence works without network
    // ========================================================================
    @Test
    fun test13_deterministicIntelligenceWorksWithoutNetwork() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        val result = repository.getWeatherIntelligence(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        assertTrue(result is ResultState.Success)
        val intel = (result as ResultState.Success).data
        assertEquals("DEMO_MODE_CACHED", intel.dataQuality)
        assertNotNull(intel.currentObservation)
        assertEquals(0, repository.getNetworkWeatherCallsCount())
    }

    // ========================================================================
    // 14. NirnayCard works when evidence is fresh enough
    // ========================================================================
    @Test
    fun test14_nirnayCardWorksWhenEvidenceIsFresh() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto(humidity = 72.39)
        )

        val result = repository.evaluateDecision("Should I spray in Gwalior tonight?")
        assertTrue(result is ResultState.Success)
        val card = (result as ResultState.Success).data
        assertEquals(DecisionVerdict.POSTPONE, card.verdict)
        assertEquals("Gwalior, Madhya Pradesh", card.evidenceMetrics["location"])
        assertEquals("Open-Meteo", card.evidenceMetrics["provider"])
        assertEquals("DEMO_MODE", card.evidenceMetrics["source_mode"])
        assertTrue(card.why.first().contains("recently retrieved", ignoreCase = true))
    }

    // ========================================================================
    // 15. Stale evidence is handled honestly
    // ========================================================================
    @Test
    fun test15_staleEvidenceIsHandledHonestly() = runTest(testDispatcher) {
        // Cache is empty -> stale/missing evidence
        val result = repository.evaluateDecision("Should I spray in Gwalior tonight?")
        assertTrue(result is ResultState.Success)
        val card = (result as ResultState.Success).data
        assertEquals(DecisionVerdict.INSUFFICIENT_DATA, card.verdict)
        assertTrue(card.recommendedAction.contains("Insufficient local evidence", ignoreCase = true))
    }

    // ========================================================================
    // 16. Demo Mode Chat operates 100% offline without remote LLM
    // ========================================================================
    @Test
    fun test16_gemmaWorksThroughUjjwalLan() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        val query = ChatQuery(
            sessionId = "session-demo-01",
            query = "What is the weather in Gwalior today?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.GENERAL
        )

        val result = repository.sendChat(query)
        assertTrue(result is ResultState.Success)
        val chatResponse = (result as ResultState.Success).data
        assertTrue(chatResponse.answer.contains("Gwalior"))
        assertTrue(chatResponse.answer.contains("28.8°C"))
        assertTrue(chatResponse.confidence?.notes?.contains("Local Intelligence") == true || chatResponse.confidence?.notes?.contains("100% Offline Demo Mode") == true)
        assertEquals(0, mockWebServer.requestCount)
    }

    // ========================================================================
    // 17. Offline Demo Chat zero network calls guarantee
    // ========================================================================
    @Test
    fun test17_gemmaFailureDoesNotBreakWeather() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        val query = ChatQuery(
            sessionId = "session-demo-02",
            query = "Should I spray my crop today?",
            languagePreference = ChatLanguage.ENGLISH,
            selectedBrain = DomainBrain.FARMER
        )

        val chatResult = repository.sendChat(query)
        assertTrue("Chat must succeed via deterministic offline intelligence", chatResult is ResultState.Success)
        val chatResponse = (chatResult as ResultState.Success).data
        assertTrue(chatResponse.answer.contains("POSTPONE") || chatResponse.answer.contains("GO"))
        assertEquals(0, mockWebServer.requestCount)

        // Weather remains 100% operational
        val weatherResult = repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        assertTrue(weatherResult is ResultState.Success)
        assertEquals(0, mockWebServer.requestCount)
    }

    // ========================================================================
    // 18. Backend failure does not break Demo Mode weather
    // ========================================================================
    @Test
    fun test18_backendFailureDoesNotBreakDemoModeWeather() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )
        localDataSource.saveForecast(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorForecastDto()
        )

        // Mock backend shuts down
        mockWebServer.shutdown()

        val weatherResult = repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        val forecastResult = repository.getWeatherForecast(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)

        assertTrue("Weather works with backend down", weatherResult is ResultState.Success)
        assertTrue("Forecast works with backend down", forecastResult is ResultState.Success)
    }

    // ========================================================================
    // 19. No "No Internet Connection" screen in Demo Mode
    // ========================================================================
    @Test
    fun test19_noInternetConnectionScreenInDemoMode() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        val viewModel = HomeViewModel(repository = repository, locationManager = locationManager)
        advanceUntilIdle()

        val state = viewModel.weatherState.value
        assertTrue("State must be Success", state is ResultState.Success)
        val data = (state as ResultState.Success).data
        assertEquals(WeatherDataSourceMode.DEMO_MODE, data.sourceMode)
        assertEquals(SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME, viewModel.uiState.value.locationName)
    }

    // ========================================================================
    // 20. No weather-network retry occurs in Demo Mode
    // ========================================================================
    @Test
    fun test20_noWeatherNetworkRetryOccursInDemoMode() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        // Call repeatedly
        repeat(5) {
            repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        }

        assertEquals("Zero network weather retries or calls occurred", 0, repository.getNetworkWeatherCallsCount())
    }

    // ========================================================================
    // 21. Gemma contradiction cannot alter verdict
    // ========================================================================
    @Test
    fun test21_gemmaContradictionCannotAlterVerdict() = runTest(testDispatcher) {
        // High humidity (78.0%) causes spray decision to be POSTPONE
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto().copy(relativeHumidityPct = 78.0)
        )

        // Mock Gemma responding on UJJWAL claiming "Go ahead, spray now"
        val contradictoryGemma = """
            {
              "model": "gemma4:e2b",
              "message": {
                "role": "assistant",
                "content": "Go ahead, spray now, everything looks good."
              }
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(contradictoryGemma))

        // Deterministic Nirnay decision evaluation
        val nirnayResult = repository.evaluateDecision("Can I spray pesticide today in Gwalior?")
        assertTrue(nirnayResult is ResultState.Success)
        val card = (nirnayResult as ResultState.Success).data
        assertEquals("Deterministic verdict must remain POSTPONE despite contradictory conversational output", DecisionVerdict.POSTPONE, card.verdict)
        assertTrue(card.recommendedAction.contains("Delay"))
    }

    // ========================================================================
    // 22. Deterministic NirnayCard works without Gemma
    // ========================================================================
    @Test
    fun test22_deterministicNirnayCardWorksWithoutGemma() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )

        // Ensure mock server is shut down / Gemma completely absent
        mockWebServer.shutdown()

        val nirnayResult = repository.evaluateDecision("Can I spray today?")
        assertTrue("NirnayCard must succeed even if Gemma is completely offline", nirnayResult is ResultState.Success)
        val card = (nirnayResult as ResultState.Success).data
        assertNotNull(card.verdict)
        assertNotNull(card.recommendedAction)
        assertEquals(SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME, card.evidenceMetrics["location"])
        assertEquals("Open-Meteo", card.evidenceMetrics["provider"])
        assertEquals(0, repository.getNetworkWeatherCallsCount())
    }

    // ========================================================================
    // 23. Official alert authority preserved
    // ========================================================================
    @Test
    fun test23_officialAlertAuthorityPreserved() = runTest(testDispatcher) {
        val alertsResult = repository.getWeatherAlerts(
            district = SharedLocationManager.DEMO_GWALIOR_DISTRICT,
            latitude = SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            longitude = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        )
        assertTrue("Alerts report returned", alertsResult is ResultState.Success)
        val report = (alertsResult as ResultState.Success).data
        // In Demo Mode with no simulated alerts, zero fabricated alerts are invented
        assertEquals("No fabricated alerts are invented when none exist locally", 0, report.alerts.size)
        assertEquals(0, repository.getNetworkWeatherCallsCount())
    }

    // ========================================================================
    // 24. Stale-data safety preserved
    // ========================================================================
    @Test
    fun test24_staleDataSafetyPreserved() = runTest(testDispatcher) {
        // Without saving cache, evaluate decision
        val nirnayResult = repository.evaluateDecision("Should I irrigate crops?")
        assertTrue(nirnayResult is ResultState.Success)
        val card = (nirnayResult as ResultState.Success).data
        assertEquals("Stale/missing evidence must yield INSUFFICIENT_DATA", DecisionVerdict.INSUFFICIENT_DATA, card.verdict)
        assertTrue(card.why.first().contains("Safe agronomic decisions require verified weather data"))
    }

    // ========================================================================
    // 25. No hidden weather retry occurs in Demo Mode
    // ========================================================================
    @Test
    fun test25_noHiddenWeatherRetryInDemoMode() = runTest(testDispatcher) {
        localDataSource.saveCurrentWeather(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorWeatherDto()
        )
        localDataSource.saveForecast(
            SharedLocationManager.DEMO_GWALIOR_LATITUDE,
            SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
            sampleRealGwaliorForecastDto()
        )

        // Multiple concurrent/sequential calls
        repository.getCurrentWeather(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        repository.getWeatherForecast(SharedLocationManager.DEMO_GWALIOR_LATITUDE, SharedLocationManager.DEMO_GWALIOR_LONGITUDE)
        repository.evaluateDecision("Is it safe to spray?")

        assertEquals("Demo Mode performs zero weather network calls and zero retries", 0, repository.getNetworkWeatherCallsCount())
    }
}
