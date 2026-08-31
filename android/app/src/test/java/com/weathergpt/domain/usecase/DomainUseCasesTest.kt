package com.weathergpt.domain.usecase

import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.farmer.CropWaterBalanceMetrics
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DomainUseCasesTest {

    private class FakeWeatherGPTRepository : WeatherGPTRepository {
        override suspend fun checkHealth() = throw NotImplementedError()
        override suspend fun checkReadiness() = throw NotImplementedError()

        override suspend fun sendChat(query: ChatQuery): ResultState<ChatResponse> {
            return ResultState.Success(
                ChatResponse(
                    responseId = "resp_uc_1",
                    sessionId = query.sessionId,
                    brain = query.selectedBrain,
                    language = "hi",
                    createdAt = "2026-08-30T10:00:00Z",
                    summary = "फसल सलाह",
                    answer = "विस्तृत उत्तर",
                    data = null,
                    recommendation = null,
                    alert = null,
                    visualizations = emptyList(),
                    sources = emptyList(),
                    confidence = null,
                    limitations = emptyList()
                )
            )
        }

        override suspend fun getCurrentWeather(latitude: Double, longitude: Double): ResultState<CurrentWeather> {
            return ResultState.Success(
                CurrentWeather(
                    location = LocationCoordinates(latitude, longitude),
                    observationTime = "2026-08-30T10:00:00Z",
                    temperatureC = 29.5,
                    feelsLikeC = 34.0,
                    relativeHumidityPct = 75.0,
                    precipitationMm = 0.0,
                    rainIntensityCategory = "none",
                    windSpeedKmh = 10.0,
                    windDirectionDeg = 180.0,
                    surfacePressureHpa = 1010.0,
                    weatherCondition = "Clear",
                    provider = "open_meteo",
                    authority = "WMO"
                )
            )
        }

        override suspend fun getWeatherForecast(latitude: Double, longitude: Double, days: Int, hourly: Boolean) = throw NotImplementedError()
        override suspend fun getWeatherAlerts(district: String?, latitude: Double?, longitude: Double?) = throw NotImplementedError()
        override suspend fun getWeatherIntelligence(latitude: Double, longitude: Double, leadHours: Int, includeNwp: Boolean) = throw NotImplementedError()

        override suspend fun getIrrigationAdvisory(
            latitude: Double,
            longitude: Double,
            cropName: String,
            cropStage: String,
            soilType: String,
            lastIrrigationDate: String?,
            forecastPrecip48hMm: Double
        ): ResultState<IrrigationAdvisory> {
            return ResultState.Success(
                IrrigationAdvisory(
                    action = "IRRIGATE",
                    urgency = "high",
                    metrics = CropWaterBalanceMetrics(5.0, 1.15, 5.75, 0.0, 5.75, 30.0),
                    rationale = "Apply irrigation.",
                    calculationMethod = "FAO-56"
                )
            )
        }

        override suspend fun getSprayWindowAdvisory(windSpeedKmh: Double, rainProbabilityPct: Double, tempC: Double, relativeHumidityPct: Double) = throw NotImplementedError()
        override suspend fun getLocationHierarchy(latitude: Double, longitude: Double) = throw NotImplementedError()
        override suspend fun getBoundary(level: String, code: String) = throw NotImplementedError()
        override suspend fun getHazardIntersection(warningGeometry: kotlinx.serialization.json.JsonObject?, alertId: String, event: String, severity: String, targetLevel: String) = throw NotImplementedError()
        override suspend fun getRiskAssessment(districtName: String, precip24hPercentile: Double, exposureIndex: Double, vulnerabilityIndex: Double, hazardType: String) = throw NotImplementedError()
        override suspend fun getGISAnalysis(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?, observedTempC: Double?, leadHours: Int) = throw NotImplementedError()
        override suspend fun getGFSGridPoint(latitude: Double, longitude: Double, leadHours: Int) = throw NotImplementedError()
        override suspend fun getNWPModelComparison(latitude: Double, longitude: Double, leadHours: Int) = throw NotImplementedError()
        override suspend fun getPointWeatherMap(latitude: Double, longitude: Double) = throw NotImplementedError()
        override suspend fun getWarningMap(warningGeometry: kotlinx.serialization.json.JsonObject, alertId: String, event: String, severity: String) = throw NotImplementedError()
        override suspend fun getRiskMap(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?) = throw NotImplementedError()
    }

    @Test
    fun `SendChatMessageUseCase executes chat via repository`() = runTest {
        val repo = FakeWeatherGPTRepository()
        val useCase = SendChatMessageUseCase(repo)

        val query = ChatQuery("sess_1", "मौसम कैसा रहेगा?", selectedBrain = DomainBrain.GENERAL)
        val result = useCase(query)

        assertTrue(result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals("resp_uc_1", data.responseId)
        assertEquals(DomainBrain.GENERAL, data.brain)
    }

    @Test
    fun `GetCurrentWeatherUseCase fetches current observation`() = runTest {
        val repo = FakeWeatherGPTRepository()
        val useCase = GetCurrentWeatherUseCase(repo)

        val result = useCase(21.1702, 72.8311)

        assertTrue(result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals(29.5, data.temperatureC, 0.01)
    }

    @Test
    fun `GetIrrigationAdvisoryUseCase computes advisory`() = runTest {
        val repo = FakeWeatherGPTRepository()
        val useCase = GetIrrigationAdvisoryUseCase(repo)

        val result = useCase(21.1702, 72.8311, "Wheat")

        assertTrue(result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals("IRRIGATE", data.action)
    }
}
