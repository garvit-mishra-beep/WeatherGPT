package com.weathergpt.presentation

import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.core.error.AppError
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.core.settings.AppLanguage
import com.weathergpt.core.settings.SharedSettingsManager
import com.weathergpt.core.settings.UnitSystem
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
import com.weathergpt.domain.model.gis.AdministrativeBoundary
import com.weathergpt.domain.model.gis.BoundaryUnit
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
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.presentation.chat.ChatViewModel
import com.weathergpt.presentation.farmer.FarmerProfileViewModel
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
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LocalizationTest {

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun createFakeRepository(
        onIrrigationAdvisory: ((cropName: String, cropStage: String, soilType: String) -> Unit)? = null
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
                return ResultState.Success(
                    ChatResponse(
                        responseId = "resp-001",
                        sessionId = query.sessionId,
                        brain = query.selectedBrain,
                        language = query.languagePreference.code,
                        createdAt = "2026-08-31T12:00:00Z",
                        summary = "Weather outlook summary",
                        answer = if (query.languagePreference == ChatLanguage.HINDI) "आज मौसम साफ रहेगा।" else "Clear skies expected with light breeze.",
                        data = null,
                        recommendation = null,
                        alert = null,
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
                        location = LocationCoordinates(latitude, longitude),
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
                        location = LocationCoordinates(latitude, longitude),
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
                        activeAlertsCount = 0,
                        alerts = emptyList()
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
                            location = LocationCoordinates(latitude, longitude),
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
                onIrrigationAdvisory?.invoke(cropName, cropStage, soilType)
                return ResultState.Success(
                    IrrigationAdvisory(
                        action = "IRRIGATE",
                        urgency = "high",
                        metrics = CropWaterBalanceMetrics(
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
                        country = BoundaryUnit(code = "IND", name = "India", level = "country", parentCode = null, areaSqkm = null),
                        state = BoundaryUnit(code = "IN-DL", name = "Delhi", level = "state", parentCode = "IND", areaSqkm = null),
                        district = BoundaryUnit(code = "IN-DL-ND", name = "New Delhi", level = "district", parentCode = "IN-DL", areaSqkm = null),
                        subdistrict = BoundaryUnit(code = "IN-DL-ND-CN", name = "Connaught Place", level = "sub_district", parentCode = "IN-DL-ND", areaSqkm = null)
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
                        divergenceAnalysis = DivergenceAnalysis(
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
        }
    }

    @Test
    fun testAppLanguageEnumValuesAndCodes() {
        assertEquals("en", AppLanguage.ENGLISH.code)
        assertEquals("hi", AppLanguage.HINDI.code)
        assertEquals("mr", AppLanguage.MARATHI.code)
        assertEquals("bn", AppLanguage.BENGALI.code)
        assertEquals("ta", AppLanguage.TAMIL.code)
        assertEquals("te", AppLanguage.TELUGU.code)
        assertEquals("gu", AppLanguage.GUJARATI.code)
        assertEquals("kn", AppLanguage.KANNADA.code)
        assertEquals("ml", AppLanguage.MALAYALAM.code)
        assertEquals("pa", AppLanguage.PUNJABI.code)

        assertEquals("English", AppLanguage.ENGLISH.nativeName)
        assertEquals("हिन्दी", AppLanguage.HINDI.nativeName)
        assertEquals("मराठी", AppLanguage.MARATHI.nativeName)
        assertEquals("বাংলা", AppLanguage.BENGALI.nativeName)
        assertEquals("தமிழ்", AppLanguage.TAMIL.nativeName)
        assertEquals("తెలుగు", AppLanguage.TELUGU.nativeName)
        assertEquals("ગુજરાતી", AppLanguage.GUJARATI.nativeName)
        assertEquals("ಕನ್ನಡ", AppLanguage.KANNADA.nativeName)
        assertEquals("മലയാളം", AppLanguage.MALAYALAM.nativeName)
        assertEquals("ਪੰਜਾਬੀ", AppLanguage.PUNJABI.nativeName)

        // Verify toChatLanguage mapping
        assertEquals(ChatLanguage.ENGLISH, AppLanguage.ENGLISH.toChatLanguage())
        assertEquals(ChatLanguage.HINDI, AppLanguage.HINDI.toChatLanguage())
        assertEquals(ChatLanguage.MARATHI, AppLanguage.MARATHI.toChatLanguage())
        assertEquals(ChatLanguage.BENGALI, AppLanguage.BENGALI.toChatLanguage())
        assertEquals(ChatLanguage.TAMIL, AppLanguage.TAMIL.toChatLanguage())
        assertEquals(ChatLanguage.TELUGU, AppLanguage.TELUGU.toChatLanguage())
        assertEquals(ChatLanguage.GUJARATI, AppLanguage.GUJARATI.toChatLanguage())
        assertEquals(ChatLanguage.KANNADA, AppLanguage.KANNADA.toChatLanguage())
        assertEquals(ChatLanguage.MALAYALAM, AppLanguage.MALAYALAM.toChatLanguage())
        assertEquals(ChatLanguage.PUNJABI, AppLanguage.PUNJABI.toChatLanguage())
    }

    @Test
    fun testChatLanguageEnumAllTenLanguages() {
        val languages = listOf("en", "hi", "mr", "bn", "ta", "te", "gu", "kn", "ml", "pa")
        for (code in languages) {
            val lang = ChatLanguage.fromCode(code)
            assertEquals(code, lang.code)
        }
        // Fallback test
        assertEquals(ChatLanguage.ENGLISH, ChatLanguage.fromCode("unknown_xyz"))
    }

    @Test
    fun testUnitSystemDisplayNames() {
        assertEquals("Metric (°C, km/h)", UnitSystem.METRIC.displayNameEn)
        assertEquals("मीट्रिक (°C, किमी/घंटा)", UnitSystem.METRIC.displayNameHi)
        assertEquals("Imperial (°F, mph)", UnitSystem.IMPERIAL.displayNameEn)
        assertEquals("इंपीरियल (°F, मील/घंटा)", UnitSystem.IMPERIAL.displayNameHi)
    }

    @Test
    fun testAllTenStringCatalogsParity() {
        val resDir = java.io.File("src/main/res")
        val baseStringsFile = java.io.File(resDir, "values/strings.xml")
        assertTrue("Base strings.xml must exist", baseStringsFile.exists())

        fun extractKeys(file: java.io.File): Set<String> {
            val content = file.readText()
            val pattern = java.util.regex.Pattern.compile("""<string\s+name="([^"]+)"""")
            val matcher = pattern.matcher(content)
            val keys = mutableSetOf<String>()
            while (matcher.find()) {
                matcher.group(1)?.let { keys.add(it) }
            }
            return keys
        }

        val baseKeys = extractKeys(baseStringsFile)
        assertTrue("Base strings.xml must have keys", baseKeys.isNotEmpty())

        val locales = listOf("hi", "mr", "bn", "ta", "te", "gu", "kn", "ml", "pa")
        for (loc in locales) {
            val locFile = java.io.File(resDir, "values-$loc/strings.xml")
            assertTrue("Locale catalog values-$loc/strings.xml must exist", locFile.exists())
            val locKeys = extractKeys(locFile)
            val missingKeys = baseKeys - locKeys
            assertTrue("values-$loc/strings.xml missing keys: $missingKeys", missingKeys.isEmpty())
        }
    }

    @Test
    fun testFarmerProfileViewModelIndicCropAndSoilNormalizationAllLanguages() = runTest {
        var capturedCrop: String? = null
        var capturedStage: String? = null
        var capturedSoil: String? = null

        val repo = createFakeRepository { crop, stage, soil ->
            capturedCrop = crop
            capturedStage = stage
            capturedSoil = soil
        }
        val locManager = SharedLocationManager()
        val viewModel = FarmerProfileViewModel(repo, locManager)

        // 1. Marathi (MR)
        viewModel.setCrop("गहू")
        viewModel.setCropStage("पेरणी / अंकुरण")
        viewModel.setSoilType("काळी कापूस माती")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("wheat", capturedCrop)
        assertEquals("initial", capturedStage)
        assertEquals("black_cotton", capturedSoil)

        // 2. Bengali (BN)
        viewModel.setCrop("ধান (চাল)")
        viewModel.setCropStage("গাছের বৃদ্ধি")
        viewModel.setSoilType("পলিমাটি / দোআঁশ")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("rice", capturedCrop)
        assertEquals("crop_development", capturedStage)
        assertEquals("alluvial_loam", capturedSoil)

        // 3. Tamil (TA)
        viewModel.setCrop("பருத்தி")
        viewModel.setCropStage("பூக்கும் பருவம்")
        viewModel.setSoilType("செம்மண்")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("cotton", capturedCrop)
        assertEquals("mid_season", capturedStage)
        assertEquals("red_sandy", capturedSoil)

        // 4. Telugu (TE)
        viewModel.setCrop("చెరకు")
        viewModel.setCropStage("పంట పక్వత / కోత")
        viewModel.setSoilType("బంకమట్టి నేల")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("sugarcane", capturedCrop)
        assertEquals("late_season", capturedStage)
        assertEquals("clay", capturedSoil)

        // 5. Gujarati (GU)
        viewModel.setCrop("મકાઈ")
        viewModel.setCropStage("વાવણી")
        viewModel.setSoilType("કાંપવાળી જમીન")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("maize", capturedCrop)
        assertEquals("initial", capturedStage)
        assertEquals("alluvial_loam", capturedSoil)

        // 6. Kannada (KN)
        viewModel.setCrop("ಸಾಸಿವೆ")
        viewModel.setCropStage("ಹೂ ಬಿಡುವ ಹಂತ")
        viewModel.setSoilType("ಕಪ್ಪು ಹತ್ತಿ ಮಣ್ಣು")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("mustard", capturedCrop)
        assertEquals("mid_season", capturedStage)
        assertEquals("black_cotton", capturedSoil)

        // 7. Malayalam (ML)
        viewModel.setCrop("നെല്ല്")
        viewModel.setCropStage("വിളവെഴുപ്പ് ഘട്ടം")
        viewModel.setSoilType("എക്കൽ മണ്ണ്")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("rice", capturedCrop)
        assertEquals("late_season", capturedStage)
        assertEquals("alluvial_loam", capturedSoil)

        // 8. Punjabi (PA)
        viewModel.setCrop("ਕਣਕ")
        viewModel.setCropStage("ਬਿਜਾਈ")
        viewModel.setSoilType("ਜਲੋਢ ਮਿੱਟੀ")
        viewModel.loadAdvisories()
        advanceUntilIdle()
        assertEquals("wheat", capturedCrop)
        assertEquals("initial", capturedStage)
        assertEquals("alluvial_loam", capturedSoil)
    }

    @Test
    fun testChatViewModelLanguageSynchronization() = runTest {
        val repo = createFakeRepository()
        val locManager = SharedLocationManager()
        val brainManager = SharedBrainManager()
        val settingsManager = SharedSettingsManager()

        val chatViewModel = ChatViewModel(
            repository = repo,
            locationManager = locManager,
            brainManager = brainManager,
            settingsManager = settingsManager
        )

        // Switch to Marathi in ChatViewModel -> updates settingsManager
        chatViewModel.setLanguage(ChatLanguage.MARATHI)
        assertEquals(ChatLanguage.MARATHI, chatViewModel.uiState.value.language)
        assertEquals(AppLanguage.MARATHI, settingsManager.appLanguage.value)

        // Switch to Tamil in settingsManager -> syncs to ChatViewModel
        settingsManager.setLanguage(AppLanguage.TAMIL)
        advanceUntilIdle()
        assertEquals(ChatLanguage.TAMIL, chatViewModel.uiState.value.language)

        // Switch to Bengali in settingsManager -> syncs to ChatViewModel
        settingsManager.setLanguage(AppLanguage.BENGALI)
        advanceUntilIdle()
        assertEquals(ChatLanguage.BENGALI, chatViewModel.uiState.value.language)
    }
}
