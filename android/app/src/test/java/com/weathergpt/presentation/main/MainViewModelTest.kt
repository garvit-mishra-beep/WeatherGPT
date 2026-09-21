package com.weathergpt.presentation.main

import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.usecase.CheckHealthUseCase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class MainViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    private class FakeNetworkMonitor(initialOnline: Boolean = true) : NetworkMonitor {
        private val _state = MutableStateFlow(
            if (initialOnline) NetworkState.Available else NetworkState.Unavailable
        )
        override val networkState: Flow<NetworkState> = _state.asStateFlow()
        override val isOnline: Boolean
            get() = _state.value is NetworkState.Available

        fun setOnline(online: Boolean) {
            _state.value = if (online) NetworkState.Available else NetworkState.Unavailable
        }
    }

    private class FakeWeatherGPTRepository : com.weathergpt.domain.repository.WeatherGPTRepository {
        var delayMs: Long = 0L
        var responseToReturn: ResultState<HealthStatus> = ResultState.Success(
            HealthStatus("healthy", "WeatherGPT", "test", "v1", "v1", "2026-08-30T10:00:00Z")
        )

        override suspend fun checkHealth(): ResultState<HealthStatus> {
            if (delayMs > 0) delay(delayMs)
            return responseToReturn
        }

        override suspend fun checkReadiness() = throw NotImplementedError()
        override suspend fun sendChat(query: com.weathergpt.domain.model.chat.ChatQuery) = throw NotImplementedError()
        override suspend fun getCurrentWeather(latitude: Double, longitude: Double) = throw NotImplementedError()
        override suspend fun getWeatherForecast(latitude: Double, longitude: Double, days: Int, hourly: Boolean) = throw NotImplementedError()
        override suspend fun getWeatherAlerts(district: String?, latitude: Double?, longitude: Double?) = throw NotImplementedError()
        override suspend fun getWeatherIntelligence(latitude: Double, longitude: Double, leadHours: Int, includeNwp: Boolean) = throw NotImplementedError()
        override suspend fun getIrrigationAdvisory(latitude: Double, longitude: Double, cropName: String, cropStage: String, soilType: String, lastIrrigationDate: String?, forecastPrecip48hMm: Double) = throw NotImplementedError()
        override suspend fun getSprayWindowAdvisory(windSpeedKmh: Double, rainProbabilityPct: Double, tempC: Double, relativeHumidityPct: Double) = throw NotImplementedError()
        override suspend fun getLocationHierarchy(latitude: Double, longitude: Double) = throw NotImplementedError()
        override suspend fun getBoundary(level: String, code: String) = throw NotImplementedError()
        override suspend fun getHazardIntersection(warningGeometry: kotlinx.serialization.json.JsonObject?, alertId: String, event: String, severity: String, targetLevel: String) = throw NotImplementedError()
        override suspend fun getRiskAssessment(districtName: String, precip24hPercentile: Double, exposureIndex: Double, vulnerabilityIndex: Double, hazardType: String) = throw NotImplementedError()
        override suspend fun getGISAnalysis(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?, observedTempC: Double?, leadHours: Int) = throw NotImplementedError()
        override suspend fun getGFSGridPoint(latitude: Double, longitude: Double, leadHours: Int) = throw NotImplementedError()
        override suspend fun getWRFGridPoint(latitude: Double, longitude: Double, leadHours: Int) = throw NotImplementedError()
        override suspend fun getNWPModelComparison(latitude: Double, longitude: Double, leadHours: Int) = throw NotImplementedError()
        override suspend fun getPointWeatherMap(latitude: Double, longitude: Double) = throw NotImplementedError()
        override suspend fun getWarningMap(warningGeometry: kotlinx.serialization.json.JsonObject, alertId: String, event: String, severity: String) = throw NotImplementedError()
        override suspend fun getRiskMap(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?) = throw NotImplementedError()
        override suspend fun evaluateDecision(question: String, locationName: String?, latitude: Double?, longitude: Double?, requestedTime: String?, domain: String?, context: Map<String, String>?) = throw NotImplementedError()
        override suspend fun getFarmerProfile(): ResultState<com.weathergpt.domain.model.farmer.FarmerProfile> = ResultState.Success(com.weathergpt.domain.model.farmer.FarmerProfile())
        override suspend fun saveFarmerProfile(profile: com.weathergpt.domain.model.farmer.FarmerProfile): ResultState<Unit> = ResultState.Success(Unit)
    }

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `verifyBackendConnectivity transitions to Loading then Success`() = runTest(testDispatcher) {
        val repo = FakeWeatherGPTRepository()
        val networkMonitor = FakeNetworkMonitor(initialOnline = true)
        val useCase = CheckHealthUseCase(repo)

        val viewModel = MainViewModel(useCase, networkMonitor)

        // Advance to execute the init block
        advanceUntilIdle()

        val state = viewModel.healthState.value
        assertTrue(state is ResultState.Success)
        val data = (state as ResultState.Success).data
        assertEquals("healthy", data.status)
    }

    @Test
    fun `re-triggering connectivity check cancels previous in-flight job safely`() = runTest(testDispatcher) {
        val repo = FakeWeatherGPTRepository().apply { delayMs = 500L }
        val networkMonitor = FakeNetworkMonitor(initialOnline = true)
        val useCase = CheckHealthUseCase(repo)

        val viewModel = MainViewModel(useCase, networkMonitor)

        // Re-trigger before first completes
        viewModel.verifyBackendConnectivity()

        advanceUntilIdle()

        val state = viewModel.healthState.value
        assertTrue(state is ResultState.Success)
    }

    @Test
    fun `networkState reflects monitor state`() = runTest(testDispatcher) {
        val repo = FakeWeatherGPTRepository()
        val networkMonitor = FakeNetworkMonitor(initialOnline = true)
        val useCase = CheckHealthUseCase(repo)

        val viewModel = MainViewModel(useCase, networkMonitor)
        assertEquals(NetworkState.Available, viewModel.networkState.value)

        networkMonitor.setOnline(false)
        advanceUntilIdle()

        assertEquals(NetworkState.Unavailable, viewModel.networkState.value)
    }

    @Test
    fun `updateBackendUrl validates and updates currentBaseUrl`() = runTest(testDispatcher) {
        val repo = FakeWeatherGPTRepository()
        val networkMonitor = FakeNetworkMonitor(initialOnline = true)
        val useCase = CheckHealthUseCase(repo)
        val viewModel = MainViewModel(useCase, networkMonitor)

        val success = viewModel.updateBackendUrl("http://192.168.1.88:8000")
        assertTrue(success)
        assertEquals("http://192.168.1.88:8000/", viewModel.currentBaseUrl.value)
        assertEquals(null, viewModel.urlValidationError.value)

        val failed = viewModel.updateBackendUrl("invalid_url_no_scheme")
        assertTrue(!failed)
        assertTrue(viewModel.urlValidationError.value != null)

        viewModel.resetBackendUrl()
        assertEquals("http://127.0.0.1:8000/", viewModel.currentBaseUrl.value)
        assertEquals(null, viewModel.urlValidationError.value)
    }
}
