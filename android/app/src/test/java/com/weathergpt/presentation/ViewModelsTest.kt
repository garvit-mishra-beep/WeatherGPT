package com.weathergpt.presentation

import com.weathergpt.core.error.AppError
import com.weathergpt.core.error.ProblemDetails
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.ConfidenceAssessment
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.chat.EvidenceCitation
import com.weathergpt.domain.model.chat.OfficialWarningCard
import com.weathergpt.domain.model.farmer.CropWaterBalanceMetrics
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.model.gis.BoundaryUnit
import com.weathergpt.domain.model.gis.AdministrativeBoundary
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.HazardIntersection
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.model.map.LegendItem
import com.weathergpt.domain.model.map.MapLayer
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.map.MapViewport
import com.weathergpt.domain.model.nwp.DivergenceAnalysis
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.presentation.alerts.AlertsViewModel
import com.weathergpt.presentation.analyst.AnalystDashboardViewModel
import com.weathergpt.presentation.brain.BrainSelectionViewModel
import com.weathergpt.presentation.chat.ChatMessage
import com.weathergpt.presentation.chat.ChatViewModel
import com.weathergpt.presentation.components.IntelligenceBrain
import com.weathergpt.presentation.data.DataViewModel
import com.weathergpt.presentation.farmer.FarmerProfileViewModel
import com.weathergpt.presentation.home.HomeViewModel
import com.weathergpt.presentation.map.MapViewModel
import com.weathergpt.presentation.map.WeatherMapLayer
import com.weathergpt.presentation.profile.ProfileViewModel
import com.weathergpt.presentation.settings.SettingsViewModel
import com.weathergpt.presentation.weather.WeatherViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.JsonObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ViewModelsTest {

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        com.weathergpt.core.config.AppConfig.setDemoMode(false)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        com.weathergpt.core.config.AppConfig.resetToDefault()
    }

    companion object {
        fun createFakeRepository(
            shouldFailChat: Boolean = false,
            chatError: AppError = AppError.ServerUnavailable(500, "req-123"),
            analystRiskMatrixResult: ResultState<OperationalRisk>? = null,
            climateTrendsResult: ResultState<com.weathergpt.domain.model.climate.ClimateTrends>? = null,
            climateNormalsResult: ResultState<com.weathergpt.domain.model.climate.ClimateNormals>? = null
        ): WeatherGPTRepository {
        return object : WeatherGPTRepository {
            override suspend fun checkHealth() = ResultState.Success(
                com.weathergpt.domain.model.HealthStatus("healthy", "WeatherGPT", "test", "v1", "v1", "now")
            )
            override suspend fun checkReadiness() = ResultState.Success(
                com.weathergpt.domain.model.ReadinessStatus(
                    status = "ready",
                    isReady = true,
                    environment = "test",
                    apiVersion = "v1",
                    timestamp = "now"
                )
            )
            override suspend fun sendChat(query: ChatQuery): ResultState<ChatResponse> {
                if (shouldFailChat) {
                    return ResultState.Error(chatError)
                }
                return ResultState.Success(
                    ChatResponse(
                        responseId = "resp-001",
                        sessionId = query.sessionId,
                        brain = query.selectedBrain,
                        language = query.languagePreference.code,
                        createdAt = "2026-08-31T12:00:00Z",
                        summary = "Weather outlook summary",
                        answer = "Clear skies expected with light breeze.",
                        data = null,
                        recommendation = null,
                        alert = OfficialWarningCard(
                            source = "IMD",
                            level = "Orange",
                            hazardType = "Heavy Rain",
                            headline = "Warning",
                            description = "Isolated squalls",
                            validUntil = "2026-09-01T12:00:00Z"
                        ),
                        visualizations = emptyList(),
                        sources = listOf(
                            EvidenceCitation(authority = "IMD", dataset = "CAP Feeds", retrievedAt = "now", isOfficial = true)
                        ),
                        confidence = ConfidenceAssessment(
                            evidenceLevel = "HIGH",
                            modelAgreement = "0.95",
                            dataFreshnessStatus = "FRESH",
                            notes = null
                        ),
                        limitations = emptyList()
                    )
                )
            }
            override suspend fun getCurrentWeather(latitude: Double, longitude: Double): ResultState<CurrentWeather> {
                return ResultState.Success(
                    CurrentWeather(
                        location = com.weathergpt.domain.model.weather.LocationCoordinates(latitude, longitude),
                        observationTime = "2026-08-31T12:00:00Z",
                        temperatureC = 31.5,
                        feelsLikeC = 34.0,
                        relativeHumidityPct = 65.0,
                        precipitationMm = 0.0,
                        rainIntensityCategory = "None",
                        windSpeedKmh = 12.0,
                        windDirectionDeg = 180.0,
                        surfacePressureHpa = 1012.0,
                        weatherCondition = "Partly Cloudy",
                        provider = "Open-Meteo",
                        authority = "IMD"
                    )
                )
            }
            override suspend fun getWeatherForecast(latitude: Double, longitude: Double, days: Int, hourly: Boolean): ResultState<WeatherForecast> {
                return ResultState.Success(
                    WeatherForecast(
                        location = com.weathergpt.domain.model.weather.LocationCoordinates(latitude, longitude),
                        generatedAt = "2026-08-31T12:00:00Z",
                        forecastStart = "2026-08-31",
                        forecastEnd = "2026-09-07",
                        dailyForecast = listOf(
                            DailyForecast("2026-08-31", 33.0, 24.0, 0.0, 10.0, 14.0, "Sunny")
                        ),
                        hourlyForecast = emptyList(),
                        provider = "Open-Meteo"
                    )
                )
            }
            override suspend fun getWeatherAlerts(district: String?, latitude: Double?, longitude: Double?): ResultState<WeatherAlertsReport> {
                return ResultState.Success(
                    WeatherAlertsReport(
                        authority = "IMD",
                        retrievedAt = "2026-08-31T12:00:00Z",
                        activeAlertsCount = 1,
                        alerts = listOf(
                            OfficialAlert(
                                alertId = "ALERT-001",
                                warningColor = "Orange",
                                hazard = "Heavy Rainfall",
                                severity = "Severe",
                                areaDescription = "Surat District",
                                headline = "Heavy Rainfall Warning",
                                description = "Isolated heavy to very heavy rainfall expected",
                                effectiveFrom = "2026-08-31T12:00:00Z",
                                expiresAt = "2026-09-01T12:00:00Z",
                                instructions = "Stay indoors"
                            )
                        )
                    )
                )
            }
            override suspend fun getWeatherIntelligence(latitude: Double, longitude: Double, leadHours: Int, includeNwp: Boolean): ResultState<WeatherIntelligence> {
                return ResultState.Success(
                    WeatherIntelligence(
                        latitude = latitude,
                        longitude = longitude,
                        dataQuality = "HIGH",
                        currentObservation = CurrentWeather(
                            location = com.weathergpt.domain.model.weather.LocationCoordinates(latitude, longitude),
                            observationTime = "2026-08-31T12:00:00Z",
                            temperatureC = 31.5,
                            feelsLikeC = 34.0,
                            relativeHumidityPct = 65.0,
                            precipitationMm = 0.0,
                            rainIntensityCategory = "None",
                            windSpeedKmh = 12.0,
                            windDirectionDeg = 180.0,
                            surfacePressureHpa = 1012.0,
                            weatherCondition = "Partly Cloudy",
                            provider = "Open-Meteo",
                            authority = "IMD"
                        ),
                        alerts = emptyList(),
                        rawProvenance = null
                    )
                )
            }
            override suspend fun getIrrigationAdvisory(latitude: Double, longitude: Double, cropName: String, cropStage: String, soilType: String, lastIrrigationDate: String?, forecastPrecip48hMm: Double): ResultState<IrrigationAdvisory> {
                return ResultState.Success(
                    IrrigationAdvisory(
                        action = "IRRIGATE",
                        urgency = "high",
                        metrics = com.weathergpt.domain.model.farmer.CropWaterBalanceMetrics(
                            referenceEt0MmDay = 4.8,
                            cropKc = 1.15,
                            dailyWaterDemandMm = 5.52,
                            forecastRainfall48hMm = 0.0,
                            netDeficitMm = 20.0,
                            finalDepletionMm = 25.0
                        ),
                        rationale = "High soil moisture depletion detected",
                        calculationMethod = "FAO-56 Penman-Monteith"
                    )
                )
            }
            override suspend fun getSprayWindowAdvisory(windSpeedKmh: Double, rainProbabilityPct: Double, tempC: Double, relativeHumidityPct: Double): ResultState<SpraySuitability> {
                return ResultState.Success(
                    SpraySuitability(
                        isSuitable = true,
                        conditionLevel = "optimal",
                        recommendation = "Optimal spraying conditions",
                        windSuitable = true,
                        rainProbabilitySuitable = true,
                        calculationMethod = "Deterministic Rule Matrix"
                    )
                )
            }
            override suspend fun getLocationHierarchy(latitude: Double, longitude: Double): ResultState<LocationHierarchy> {
                return ResultState.Success(
                    LocationHierarchy(
                        latitude = latitude,
                        longitude = longitude,
                        isResolved = true,
                        country = com.weathergpt.domain.model.gis.BoundaryUnit(code = "IND", name = "India", level = "country", parentCode = null, areaSqkm = null),
                        state = com.weathergpt.domain.model.gis.BoundaryUnit(code = "IN-DL", name = "Delhi", level = "state", parentCode = "IND", areaSqkm = null),
                        district = com.weathergpt.domain.model.gis.BoundaryUnit(code = "IN-DL-ND", name = "New Delhi", level = "district", parentCode = "IN-DL", areaSqkm = null),
                        subdistrict = com.weathergpt.domain.model.gis.BoundaryUnit(code = "IN-DL-ND-CN", name = "Connaught Place", level = "sub_district", parentCode = "IN-DL-ND", areaSqkm = null)
                    )
                )
            }
            override suspend fun getBoundary(level: String, code: String) = throw NotImplementedError()
            override suspend fun getHazardIntersection(warningGeometry: JsonObject?, alertId: String, event: String, severity: String, targetLevel: String) = throw NotImplementedError()
            override suspend fun getRiskAssessment(districtName: String, precip24hPercentile: Double, exposureIndex: Double, vulnerabilityIndex: Double, hazardType: String): ResultState<OperationalRisk> {
                return ResultState.Success(
                    OperationalRisk(
                        district = districtName,
                        hazardType = hazardType,
                        hazardIndex = 6.5,
                        exposureIndex = exposureIndex,
                        vulnerabilityIndex = vulnerabilityIndex,
                        compositeRiskScore = 7.05,
                        riskLevel = "HIGH",
                        actionPriority = "Immediate drainage clearance"
                    )
                )
            }
            override suspend fun getGISAnalysis(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?, observedTempC: Double?, leadHours: Int): ResultState<GISAnalysisReport> {
                return ResultState.Success(
                    GISAnalysisReport(
                        analysisId = "GIS-REP-001",
                        latitude = latitude ?: 28.61,
                        longitude = longitude ?: 77.20,
                        hazardScore = 6.5,
                        exposureScore = 8.0,
                        vulnerabilityScore = 7.0,
                        impactScore = 7.05,
                        riskCategory = "HIGH",
                        actionableGuidance = listOf("Immediate drainage clearance")
                    )
                )
            }
            override suspend fun getGFSGridPoint(latitude: Double, longitude: Double, leadHours: Int): ResultState<NWPGridPoint> {
                return ResultState.Success(
                    NWPGridPoint(
                        model = "GFS",
                        gridResolutionDeg = 0.25,
                        latitude = latitude,
                        longitude = longitude,
                        forecastLeadHours = leadHours,
                        validTime = "2026-08-31T12:00:00Z",
                        temperature2mC = 30.2,
                        relativeHumidity2mPct = 58.0,
                        accumulatedPrecipMm = 0.0,
                        windSpeedKmh = 12.0,
                        windDirectionDeg = 180.0,
                        windGustKmh = null,
                        pressureMslHpa = 1011.5,
                        totalCloudCoverPct = 20.0
                    )
                )
            }
            override suspend fun getWRFGridPoint(latitude: Double, longitude: Double, leadHours: Int): ResultState<NWPGridPoint> {
                return ResultState.Success(
                    NWPGridPoint(
                        model = "WRF_REGIONAL",
                        gridResolutionDeg = 0.03,
                        latitude = latitude,
                        longitude = longitude,
                        forecastLeadHours = leadHours,
                        validTime = "2026-08-31T12:00:00Z",
                        temperature2mC = 0.0,
                        relativeHumidity2mPct = 0.0,
                        accumulatedPrecipMm = 0.0,
                        windSpeedKmh = 0.0,
                        windDirectionDeg = 0.0,
                        windGustKmh = null,
                        pressureMslHpa = 1013.25,
                        totalCloudCoverPct = 0.0,
                        status = "UNAVAILABLE",
                        statusMessage = "WRF regional data source is unconfigured."
                    )
                )
            }
            override suspend fun getNWPModelComparison(latitude: Double, longitude: Double, leadHours: Int): ResultState<NWPModelComparison> {
                return ResultState.Success(
                    NWPModelComparison(
                        latitude = latitude,
                        longitude = longitude,
                        forecastLeadHours = leadHours,
                        modelsStatus = mapOf("GFS_0p25" to "AVAILABLE", "WRF_REGIONAL" to "UNAVAILABLE"),
                        models = emptyMap(),
                        variablesCompared = emptyList(),
                        divergenceAnalysis = com.weathergpt.domain.model.nwp.DivergenceAnalysis(
                            variable = "temperature_2m",
                            units = "°C",
                            modelsCompared = listOf("GFS", "ECMWF"),
                            meanForecast = 30.5,
                            stdDev = 0.8,
                            divergenceRatio = 0.12,
                            agreementCategory = "HIGH",
                            isActionable = true
                        )
                    )
                )
            }
            override suspend fun getPointWeatherMap(latitude: Double, longitude: Double): ResultState<MapSpecification> {
                return ResultState.Success(
                    MapSpecification(
                        id = "map-pt-001",
                        title = "Live Point Map",
                        viewport = MapViewport(centerLatitude = latitude, centerLongitude = longitude, zoom = 6.0),
                        layers = listOf(
                            MapLayer(id = "layer_radar", name = "Radar", type = "raster", visible = true)
                        ),
                        legend = listOf(
                            LegendItem(label = "Light Rain", color = "#81D4FA")
                        )
                    )
                )
            }
            override suspend fun getWarningMap(warningGeometry: JsonObject, alertId: String, event: String, severity: String) = throw NotImplementedError()
            override suspend fun getRiskMap(latitude: Double?, longitude: Double?, districtCode: String?, observedRainMm: Double?, observedWindKmh: Double?): ResultState<MapSpecification> {
                return ResultState.Success(
                    MapSpecification(
                        id = "map-risk-001",
                        title = "Risk Map",
                        viewport = MapViewport(centerLatitude = latitude ?: 28.61, centerLongitude = longitude ?: 77.20, zoom = 7.0),
                        layers = emptyList(),
                        legend = emptyList()
                    )
                )
            }
            override suspend fun evaluateDecision(question: String, locationName: String?, latitude: Double?, longitude: Double?, requestedTime: String?, domain: String?, context: Map<String, String>?): ResultState<com.weathergpt.domain.model.decision.NirnayCard> = throw NotImplementedError()
            override suspend fun getFarmerProfile(): ResultState<com.weathergpt.domain.model.farmer.FarmerProfile> = ResultState.Success(com.weathergpt.domain.model.farmer.FarmerProfile())
            override suspend fun saveFarmerProfile(profile: com.weathergpt.domain.model.farmer.FarmerProfile): ResultState<Unit> = ResultState.Success(Unit)

            override suspend fun getAnalystRiskMatrix(
                districtName: String,
                precip24hPercentile: Double,
                exposureIndex: Double,
                vulnerabilityIndex: Double,
                hazardType: String
            ): ResultState<OperationalRisk> {
                return analystRiskMatrixResult ?: ResultState.Success(
                    OperationalRisk(
                        district = districtName,
                        hazardType = hazardType,
                        hazardIndex = 6.5,
                        exposureIndex = exposureIndex,
                        vulnerabilityIndex = vulnerabilityIndex,
                        compositeRiskScore = 7.05,
                        riskLevel = "HIGH",
                        actionPriority = "Immediate drainage clearance"
                    )
                )
            }

            override suspend fun getClimateTrends(
                latitude: Double,
                longitude: Double,
                location: String?,
                variable: String
            ): ResultState<com.weathergpt.domain.model.climate.ClimateTrends> {
                return climateTrendsResult ?: ResultState.Success(
                    com.weathergpt.domain.model.climate.ClimateTrends(
                        location = location ?: "Delhi",
                        latitude = latitude,
                        longitude = longitude,
                        variable = variable,
                        trendSlope = 0.024,
                        pValue = 0.012,
                        isSignificant = true,
                        direction = "INCREASING",
                        sampleSize = 30,
                        period = "1991-2020",
                        method = "Mann-Kendall / Sen's Slope"
                    )
                )
            }

            override suspend fun getClimateNormals(
                latitude: Double,
                longitude: Double,
                location: String?,
                month: Int?
            ): ResultState<com.weathergpt.domain.model.climate.ClimateNormals> {
                return climateNormalsResult ?: ResultState.Success(
                    com.weathergpt.domain.model.climate.ClimateNormals(
                        location = location ?: "Delhi",
                        latitude = latitude,
                        longitude = longitude,
                        month = month ?: 9,
                        normalRainfallMm = 125.0,
                        actualRainfallMm = 110.0,
                        rainfallAnomalyPct = -12.0,
                        normalTempC = 34.2,
                        actualTempC = 33.8,
                        tempAnomalyC = -0.4,
                        category = "Normal",
                        source = "IMD_CLIMATOLOGICAL_NORMALS_1991_2020",
                        referencePeriod = "1991-2020"
                    )
                )
            }
        }
    }
}

    @Test
    fun chatViewModel_successFlow_storesUserAndAssistantMessage() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = ChatViewModel(repository = repo, locationManager = locManager)

        vm.setInputText("Is today suitable for spraying?")
        vm.sendMessage()
        advanceUntilIdle()

        assertEquals(2, vm.uiState.value.messages.size)
        assertTrue(vm.uiState.value.messages[0] is ChatMessage.User)
        assertTrue(vm.uiState.value.messages[1] is ChatMessage.Assistant)

        val assistantMsg = (vm.uiState.value.messages[1] as ChatMessage.Assistant)
        assertEquals("Clear skies expected with light breeze.", assistantMsg.response.answer)
        assertEquals("Orange", assistantMsg.response.alert?.level)
    }

    @Test
    fun chatViewModel_errorAndRetry_handlesFailureAndPreservesQuery() = runTest {
        val repo = createFakeRepository(
            shouldFailChat = true,
            chatError = AppError.ServerUnavailable(503, "req-retry-99")
        )
        val locManager = SharedLocationManager()
        val vm = ChatViewModel(repository = repo, locationManager = locManager)

        vm.setInputText("What is the monsoon forecast?")
        vm.sendMessage()
        advanceUntilIdle()

        assertTrue(vm.chatState.value is ResultState.Error)
        val err = (vm.chatState.value as ResultState.Error).error
        assertTrue(err.isRetryable)
        assertEquals("What is the monsoon forecast?", vm.uiState.value.lastFailedQuery)

        // Verify exactly ONE user message exists after the initial failed send
        assertEquals(1, vm.uiState.value.messages.size)
        assertTrue(vm.uiState.value.messages[0] is ChatMessage.User)

        // Call retryLast()
        vm.retryLast()
        advanceUntilIdle()

        // Verify retry did NOT add a duplicate user message
        assertEquals(1, vm.uiState.value.messages.size)
    }

    @Test
    fun chatViewModel_preventDuplicateSubmissionsWhileSending() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = ChatViewModel(repository = repo, locationManager = locManager)

        vm.setInputText("क्या में बिहार जा सकती हु कल")
        vm.sendMessage()
        // Immediate second call while sending
        vm.sendMessage()
        advanceUntilIdle()

        // Should contain exactly ONE user message and ONE assistant message
        val userMessages = vm.uiState.value.messages.filterIsInstance<ChatMessage.User>()
        assertEquals(1, userMessages.size)
        assertEquals("क्या में बिहार जा सकती हु कल", userMessages[0].text)
    }

    @Test
    fun sharedLocationManager_updatesLocationAndResolvesHierarchy() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()

        locManager.resolveLocationHierarchy(repo)
        val loc = locManager.locationState.value

        assertEquals("New Delhi", loc.districtName)
        assertEquals("Delhi", loc.stateName)
        assertEquals("Connaught Place, New Delhi, Delhi", loc.formattedAddress)
    }

    @Test
    fun homeViewModel_synchronizesWithLocationAndAlerts() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = HomeViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.weatherState.value is ResultState.Success)
        val weather = (vm.weatherState.value as ResultState.Success).data
        assertEquals(31.5, weather.temperatureC, 0.1)
        assertEquals(1, vm.uiState.value.activeAlertsCount)
        assertEquals("Heavy Rainfall Warning", vm.uiState.value.topAlertHeadline)
        assertEquals("Orange", vm.uiState.value.topAlertLevel)
        assertEquals("Garvit", vm.uiState.value.userName)
    }

    @Test
    fun homeViewModel_errorAndOfflineState() = runTest {
        val repo = object : WeatherGPTRepository by createFakeRepository() {
            override suspend fun getCurrentWeather(latitude: Double, longitude: Double): ResultState<CurrentWeather> {
                return ResultState.Error(AppError.NetworkUnavailable())
            }
        }
        val locManager = SharedLocationManager()
        val vm = HomeViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.weatherState.value is ResultState.Error)
        val err = (vm.weatherState.value as ResultState.Error).error
        assertTrue(err is AppError.NetworkUnavailable)
        assertTrue(err.isRetryable)
        assertEquals("ERR_OFFLINE_NO_INTERNET", err.errorCode)
    }

    @Test
    fun homeViewModel_locationChangeUpdatesWeather() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = HomeViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        vm.setLocation("Surat, Gujarat", 21.1702, 72.8311)
        advanceUntilIdle()

        assertEquals("Surat, Gujarat", vm.uiState.value.locationName)
        assertEquals(21.1702, vm.uiState.value.latitude, 0.001)
        assertEquals(72.8311, vm.uiState.value.longitude, 0.001)
        assertTrue(vm.weatherState.value is ResultState.Success)
    }

    @Test
    fun brainSelectionViewModel_selectsAllBrainsAndMapsDomain() = runTest {
        val brainManager = com.weathergpt.core.brain.SharedBrainManager()
        val vm = BrainSelectionViewModel(brainManager = brainManager)

        assertEquals(IntelligenceBrain.AUTO, vm.selectedBrain.value)
        assertEquals(DomainBrain.AUTO, brainManager.getDomainBrain())

        vm.selectBrain(IntelligenceBrain.GENERAL)
        assertEquals(IntelligenceBrain.GENERAL, vm.selectedBrain.value)
        assertEquals(DomainBrain.GENERAL, brainManager.getDomainBrain())

        vm.selectBrain(IntelligenceBrain.FARMER)
        assertEquals(IntelligenceBrain.FARMER, vm.selectedBrain.value)
        assertEquals(DomainBrain.FARMER, brainManager.getDomainBrain())

        vm.selectBrain(IntelligenceBrain.RESEARCHER)
        assertEquals(IntelligenceBrain.RESEARCHER, vm.selectedBrain.value)
        assertEquals(DomainBrain.RESEARCHER, brainManager.getDomainBrain())

        vm.selectBrain(IntelligenceBrain.ANALYST)
        assertEquals(IntelligenceBrain.ANALYST, vm.selectedBrain.value)
        assertEquals(DomainBrain.ANALYST, brainManager.getDomainBrain())
    }

    @Test
    fun sharedBrainManager_synchronizesWithHomeAndChat() = runTest {
        val brainManager = com.weathergpt.core.brain.SharedBrainManager()
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()

        val brainVm = BrainSelectionViewModel(brainManager = brainManager)
        val homeVm = HomeViewModel(repository = repo, locationManager = locManager, brainManager = brainManager)
        val chatVm = ChatViewModel(repository = repo, locationManager = locManager, brainManager = brainManager)
        advanceUntilIdle()

        assertEquals(IntelligenceBrain.AUTO, homeVm.uiState.value.selectedBrain)
        assertEquals(DomainBrain.AUTO, chatVm.uiState.value.selectedBrain)

        // Select FARMER in Brain Selection
        brainVm.selectBrain(IntelligenceBrain.FARMER)
        advanceUntilIdle()

        // Home and Chat must immediately reflect FARMER
        assertEquals(IntelligenceBrain.FARMER, homeVm.uiState.value.selectedBrain)
        assertEquals(DomainBrain.FARMER, chatVm.uiState.value.selectedBrain)

        // Select ANALYST in Chat
        chatVm.selectBrain(DomainBrain.ANALYST)
        advanceUntilIdle()

        // Brain Selection and Home must reflect ANALYST
        assertEquals(IntelligenceBrain.ANALYST, brainVm.selectedBrain.value)
        assertEquals(IntelligenceBrain.ANALYST, homeVm.uiState.value.selectedBrain)
    }

    @Test
    fun homeViewModel_brainSelection() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val brainManager = com.weathergpt.core.brain.SharedBrainManager()
        val vm = HomeViewModel(repository = repo, locationManager = locManager, brainManager = brainManager)

        assertEquals(IntelligenceBrain.AUTO, vm.uiState.value.selectedBrain)
        vm.selectBrain(IntelligenceBrain.FARMER)
        assertEquals(IntelligenceBrain.FARMER, vm.uiState.value.selectedBrain)
    }

    @Test
    fun weatherViewModel_loadsCurrentForecastAndIntelligence() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = WeatherViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.currentWeatherState.value is ResultState.Success)
        val current = (vm.currentWeatherState.value as ResultState.Success).data
        assertEquals(31.5, current.temperatureC, 0.1)
        assertEquals("Open-Meteo", current.provider)
        assertEquals("IMD", current.authority)

        assertTrue(vm.forecastState.value is ResultState.Success)
        val forecast = (vm.forecastState.value as ResultState.Success).data
        assertEquals(1, forecast.dailyForecast.size)
        assertEquals("Sunny", forecast.dailyForecast[0].dominantCondition)

        assertTrue(vm.intelligenceState.value is ResultState.Success)
        val intel = (vm.intelligenceState.value as ResultState.Success).data
        assertEquals("HIGH", intel.dataQuality)
    }

    @Test
    fun weatherViewModel_intervalTabSwitching() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = WeatherViewModel(repository = repo, locationManager = locManager)

        assertEquals(com.weathergpt.presentation.weather.ForecastInterval.HOURLY, vm.uiState.value.selectedInterval)
        vm.setInterval(com.weathergpt.presentation.weather.ForecastInterval.THREE_DAYS)
        assertEquals(com.weathergpt.presentation.weather.ForecastInterval.THREE_DAYS, vm.uiState.value.selectedInterval)
        vm.setInterval(com.weathergpt.presentation.weather.ForecastInterval.TEN_DAYS)
        assertEquals(com.weathergpt.presentation.weather.ForecastInterval.TEN_DAYS, vm.uiState.value.selectedInterval)
    }

    @Test
    fun weatherViewModel_errorAndOfflineState() = runTest {
        val repo = object : WeatherGPTRepository by createFakeRepository() {
            override suspend fun getCurrentWeather(latitude: Double, longitude: Double): ResultState<CurrentWeather> {
                return ResultState.Error(AppError.NetworkUnavailable())
            }
        }
        val locManager = SharedLocationManager()
        val vm = WeatherViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.currentWeatherState.value is ResultState.Error)
        val err = (vm.currentWeatherState.value as ResultState.Error).error
        assertTrue(err is AppError.NetworkUnavailable)
        assertTrue(err.isRetryable)
        assertEquals("ERR_OFFLINE_NO_INTERNET", err.errorCode)
    }

    @Test
    fun weatherViewModel_locationChangeTriggersReload() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = WeatherViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        vm.setLocation("Jhansi, Uttar Pradesh", 25.4484, 78.5685)
        advanceUntilIdle()

        assertEquals("Jhansi, Uttar Pradesh", vm.uiState.value.locationName)
        assertEquals(25.4484, vm.uiState.value.latitude, 0.001)
        assertEquals(78.5685, vm.uiState.value.longitude, 0.001)
        assertTrue(vm.currentWeatherState.value is ResultState.Success)
    }

    @Test
    fun alertsViewModel_loadsRealAlertsAndFiltersByCategory() = runTest {
        val repo = object : WeatherGPTRepository by createFakeRepository() {
            override suspend fun getWeatherAlerts(district: String?, latitude: Double?, longitude: Double?): ResultState<WeatherAlertsReport> {
                return ResultState.Success(
                    WeatherAlertsReport(
                        authority = "IMD",
                        retrievedAt = "2026-08-31T12:00:00Z",
                        activeAlertsCount = 3,
                        alerts = listOf(
                            OfficialAlert(
                                alertId = "ALERT-001",
                                warningColor = "Orange",
                                hazard = "Heavy Rainfall Warning",
                                severity = "Severe",
                                areaDescription = "Surat District",
                                headline = "Heavy Rainfall Warning",
                                description = "Heavy to very heavy rainfall expected across low-lying areas",
                                effectiveFrom = "2026-08-31T12:00:00Z",
                                expiresAt = "2026-09-01T12:00:00Z",
                                instructions = "Stay indoors and avoid waterlogged roads"
                            ),
                            OfficialAlert(
                                alertId = "ALERT-002",
                                warningColor = "Yellow",
                                hazard = "Crop Advisory",
                                severity = "Moderate",
                                areaDescription = "Surat Rural",
                                headline = "Pest Alert & Crop Protection",
                                description = "Postpone fertilizer application and pesticide spraying for cotton crop",
                                effectiveFrom = "2026-08-31T12:00:00Z",
                                expiresAt = "2026-09-01T12:00:00Z",
                                instructions = "Drain excess water from crop fields"
                            ),
                            OfficialAlert(
                                alertId = "ALERT-003",
                                warningColor = "Red",
                                hazard = "Disaster Management Advisory",
                                severity = "Extreme",
                                areaDescription = "Surat Coastal",
                                headline = "NDMA Evacuation Order",
                                description = "District Administration orders immediate evacuation of coastal settlements",
                                effectiveFrom = "2026-08-31T12:00:00Z",
                                expiresAt = "2026-09-01T12:00:00Z",
                                instructions = "Move to designated relief shelters"
                            )
                        )
                    )
                )
            }
        }
        val locManager = SharedLocationManager()
        val vm = AlertsViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.alertsState.value is ResultState.Success)
        val report = (vm.alertsState.value as ResultState.Success).data
        assertEquals(3, report.activeAlertsCount)

        // All category: must show all 3 alerts
        vm.selectCategoryIndex(0)
        assertEquals(3, vm.getFilteredAlerts(report).size)

        // Weather category: must only show Rainfall alert (ALERT-001)
        vm.selectCategoryIndex(1)
        val weatherAlerts = vm.getFilteredAlerts(report)
        assertEquals(1, weatherAlerts.size)
        assertEquals("ALERT-001", weatherAlerts[0].alertId)

        // Agriculture category: must only show Crop Advisory (ALERT-002)
        vm.selectCategoryIndex(2)
        val agriAlerts = vm.getFilteredAlerts(report)
        assertEquals(1, agriAlerts.size)
        assertEquals("ALERT-002", agriAlerts[0].alertId)

        // Government category: must only show NDMA Evacuation Order (ALERT-003)
        vm.selectCategoryIndex(3)
        val govtAlerts = vm.getFilteredAlerts(report)
        assertEquals(1, govtAlerts.size)
        assertEquals("ALERT-003", govtAlerts[0].alertId)
    }

    @Test
    fun alertsViewModel_offlineErrorHandling() = runTest {
        val repo = object : WeatherGPTRepository by createFakeRepository() {
            override suspend fun getWeatherAlerts(district: String?, latitude: Double?, longitude: Double?): ResultState<WeatherAlertsReport> {
                return ResultState.Error(AppError.NetworkUnavailable())
            }
        }
        val locManager = SharedLocationManager()
        val vm = AlertsViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.alertsState.value is ResultState.Error)
        val err = (vm.alertsState.value as ResultState.Error).error
        assertTrue(err is AppError.NetworkUnavailable)
        assertTrue(err.isRetryable)
    }

    @Test
    fun farmerProfileViewModel_loadsIrrigationAndSprayAdvisories() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = FarmerProfileViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.irrigationState is ResultState.Success)
        assertTrue(vm.uiState.value.sprayState is ResultState.Success)

        val irr = (vm.uiState.value.irrigationState as ResultState.Success).data
        assertEquals("IRRIGATE", irr.action)
        assertEquals("high", irr.urgency)
        assertEquals(20.0, irr.metrics.netDeficitMm, 0.01)

        val spray = (vm.uiState.value.sprayState as ResultState.Success).data
        assertTrue(spray.isSuitable)
    }

    @Test
    fun farmerProfileViewModel_cropSelectionAndValidation() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = FarmerProfileViewModel(repository = repo, locationManager = locManager)

        vm.setCrop("Cotton")
        assertEquals("Cotton", vm.uiState.value.cropName)

        vm.setCropStage("Flowering")
        assertEquals("Flowering", vm.uiState.value.cropStage)

        vm.setSoilType("Black Cotton")
        assertEquals("Black Cotton", vm.uiState.value.soilType)

        // Invalid area
        vm.setFieldArea("-1.0")
        assertFalse(vm.saveProfile())
        assertNotNull(vm.uiState.value.validationError)

        // Valid area
        vm.setFieldArea("3.5")
        assertTrue(vm.saveProfile())
        assertNull(vm.uiState.value.validationError)
        assertTrue(vm.uiState.value.isSavedSuccessfully)
    }

    @Test
    fun dataViewModel_loadsGFSAndComparison() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = DataViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.gfsGridState is ResultState.Success)
        val gfs = (vm.uiState.value.gfsGridState as ResultState.Success).data
        assertEquals("GFS", gfs.model)
        assertEquals(30.2, gfs.temperature2mC, 0.1)

        assertTrue(vm.uiState.value.wrfGridState is ResultState.Success)
        val wrf = (vm.uiState.value.wrfGridState as ResultState.Success).data
        assertEquals("WRF_REGIONAL", wrf.model)
        assertEquals("UNAVAILABLE", wrf.status)

        assertTrue(vm.uiState.value.nwpComparisonState is ResultState.Success)
        assertEquals(0.12, vm.uiState.value.divergenceRatio, 0.001)

        vm.selectModel("WRF (Regional)")
        assertEquals("WRF (Regional)", vm.uiState.value.selectedModel)
    }

    @Test
    fun analystDashboardViewModel_loadsRiskAssessmentAndGISAnalysis() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = AnalystDashboardViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.riskAssessmentState is ResultState.Success)
        assertTrue(vm.uiState.value.gisAnalysisState is ResultState.Success)
        assertEquals(7.05, vm.uiState.value.compositeRiskScore, 0.01)
        assertEquals("HIGH", vm.uiState.value.riskCategory)
    }

    @Test
    fun analystDashboardViewModel_locationSwitchRefreshesAllMetrics() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = AnalystDashboardViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertEquals("Surat", vm.uiState.value.districtName)
        assertEquals(21.1702, vm.uiState.value.latitude, 0.001)

        // Select New Delhi from availableLocations
        val newDelhi = vm.availableLocations.first { it.districtName == "New Delhi" }
        vm.selectPredefinedLocation(newDelhi)
        advanceUntilIdle()

        assertEquals("New Delhi", vm.uiState.value.districtName)
        assertEquals(28.6139, vm.uiState.value.latitude, 0.001)
        assertEquals(77.2090, vm.uiState.value.longitude, 0.001)
        assertTrue(vm.uiState.value.riskAssessmentState is ResultState.Success)
        assertTrue(vm.uiState.value.gisAnalysisState is ResultState.Success)
        assertTrue(vm.uiState.value.weatherState is ResultState.Success)
        assertTrue(vm.uiState.value.gfsState is ResultState.Success)
    }

    @Test
    fun mapViewModel_loadsMapSpecFromRealApi() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = MapViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertFalse(vm.uiState.value.isLoading)
        assertNotNull(vm.uiState.value.mapSpec)
        assertEquals("Live Point Map", vm.uiState.value.mapSpec.title)

        vm.setLayer(WeatherMapLayer.RISK)
        advanceUntilIdle()
        assertEquals("Risk Map", vm.uiState.value.mapSpec.title)
    }

    @Test
    fun appError_unifiedContractsProperties() {
        val offline = AppError.NetworkUnavailable()
        assertTrue(offline.isRetryable)
        assertEquals("ERR_OFFLINE_NO_INTERNET", offline.errorCode)

        val timeout = AppError.Timeout()
        assertTrue(timeout.isRetryable)
        assertEquals("ERR_NETWORK_TIMEOUT", timeout.errorCode)

        val rateLimit = AppError.RateLimited(429, 30L, "req-rate-1")
        assertTrue(rateLimit.isRetryable)
        assertEquals("ERR_RATE_LIMITED_429", rateLimit.errorCode)
        assertEquals("req-rate-1", rateLimit.errorRequestId)

        val validation = AppError.ValidationError(
            statusCode = 422,
            problemDetails = ProblemDetails(title = "Unprocessable Entity", requestId = "req-val-1")
        )
        assertFalse(validation.isRetryable)
        assertEquals("ERR_VALIDATION_FAILED_422", validation.errorCode)
        assertEquals("req-val-1", validation.errorRequestId)
    }

    @Test
    fun profileViewModel_initialStateAndLocationSelection() = runTest {
        val locManager = SharedLocationManager()
        val vm = ProfileViewModel(locationManager = locManager)
        val state = vm.uiState.value
        assertEquals("Garvit Mishra", state.userName)
        assertEquals("Surat, Gujarat", state.primaryLocation)
        assertEquals(11, state.savedLocationsCount)

        val newDelhi = vm.availableLocations.first { it.districtName == "New Delhi" }
        vm.selectLocation(newDelhi)
        advanceUntilIdle()

        assertEquals("New Delhi, Delhi", vm.uiState.value.primaryLocation)
        assertEquals("New Delhi, Delhi", locManager.locationState.value.formattedAddress)
    }

    @Test
    fun homeViewModel_selectPredefinedLocation_updatesStateAndLocationManager() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val vm = HomeViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        val mumbai = vm.availableLocations.first { it.districtName == "Mumbai" }
        vm.selectPredefinedLocation(mumbai)
        advanceUntilIdle()

        assertEquals("Mumbai, Maharashtra", vm.uiState.value.locationName)
        assertEquals(19.0760, vm.uiState.value.latitude, 0.001)
        assertEquals(72.8777, vm.uiState.value.longitude, 0.001)
    }

    @Test
    fun settingsViewModel_preferencesAndValidation() = runTest {
        val settingsManager = com.weathergpt.core.settings.SharedSettingsManager()
        val vm = SettingsViewModel(settingsManager = settingsManager)

        vm.setLanguage(com.weathergpt.core.settings.AppLanguage.HINDI)
        assertEquals(com.weathergpt.core.settings.AppLanguage.HINDI, vm.uiState.value.language)
        assertEquals("हिन्दी", vm.uiState.value.selectedLanguage)

        vm.setLanguage(com.weathergpt.core.settings.AppLanguage.ENGLISH)
        assertEquals(com.weathergpt.core.settings.AppLanguage.ENGLISH, vm.uiState.value.language)
        assertEquals("English", vm.uiState.value.selectedLanguage)

        vm.setUnits(com.weathergpt.core.settings.UnitSystem.IMPERIAL)
        assertEquals(com.weathergpt.core.settings.UnitSystem.IMPERIAL, vm.uiState.value.unitSystem)
        assertEquals("Imperial (°F, mph)", vm.uiState.value.selectedUnits)

        vm.toggleNotifications(false)
        assertFalse(vm.uiState.value.notificationsEnabled)

        // Invalid URL
        val invalidSuccess = vm.updateBackendUrl("ftp://invalid-url", null)
        assertFalse(invalidSuccess)
        assertNotNull(vm.uiState.value.urlValidationError)

        // Clear validation error
        vm.clearValidationError()
        assertNull(vm.uiState.value.urlValidationError)
    }

    @Test
    fun profileViewModel_updateUserName() = runTest {
        val locManager = SharedLocationManager()
        val vm = ProfileViewModel(locationManager = locManager)

        vm.updateUserName("Vikram Patel")
        assertEquals("Vikram Patel", vm.uiState.value.userName)
    }

    @Test
    fun chatViewModel_textChatControls() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val brainManager = SharedBrainManager()
        val vm = ChatViewModel(
            repository = repo,
            locationManager = locManager,
            brainManager = brainManager
        )

        vm.setLanguage(com.weathergpt.domain.model.chat.ChatLanguage.HINDI)
        assertEquals(com.weathergpt.domain.model.chat.ChatLanguage.HINDI, vm.uiState.value.language)

        vm.selectBrain(com.weathergpt.domain.model.chat.DomainBrain.FARMER)
        assertEquals(com.weathergpt.domain.model.chat.DomainBrain.FARMER, vm.uiState.value.selectedBrain)

        vm.setInputText("गेहूं की सिंचाई कब करें?")
        assertEquals("गेहूं की सिंचाई कब करें?", vm.uiState.value.inputText)

        vm.sendMessage()
        advanceUntilIdle()

        assertEquals(2, vm.uiState.value.messages.size)
        assertTrue(vm.uiState.value.messages[0] is ChatMessage.User)
        assertTrue(vm.uiState.value.messages[1] is ChatMessage.Assistant)
    }

    @Test
    fun analystDashboardViewModel_liveRiskMatrixApiSuccess_updatesUiState() = runTest {
        val customRisk = OperationalRisk(
            district = "Pune",
            hazardType = "FLASH_FLOOD",
            hazardIndex = 8.1,
            exposureIndex = 7.4,
            vulnerabilityIndex = 6.2,
            compositeRiskScore = 7.35,
            riskLevel = "VERY_HIGH",
            actionPriority = "Deploy NDRF and evacuate low lying areas"
        )
        val repo = createFakeRepository(analystRiskMatrixResult = ResultState.Success(customRisk))
        val locManager = SharedLocationManager()
        val vm = AnalystDashboardViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.riskAssessmentState is ResultState.Success)
        assertEquals(7.35, vm.uiState.value.compositeRiskScore, 0.01)
        assertEquals("VERY_HIGH", vm.uiState.value.riskCategory)
        assertEquals("Deploy NDRF and evacuate low lying areas", vm.uiState.value.actionPriority)
    }

    @Test
    fun analystDashboardViewModel_riskMatrixApiFailure_setsErrorStateWithoutFakeNumbers() = runTest {
        val networkErr = AppError.NetworkUnavailable("Live risk matrix backend timeout")
        val repo = createFakeRepository(analystRiskMatrixResult = ResultState.Error(networkErr))
        val locManager = SharedLocationManager()
        val vm = AnalystDashboardViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.riskAssessmentState is ResultState.Error)
    }

    @Test
    fun dataViewModel_climateApisSuccess_updatesClimateState() = runTest {
        val customTrends = com.weathergpt.domain.model.climate.ClimateTrends(
            location = "Surat",
            latitude = 21.1702,
            longitude = 72.8311,
            variable = "rainfall",
            trendSlope = 0.035,
            pValue = 0.005,
            isSignificant = true,
            direction = "INCREASING",
            sampleSize = 30,
            period = "1991-2020",
            method = "Mann-Kendall / Sen's Slope"
        )
        val customNormals = com.weathergpt.domain.model.climate.ClimateNormals(
            location = "Surat",
            latitude = 21.1702,
            longitude = 72.8311,
            month = 9,
            normalRainfallMm = 180.0,
            actualRainfallMm = 210.0,
            rainfallAnomalyPct = 16.7,
            normalTempC = 33.5,
            actualTempC = 34.0,
            tempAnomalyC = 0.5,
            category = "Above Normal",
            source = "IMD_CLIMATOLOGICAL_NORMALS_1991_2020",
            referencePeriod = "1991-2020"
        )
        val repo = createFakeRepository(
            climateTrendsResult = ResultState.Success(customTrends),
            climateNormalsResult = ResultState.Success(customNormals)
        )
        val locManager = SharedLocationManager()
        val vm = DataViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertEquals(0.035, vm.uiState.value.historicalTrendSlope ?: 0.0, 0.001)
        assertEquals("INCREASING", vm.uiState.value.trendDirection)
        assertEquals(180.0, vm.uiState.value.normalRainfallMm ?: 0.0, 0.1)
        assertEquals(210.0, vm.uiState.value.actualRainfallMm ?: 0.0, 0.1)
        assertEquals(16.7, vm.uiState.value.rainfallAnomalyPct ?: 0.0, 0.1)
        assertTrue(vm.uiState.value.climateTrendsState is ResultState.Success)
        assertTrue(vm.uiState.value.climateNormalsState is ResultState.Success)
    }

    @Test
    fun dataViewModel_climateApisFailure_handlesGracefully() = runTest {
        val repo = createFakeRepository(
            climateTrendsResult = ResultState.Error(AppError.NetworkUnavailable("Trends offline")),
            climateNormalsResult = ResultState.Error(AppError.NetworkUnavailable("Normals offline"))
        )
        val locManager = SharedLocationManager()
        val vm = DataViewModel(repository = repo, locationManager = locManager)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.climateTrendsState is ResultState.Error)
        assertTrue(vm.uiState.value.climateNormalsState is ResultState.Error)
    }
}
