package com.weathergpt.data.repository

import com.weathergpt.core.error.AppError
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.core.network.RetrofitClientFactory
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.DomainBrain
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.concurrent.TimeUnit

@OptIn(ExperimentalCoroutinesApi::class)
class WeatherGPTRepositoryTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var repository: WeatherGPTRepositoryImpl
    private val testDispatcher = UnconfinedTestDispatcher()

    private class FakeNetworkMonitor(var online: Boolean = true) : NetworkMonitor {
        override val networkState: Flow<NetworkState> = MutableStateFlow(
            if (online) NetworkState.Available else NetworkState.Unavailable
        )
        override val isOnline: Boolean
            get() = online
    }

    @Before
    fun setup() {
        mockWebServer = MockWebServer()
        mockWebServer.start()

        val okHttpClient = OkHttpClient.Builder()
            .connectTimeout(2, TimeUnit.SECONDS)
            .readTimeout(2, TimeUnit.SECONDS)
            .build()

        val retrofit = RetrofitClientFactory.createRetrofit(
            okHttpClient = okHttpClient,
            baseUrl = mockWebServer.url("/").toString()
        )
        val apiService = retrofit.create(WeatherGPTApiService::class.java)
        repository = WeatherGPTRepositoryImpl(
            apiService = apiService,
            ioDispatcher = testDispatcher,
            networkMonitor = FakeNetworkMonitor(online = true)
        )
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
    }

    // ========================================================================
    // 1. System Endpoints
    // ========================================================================

    @Test
    fun `checkHealth returns Success when server responds with 200`() = runTest(testDispatcher) {
        val json = """
            {
                "status": "healthy",
                "app_name": "WeatherGPT",
                "environment": "production",
                "version": "v1",
                "timestamp": "2026-08-30T10:00:00Z"
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.checkHealth()

        assertTrue(result is ResultState.Success)
        val health = (result as ResultState.Success).data
        assertEquals("healthy", health.status)
        assertTrue(health.isHealthy)
    }

    // ========================================================================
    // 2. Chat Endpoints
    // ========================================================================

    @Test
    fun `sendChat returns Success with grounded response`() = runTest(testDispatcher) {
        val json = """
            {
                "response_id": "resp_9988",
                "session_id": "sess_123",
                "brain": "farmer",
                "language": "hi",
                "created_at": "2026-08-30T10:00:00Z",
                "summary": "सिंचाई स्थगित करने की सलाह।",
                "answer": "आगामी 48 घंटों में पर्याप्त वर्षा होने की संभावना है।",
                "visualizations": [],
                "sources": [],
                "limitations": []
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val query = ChatQuery(
            sessionId = "sess_123",
            query = "क्या मुझे आज सिंचाई करनी चाहिए?",
            selectedBrain = DomainBrain.FARMER
        )
        val result = repository.sendChat(query)

        assertTrue(result is ResultState.Success)
        val response = (result as ResultState.Success).data
        assertEquals("resp_9988", response.responseId)
        assertEquals(DomainBrain.FARMER, response.brain)
        assertEquals("सिंचाई स्थगित करने की सलाह।", response.summary)
    }

    // ========================================================================
    // 3. Weather Endpoints
    // ========================================================================

    @Test
    fun `getCurrentWeather returns accurate meteorological observation`() = runTest(testDispatcher) {
        val json = """
            {
                "location": {"latitude": 21.1702, "longitude": 72.8311},
                "observation_time": "2026-08-30T10:00:00Z",
                "temperature_c": 30.5,
                "feels_like_c": 35.2,
                "relative_humidity_pct": 80.0,
                "precipitation_mm": 2.5,
                "rain_intensity_category": "light",
                "wind_speed_kmh": 12.0,
                "wind_direction_deg": 220.0,
                "surface_pressure_hpa": 1008.0,
                "weather_condition": "Rain"
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getCurrentWeather(21.1702, 72.8311)

        assertTrue(result is ResultState.Success)
        val obs = (result as ResultState.Success).data
        assertEquals(30.5, obs.temperatureC, 0.01)
        assertEquals("Rain", obs.weatherCondition)
    }

    @Test
    fun `getWeatherAlerts preserves official severity level`() = runTest(testDispatcher) {
        val json = """
            {
                "authority": "India Meteorological Department (IMD)",
                "retrieved_at": "2026-08-30T10:00:00Z",
                "active_alerts_count": 1,
                "alerts": [
                    {
                        "alert_id": "IMD-WARN-01",
                        "warning_color": "Orange",
                        "hazard": "Heavy Rainfall",
                        "severity": "Severe",
                        "area_description": "Surat District",
                        "headline": "Orange Alert Issued",
                        "description": "Heavy to very heavy rainfall expected.",
                        "effective_from": "2026-08-30T10:00:00Z",
                        "expires_at": "2026-08-31T10:00:00Z"
                    }
                ]
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getWeatherAlerts(district = "Surat")

        assertTrue(result is ResultState.Success)
        val report = (result as ResultState.Success).data
        assertEquals(1, report.activeAlertsCount)
        assertEquals("Orange", report.alerts[0].warningColor)
    }

    // ========================================================================
    // 4. Farmer Endpoints
    // ========================================================================

    @Test
    fun `getIrrigationAdvisory returns deterministic water balance`() = runTest(testDispatcher) {
        val json = """
            {
                "action": "IRRIGATE",
                "urgency": "high",
                "metrics": {
                    "reference_et0_mm_day": 5.4,
                    "crop_kc": 1.15,
                    "daily_water_demand_mm": 6.21,
                    "forecast_rainfall_48h_mm": 0.0,
                    "net_deficit_mm": 6.21,
                    "final_depletion_mm": 40.0
                },
                "rationale": "Irrigation is required.",
                "provenance": {"calculation_method": "FAO-56 Penman-Monteith"}
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getIrrigationAdvisory(21.1702, 72.8311, "Wheat")

        assertTrue(result is ResultState.Success)
        val adv = (result as ResultState.Success).data
        assertEquals("IRRIGATE", adv.action)
        assertEquals(5.4, adv.metrics.referenceEt0MmDay, 0.01)
    }

    // ========================================================================
    // 5. GIS Endpoints
    // ========================================================================

    @Test
    fun `getLocationHierarchy returns resolved district and state`() = runTest(testDispatcher) {
        val json = """
            {
                "latitude": 21.1702,
                "longitude": 72.8311,
                "is_resolved": true,
                "district": {"code": "IN-GJ-24", "name": "Surat", "level": "district"},
                "state": {"code": "IN-GJ", "name": "Gujarat", "level": "state"}
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getLocationHierarchy(21.1702, 72.8311)

        assertTrue(result is ResultState.Success)
        val loc = (result as ResultState.Success).data
        assertTrue(loc.isResolved)
        assertEquals("Surat", loc.district?.name)
    }

    @Test
    fun `getBoundary returns administrative boundary GeoJSON`() = runTest(testDispatcher) {
        val json = """
            {
                "code": "IN-GJ-24",
                "name": "Surat",
                "level": "district",
                "parent_code": "IN-GJ",
                "area_sqkm": 4418.0,
                "geojson": {
                    "type": "MultiPolygon",
                    "coordinates": []
                }
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getBoundary("district", "IN-GJ-24")

        assertTrue(result is ResultState.Success)
        val boundary = (result as ResultState.Success).data
        assertEquals("Surat", boundary.name)
        assertEquals("district", boundary.level)
        assertEquals(4418.0, boundary.areaSqkm!!, 0.01)
    }

    @Test
    fun `getHazardIntersection returns affected boundary units and exposed area`() = runTest(testDispatcher) {
        val json = """
            {
                "alert_id": "IMD-WARN-01",
                "event": "Heavy Rainfall",
                "severity": "Orange",
                "total_affected_boundaries": 1,
                "total_affected_area_sqkm": 250.5,
                "affected_units": [
                    {
                        "boundary": {
                            "code": "IN-GJ-24",
                            "name": "Surat",
                            "level": "district"
                        },
                        "exposed_area_sqkm": 250.5,
                        "exposed_area_pct": 5.67
                    }
                ]
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getHazardIntersection(
            warningGeometry = buildJsonObject { put("type", "Polygon") },
            alertId = "IMD-WARN-01",
            event = "Heavy Rainfall",
            severity = "Orange"
        )

        assertTrue(result is ResultState.Success)
        val intersection = (result as ResultState.Success).data
        assertEquals("IMD-WARN-01", intersection.alertId)
        assertEquals("Orange", intersection.severity)
        assertEquals(1, intersection.totalAffectedBoundaries)
        assertEquals(250.5, intersection.totalAffectedAreaSqkm!!, 0.01)
    }

    // ========================================================================
    // 6. NWP Endpoints
    // ========================================================================

    @Test
    fun `getGFSGridPoint returns prognostic variables`() = runTest(testDispatcher) {
        val json = """
            {
                "model": "GFS_0p25",
                "grid_resolution_deg": 0.25,
                "location": {"latitude": 21.25, "longitude": 72.75},
                "forecast_lead_hours": 24,
                "valid_time": "2026-08-31T00:00:00Z",
                "atmospheric_variables": {
                    "temperature_2m_c": 28.5,
                    "relative_humidity_2m_pct": 85.0,
                    "accumulated_precip_mm": 24.0,
                    "wind_speed_kmh": 15.0,
                    "wind_direction_deg": 230.0,
                    "pressure_msl_hpa": 1006.0,
                    "total_cloud_cover_pct": 90.0
                }
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getGFSGridPoint(21.25, 72.75)

        assertTrue(result is ResultState.Success)
        val nwp = (result as ResultState.Success).data
        assertEquals("GFS_0p25", nwp.model)
        assertEquals(24.0, nwp.accumulatedPrecipMm, 0.01)
    }

    @Test
    fun `getWRFGridPoint returns structured unavailable response`() = runTest(testDispatcher) {
        val json = """
            {
                "status": "UNAVAILABLE",
                "status_code": "WRF_DATA_UNAVAILABLE",
                "message": "WRF regional data source is unconfigured.",
                "model": "WRF_REGIONAL",
                "grid_resolution_deg": 0.03,
                "location": {"latitude": 21.25, "longitude": 72.75},
                "forecast_lead_hours": 24,
                "valid_time": null,
                "atmospheric_variables": null,
                "provenance": {"configured": false}
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getWRFGridPoint(21.25, 72.75)

        assertTrue(result is ResultState.Success)
        val wrf = (result as ResultState.Success).data
        assertEquals("WRF_REGIONAL", wrf.model)
        assertEquals("UNAVAILABLE", wrf.status)
        assertEquals("WRF regional data source is unconfigured.", wrf.statusMessage)
    }

    @Test
    fun `getWRFGridPoint returns valid prognostic when available`() = runTest(testDispatcher) {
        val json = """
            {
                "status": "AVAILABLE",
                "status_code": "WRF_DATA_AVAILABLE",
                "message": "Valid WRF data",
                "model": "WRF_REGIONAL",
                "grid_resolution_deg": 0.03,
                "location": {"latitude": 21.25, "longitude": 72.75},
                "forecast_lead_hours": 24,
                "valid_time": "2026-08-31T12:00:00Z",
                "atmospheric_variables": {
                    "temperature_2m_c": 31.0,
                    "relative_humidity_2m_pct": 70.0,
                    "accumulated_precip_mm": 12.5,
                    "wind_speed_kmh": 16.0,
                    "wind_direction_deg": 240.0,
                    "pressure_msl_hpa": 1009.0,
                    "total_cloud_cover_pct": 80.0,
                    "cape_jkg": 1500.0
                }
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getWRFGridPoint(21.25, 72.75)

        assertTrue(result is ResultState.Success)
        val wrf = (result as ResultState.Success).data
        assertEquals("WRF_REGIONAL", wrf.model)
        assertEquals("AVAILABLE", wrf.status)
        assertEquals(31.0, wrf.temperature2mC, 0.01)
        assertEquals(1500.0, wrf.capeJkg ?: 0.0, 0.01)
    }

    // ========================================================================
    // 7. Map Endpoints
    // ========================================================================

    @Test
    fun `getPointWeatherMap returns map specification with coordinates`() = runTest(testDispatcher) {
        val json = """
            {
                "type": "map_specification",
                "id": "map_pt_1",
                "title": "Surat Weather Point",
                "viewport": {
                    "center": [72.8311, 21.1702],
                    "zoom": 10.0,
                    "pitch": 0.0,
                    "bearing": 0.0,
                    "bbox": [72.0, 20.5, 73.5, 22.0]
                },
                "layers": [],
                "legend": []
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getPointWeatherMap(21.1702, 72.8311)

        assertTrue(result is ResultState.Success)
        val map = (result as ResultState.Success).data
        assertEquals("map_pt_1", map.id)
        assertEquals(72.8311, map.centerLongitude, 0.0001)
        assertEquals(21.1702, map.centerLatitude, 0.0001)
    }

    @Test
    fun `getWarningMap preserves authoritative warning polygon and severity`() = runTest(testDispatcher) {
        val json = """
            {
                "type": "map_specification",
                "id": "map_warn_01",
                "title": "IMD Red Warning Map",
                "viewport": {
                    "center": [72.8311, 21.1702],
                    "zoom": 9.0
                },
                "layers": [
                    {
                        "id": "warning_layer",
                        "name": "Red Alert Zone",
                        "type": "fill",
                        "visible": true
                    }
                ],
                "legend": [
                    {
                        "label": "Red Alert",
                        "color": "#D32F2F",
                        "official_level": "Red"
                    }
                ],
                "provenance": {
                    "authority": "IMD"
                },
                "quality": "AVAILABLE"
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getWarningMap(
            warningGeometry = buildJsonObject { put("type", "Polygon") },
            alertId = "IMD-WARN-RED",
            event = "Extremely Heavy Rainfall",
            severity = "Red"
        )

        assertTrue(result is ResultState.Success)
        val map = (result as ResultState.Success).data
        assertEquals("map_warn_01", map.id)
        assertEquals(1, map.layers.size)
        assertEquals(1, map.legend.size)
        assertEquals("Red", map.legend[0].officialLevel)
    }

    @Test
    fun `getRiskMap returns analytical risk map specification`() = runTest(testDispatcher) {
        val json = """
            {
                "type": "map_specification",
                "id": "map_risk_01",
                "title": "Operational Risk Map — Surat",
                "viewport": {
                    "center": [72.8311, 21.1702],
                    "zoom": 8.5
                },
                "layers": [
                    {
                        "id": "risk_overlay",
                        "name": "Composite Risk Score",
                        "type": "circle",
                        "visible": true
                    }
                ],
                "legend": [
                    {
                        "label": "High Risk",
                        "color": "#E65100",
                        "value_range": "6.0 - 8.0"
                    }
                ],
                "quality": "AVAILABLE"
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val result = repository.getRiskMap(latitude = 21.1702, longitude = 72.8311)

        assertTrue(result is ResultState.Success)
        val map = (result as ResultState.Success).data
        assertEquals("map_risk_01", map.id)
        assertEquals(1, map.layers.size)
        assertEquals("High Risk", map.legend[0].label)
    }

    // ========================================================================
    // 8. Offline & Error Hardening Scenarios
    // ========================================================================

    @Test
    fun `offline monitor fast-fails before network call is dispatched`() = runTest(testDispatcher) {
        val offlineRepo = WeatherGPTRepositoryImpl(
            apiService = repository.let {
                val retrofit = RetrofitClientFactory.createRetrofit(
                    baseUrl = mockWebServer.url("/").toString()
                )
                retrofit.create(WeatherGPTApiService::class.java)
            },
            ioDispatcher = testDispatcher,
            networkMonitor = FakeNetworkMonitor(online = false)
        )

        val result = offlineRepo.getCurrentWeather(21.1702, 72.8311)

        assertTrue(result is ResultState.Error)
        val error = (result as ResultState.Error).error
        assertTrue(error is AppError.NetworkUnavailable)
        assertEquals(0, mockWebServer.requestCount) // Zero HTTP requests dispatched!
    }

    @Test
    fun `idempotent GET request recovers after transient 503 error`() = runTest(testDispatcher) {
        val validJson = """
            {
                "location": {"latitude": 21.1702, "longitude": 72.8311},
                "observation_time": "2026-08-30T10:00:00Z",
                "temperature_c": 30.5,
                "feels_like_c": 35.2,
                "relative_humidity_pct": 80.0,
                "precipitation_mm": 2.5,
                "rain_intensity_category": "light",
                "wind_speed_kmh": 12.0,
                "wind_direction_deg": 220.0,
                "surface_pressure_hpa": 1008.0,
                "weather_condition": "Rain"
            }
        """.trimIndent()

        // 1st request fails with 503, 2nd request succeeds with 200
        mockWebServer.enqueue(MockResponse().setResponseCode(503).setBody("Temporary Gateway Hiccup"))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(validJson))

        val result = repository.getCurrentWeather(21.1702, 72.8311)

        assertTrue(result is ResultState.Success)
        val obs = (result as ResultState.Success).data
        assertEquals(30.5, obs.temperatureC, 0.01)
        assertEquals(2, mockWebServer.requestCount) // Retried once and succeeded
    }

    @Test
    fun `422 validation error maps to ValidationError with RFC 7807 problem details`() = runTest(testDispatcher) {
        val problemJson = """
            {
                "type": "https://weathergpt.in/errors/validation-error",
                "title": "Unprocessable Entity",
                "status": 422,
                "detail": "Latitude 45.0 is outside India boundary (6.0 to 38.0)",
                "instance": "/api/v1/weather/current",
                "request_id": "req_val_err_01"
            }
        """.trimIndent()
        mockWebServer.enqueue(MockResponse().setResponseCode(422).setBody(problemJson))

        val result = repository.getCurrentWeather(45.0, 72.0)

        assertTrue(result is ResultState.Error)
        val error = (result as ResultState.Error).error
        assertTrue(error is AppError.ValidationError)
        val validationError = error as AppError.ValidationError
        assertEquals(422, validationError.statusCode)
        assertEquals("req_val_err_01", validationError.requestId)
        assertEquals("Latitude 45.0 is outside India boundary (6.0 to 38.0)", validationError.message)
    }

    @Test
    fun `429 rate limited error maps to RateLimited`() = runTest(testDispatcher) {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(429)
                .setHeader("Retry-After", "60")
                .setHeader("x-request-id", "req-rate-429")
                .setBody("Too Many Requests")
        )

        val result = repository.getCurrentWeather(21.0, 72.0)

        assertTrue(result is ResultState.Error)
        val error = (result as ResultState.Error).error
        assertTrue(error is AppError.RateLimited)
        val rateLimitError = error as AppError.RateLimited
        assertEquals(429, rateLimitError.statusCode)
        assertEquals(60L, rateLimitError.retryAfterSeconds)
        assertEquals("req-rate-429", rateLimitError.requestId)
    }
}
