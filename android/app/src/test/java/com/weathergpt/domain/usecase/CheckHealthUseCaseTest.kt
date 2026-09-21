package com.weathergpt.domain.usecase

import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.model.ReadinessStatus
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.model.gis.AdministrativeBoundary
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.HazardIntersection
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class CheckHealthUseCaseTest {

    private class MockRepository : WeatherGPTRepository {
        var healthStateToReturn: ResultState<HealthStatus> = ResultState.Success(
            HealthStatus(
                status = "healthy",
                appName = "WeatherGPT",
                environment = "test",
                version = "v1",
                apiVersion = "v1",
                timestamp = "2026-08-30T10:00:00Z"
            )
        )
        var readinessStateToReturn: ResultState<ReadinessStatus> = ResultState.Success(
            ReadinessStatus(
                status = "ready",
                isReady = true,
                environment = "test",
                apiVersion = "v1",
                dependencies = mapOf("database" to "healthy"),
                probes = mapOf("database" to true),
                timestamp = "2026-08-30T10:00:00Z"
            )
        )

        override suspend fun checkHealth(): ResultState<HealthStatus> = healthStateToReturn
        override suspend fun checkReadiness(): ResultState<ReadinessStatus> = readinessStateToReturn
        override suspend fun sendChat(query: ChatQuery): ResultState<ChatResponse> = throw NotImplementedError()
        override suspend fun getCurrentWeather(latitude: Double, longitude: Double): ResultState<CurrentWeather> = throw NotImplementedError()
        override suspend fun getWeatherForecast(latitude: Double, longitude: Double, days: Int, hourly: Boolean): ResultState<WeatherForecast> = throw NotImplementedError()
        override suspend fun getWeatherAlerts(district: String?, latitude: Double?, longitude: Double?): ResultState<WeatherAlertsReport> = throw NotImplementedError()
        override suspend fun getWeatherIntelligence(latitude: Double, longitude: Double, leadHours: Int, includeNwp: Boolean): ResultState<WeatherIntelligence> = throw NotImplementedError()
        override suspend fun getIrrigationAdvisory(latitude: Double, longitude: Double, cropName: String, cropStage: String, soilType: String, lastIrrigationDate: String?, forecastPrecip48hMm: Double): ResultState<IrrigationAdvisory> = throw NotImplementedError()
        override suspend fun getSprayWindowAdvisory(windSpeedKmh: Double, rainProbabilityPct: Double, tempC: Double, relativeHumidityPct: Double): ResultState<SpraySuitability> = throw NotImplementedError()
        override suspend fun getLocationHierarchy(latitude: Double, longitude: Double): ResultState<LocationHierarchy> = throw NotImplementedError()
        override suspend fun getBoundary(level: String, code: String): ResultState<AdministrativeBoundary> = throw NotImplementedError()
        override suspend fun getHazardIntersection(warningGeometry: JsonObject?, alertId: String, event: String, severity: String, targetLevel: String): ResultState<HazardIntersection> = throw NotImplementedError()
        override suspend fun getRiskAssessment(districtName: String, precip24hPercentile: Double, exposureIndex: Double, vulnerabilityIndex: Double, hazardType: String): ResultState<OperationalRisk> = throw NotImplementedError()
        override suspend fun getGISAnalysis(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?, observedTempC: Double?, leadHours: Int): ResultState<GISAnalysisReport> = throw NotImplementedError()
        override suspend fun getGFSGridPoint(latitude: Double, longitude: Double, leadHours: Int): ResultState<NWPGridPoint> = throw NotImplementedError()
        override suspend fun getWRFGridPoint(latitude: Double, longitude: Double, leadHours: Int): ResultState<NWPGridPoint> = throw NotImplementedError()
        override suspend fun getNWPModelComparison(latitude: Double, longitude: Double, leadHours: Int): ResultState<NWPModelComparison> = throw NotImplementedError()
        override suspend fun getPointWeatherMap(latitude: Double, longitude: Double): ResultState<MapSpecification> = throw NotImplementedError()
        override suspend fun getWarningMap(warningGeometry: JsonObject, alertId: String, event: String, severity: String): ResultState<MapSpecification> = throw NotImplementedError()
        override suspend fun getRiskMap(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?): ResultState<MapSpecification> = throw NotImplementedError()
        override suspend fun evaluateDecision(question: String, locationName: String?, latitude: Double?, longitude: Double?, requestedTime: String?, domain: String?, context: Map<String, String>?): ResultState<com.weathergpt.domain.model.decision.NirnayCard> = throw NotImplementedError()
        override suspend fun getFarmerProfile(): ResultState<com.weathergpt.domain.model.farmer.FarmerProfile> = ResultState.Success(com.weathergpt.domain.model.farmer.FarmerProfile())
        override suspend fun saveFarmerProfile(profile: com.weathergpt.domain.model.farmer.FarmerProfile): ResultState<Unit> = ResultState.Success(Unit)
    }

    @Test
    fun `invoke delegates call to repository checkHealth`() = runTest {
        val mockRepo = MockRepository()
        val useCase = CheckHealthUseCase(mockRepo)

        val result = useCase()

        assertTrue(result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertEquals("healthy", data.status)
        assertEquals("test", data.environment)
    }

    @Test
    fun `CheckReadinessUseCase delegates call to repository checkReadiness`() = runTest {
        val mockRepo = MockRepository()
        val useCase = CheckReadinessUseCase(mockRepo)

        val result = useCase()

        assertTrue(result is ResultState.Success)
        val data = (result as ResultState.Success).data
        assertTrue(data.isReady)
        assertEquals("ready", data.status)
    }
}
