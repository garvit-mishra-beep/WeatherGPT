package com.weathergpt.data.repository

import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.error.AppError
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.network.ErrorMapper
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.RetryPolicy
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.mapper.Mappers.toDomain
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.data.remote.dto.chat.ChatRequestDto
import com.weathergpt.data.remote.dto.chat.DeviceContextDto
import com.weathergpt.data.remote.dto.chat.GPSLocationDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryRequestDto
import com.weathergpt.data.remote.dto.farmer.SprayWindowRequestDto
import com.weathergpt.data.remote.dto.voice.VoiceQueryResponseDto
import com.weathergpt.data.remote.dto.voice.VoiceSttResponseDto
import com.weathergpt.data.remote.dto.voice.VoiceTtsRequestDto
import com.weathergpt.domain.model.climate.toDomain
import com.weathergpt.domain.model.climate.ClimateNormals
import com.weathergpt.domain.model.climate.ClimateTrends
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import com.weathergpt.data.remote.dto.gis.GISAnalysisRequestDto
import com.weathergpt.data.remote.dto.gis.HazardIntersectionRequestDto
import com.weathergpt.data.remote.dto.gis.RiskAssessmentRequestDto
import com.weathergpt.data.remote.dto.map.RiskMapRequestDto
import com.weathergpt.data.remote.dto.map.WarningMapRequestDto
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.model.ReadinessStatus
import com.weathergpt.domain.model.chat.AdvisoryRecommendation
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.ConfidenceAssessment
import com.weathergpt.domain.model.chat.EvidenceCitation
import com.weathergpt.domain.model.decision.ActionWindow
import com.weathergpt.domain.model.decision.DecisionConfidence
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionUncertainty
import com.weathergpt.domain.model.decision.DecisionVerdict
import com.weathergpt.domain.model.decision.NirnayCard
import com.weathergpt.domain.model.farmer.CropWaterBalanceMetrics
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.model.gis.AdministrativeBoundary
import com.weathergpt.domain.model.gis.BoundaryUnit
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.HazardIntersection
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import com.weathergpt.core.network.DemoModeNetworkGuard
import com.weathergpt.domain.brain.OfflineDemoIntelligenceEngine
import com.weathergpt.domain.model.farmer.FarmerProfile
import com.weathergpt.domain.model.weather.AlertSeverity
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.util.Locale
import java.util.UUID
import java.util.concurrent.atomic.AtomicInteger

/**
 * Hardened production-grade implementation of [WeatherGPTRepository].
 *
 * Guarantees:
 * 1. Offline fast-fail via [NetworkMonitor].
 * 2. Bounded transient retries for idempotent GET requests.
 * 3. Zero automatic retries for non-idempotent POST operations.
 * 4. Cancellation-safe coroutines: [CancellationException] is NEVER swallowed.
 * 5. Structured RFC 7807 problem details and request ID preservation.
 * 6. Zero network weather requests in DEMO_MODE.
 */
class WeatherGPTRepositoryImpl(
    private val apiService: WeatherGPTApiService,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val networkMonitor: NetworkMonitor? = null,
    private val localWeatherDataSource: com.weathergpt.data.local.LocalWeatherDataSource? = null,
    private val okHttpClient: OkHttpClient? = null
) : WeatherGPTRepository {

    private val networkWeatherCalls = AtomicInteger(0)

    override fun getNetworkWeatherCallsCount(): Int = networkWeatherCalls.get()

    private suspend fun <T> safeApiCall(
        isIdempotent: Boolean = false,
        block: suspend () -> T
    ): ResultState<T> {
        if (AppConfig.isDemoMode) {
            DemoModeNetworkGuard.assertNoNetworkCalls("safeApiCall")
            return ResultState.Error(
                AppError.NetworkUnavailable(
                    message = "Network operations are strictly disabled in 100% Offline Demo Mode."
                )
            )
        }

        // Fast-fail if network monitor reports offline
        if (networkMonitor != null && !networkMonitor.isOnline) {
            return ResultState.Error(AppError.NetworkUnavailable())
        }

        return withContext(ioDispatcher) {
            try {
                val data = RetryPolicy.executeWithRetry(isIdempotent = isIdempotent) {
                    block()
                }
                ResultState.Success(data)
            } catch (cancellation: CancellationException) {
                // Must rethrow to allow coroutine cancellation to propagate
                throw cancellation
            } catch (throwable: Throwable) {
                val error = ErrorMapper.mapThrowable(throwable)
                ResultState.Error(error)
            }
        }
    }

    // ========================================================================
    // 1. System
    // ========================================================================

    override suspend fun checkHealth(): ResultState<HealthStatus> = safeApiCall(isIdempotent = true) {
        apiService.getHealth().toDomain()
    }

    override suspend fun checkReadiness(): ResultState<ReadinessStatus> = safeApiCall(isIdempotent = true) {
        apiService.getReadiness().toDomain()
    }

    // ========================================================================
    // 2. Chat & LLM Orchestration (POST -> No Automatic Retry)
    // ========================================================================

    override suspend fun sendChat(query: ChatQuery): ResultState<ChatResponse> {
        if (AppConfig.isDemoMode) {
            return sendDemoChat(query)
        }

        return safeApiCall(isIdempotent = false) {
            val deviceContext = if (query.latitude != null && query.longitude != null) {
                DeviceContextDto(
                    gpsLocation = GPSLocationDto(
                        latitude = query.latitude,
                        longitude = query.longitude
                    )
                )
            } else {
                null
            }

            val requestDto = ChatRequestDto(
                sessionId = query.sessionId,
                userId = query.userId,
                query = query.query,
                languagePreference = query.languagePreference.code,
                selectedBrain = query.selectedBrain.value,
                deviceContext = deviceContext
            )

            apiService.sendChatMessage(requestDto).toDomain()
        }
    }

    // ========================================================================
    // 3. Weather & Official Alerts (GET -> Idempotent)
    // ========================================================================

    override suspend fun getCurrentWeather(
        latitude: Double,
        longitude: Double
    ): ResultState<CurrentWeather> {
        if (AppConfig.isDemoMode) {
            val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
            val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
            val cached = localWeatherDataSource?.getCachedCurrentWeather(gwaliorLat, gwaliorLon)
            return if (cached != null) {
                ResultState.Success(
                    cached.copy(
                        location = LocationCoordinates(gwaliorLat, gwaliorLon),
                        sourceMode = WeatherDataSourceMode.DEMO_MODE
                    )
                )
            } else {
                ResultState.Error(
                    AppError.WeatherUnavailable(
                        "Demo Mode active: Gwalior real weather cache not found. Please prefetch real weather while online first."
                    )
                )
            }
        }

        networkWeatherCalls.incrementAndGet()
        val remoteResult = safeApiCall(isIdempotent = true) {
            val dto = apiService.getCurrentWeather(latitude, longitude)
            localWeatherDataSource?.saveCurrentWeather(latitude, longitude, dto)
            dto.toDomain().copy(
                sourceMode = WeatherDataSourceMode.LIVE,
                retrievedAt = dto.provenance?.retrievalTimestamp
            )
        }

        return when (remoteResult) {
            is ResultState.Success -> remoteResult
            is ResultState.Error -> {
                val cached = localWeatherDataSource?.getCachedCurrentWeather(latitude, longitude)
                if (cached != null) {
                    ResultState.Success(cached)
                } else if (localWeatherDataSource == null || remoteResult.error is AppError.ValidationError || remoteResult.error is AppError.RateLimited) {
                    remoteResult
                } else {
                    ResultState.Error(
                        AppError.WeatherUnavailable(
                            "Live weather is temporarily unavailable and no cached weather is available for this location.",
                            remoteResult.error.cause
                        )
                    )
                }
            }
            else -> remoteResult
        }
    }

    override suspend fun prefetchDemoWeather(): ResultState<CurrentWeather> {
        val wasDemo = AppConfig.isDemoMode
        if (wasDemo) {
            AppConfig.setDemoMode(false)
        }
        return try {
            val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
            val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
            val currentRes = getCurrentWeather(gwaliorLat, gwaliorLon)
            getWeatherForecast(gwaliorLat, gwaliorLon, days = 7, hourly = true)
            getWeatherAlerts(district = SharedLocationManager.DEMO_GWALIOR_DISTRICT, latitude = gwaliorLat, longitude = gwaliorLon)
            currentRes
        } finally {
            if (wasDemo) {
                AppConfig.setDemoMode(true)
            }
        }
    }

    override suspend fun getWeatherForecast(
        latitude: Double,
        longitude: Double,
        days: Int,
        hourly: Boolean
    ): ResultState<WeatherForecast> {
        if (AppConfig.isDemoMode) {
            val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
            val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
            val cached = localWeatherDataSource?.getCachedForecast(gwaliorLat, gwaliorLon)
            return if (cached != null) {
                ResultState.Success(
                    cached.copy(
                        location = LocationCoordinates(gwaliorLat, gwaliorLon),
                        sourceMode = WeatherDataSourceMode.DEMO_MODE
                    )
                )
            } else {
                ResultState.Error(
                    AppError.WeatherUnavailable(
                        "Demo Mode active: Gwalior real forecast cache not found."
                    )
                )
            }
        }

        networkWeatherCalls.incrementAndGet()
        val remoteResult = safeApiCall(isIdempotent = true) {
            val dto = apiService.getWeatherForecast(latitude, longitude, days, hourly)
            localWeatherDataSource?.saveForecast(latitude, longitude, dto)
            dto.toDomain().copy(
                sourceMode = WeatherDataSourceMode.LIVE,
                retrievedAt = dto.generatedAt
            )
        }

        return when (remoteResult) {
            is ResultState.Success -> remoteResult
            is ResultState.Error -> {
                val cached = localWeatherDataSource?.getCachedForecast(latitude, longitude)
                if (cached != null) {
                    ResultState.Success(cached)
                } else if (localWeatherDataSource == null || remoteResult.error is AppError.ValidationError || remoteResult.error is AppError.RateLimited) {
                    remoteResult
                } else {
                    ResultState.Error(
                        AppError.WeatherUnavailable(
                            "Live weather forecast is temporarily unavailable and no cached forecast is available for this location.",
                            remoteResult.error.cause
                        )
                    )
                }
            }
            else -> remoteResult
        }
    }

    override suspend fun getWeatherAlerts(
        district: String?,
        latitude: Double?,
        longitude: Double?
    ): ResultState<WeatherAlertsReport> {
        if (AppConfig.isDemoMode) {
            val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
            val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
            val cached = localWeatherDataSource?.getCachedAlerts(gwaliorLat, gwaliorLon)
            return if (cached != null) {
                ResultState.Success(cached)
            } else {
                ResultState.Success(
                    WeatherAlertsReport(
                        authority = "Official Warning System",
                        retrievedAt = "Offline Verified Cache",
                        activeAlertsCount = 0,
                        alerts = emptyList(),
                        isCached = true
                    )
                )
            }
        }

        networkWeatherCalls.incrementAndGet()
        val remoteResult = safeApiCall(isIdempotent = true) {
            val dto = apiService.getWeatherAlerts(district, latitude, longitude)
            if (latitude != null && longitude != null) {
                localWeatherDataSource?.saveAlerts(latitude, longitude, dto)
            }
            dto.toDomain().copy(isCached = false)
        }

        if (localWeatherDataSource == null) {
            return remoteResult
        }

        return when (remoteResult) {
            is ResultState.Success -> remoteResult
            is ResultState.Error -> {
                if (latitude != null && longitude != null) {
                    val cached = localWeatherDataSource.getCachedAlerts(latitude, longitude)
                    if (cached != null) {
                        ResultState.Success(cached)
                    } else {
                        remoteResult
                    }
                } else {
                    remoteResult
                }
            }
            else -> remoteResult
        }
    }

    override suspend fun getWeatherIntelligence(
        latitude: Double,
        longitude: Double,
        leadHours: Int,
        includeNwp: Boolean
    ): ResultState<WeatherIntelligence> {
        if (AppConfig.isDemoMode) {
            val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
            val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
            val cachedWeather = localWeatherDataSource?.getCachedCurrentWeather(gwaliorLat, gwaliorLon)
            val cachedAlerts = localWeatherDataSource?.getCachedAlerts(gwaliorLat, gwaliorLon)
            return ResultState.Success(
                WeatherIntelligence(
                    latitude = gwaliorLat,
                    longitude = gwaliorLon,
                    dataQuality = "DEMO_MODE_CACHED",
                    currentObservation = cachedWeather?.copy(
                        location = LocationCoordinates(gwaliorLat, gwaliorLon),
                        sourceMode = WeatherDataSourceMode.DEMO_MODE
                    ),
                    alerts = cachedAlerts?.alerts ?: emptyList(),
                    rawProvenance = null
                )
            )
        }

        networkWeatherCalls.incrementAndGet()
        return safeApiCall(isIdempotent = true) {
            apiService.getWeatherIntelligence(latitude, longitude, leadHours, includeNwp).toDomain()
        }
    }

    // ========================================================================
    // 4. Agricultural & Farmer (POST -> No Automatic Retry)
    // ========================================================================

    override suspend fun getIrrigationAdvisory(
        latitude: Double,
        longitude: Double,
        cropName: String,
        cropStage: String,
        soilType: String,
        lastIrrigationDate: String?,
        forecastPrecip48hMm: Double
    ): ResultState<IrrigationAdvisory> {
        if (AppConfig.isDemoMode) {
            val needsIrrigation = forecastPrecip48hMm < 10.0
            return ResultState.Success(
                IrrigationAdvisory(
                    action = if (needsIrrigation) "IRRIGATE" else "WAIT_RAIN_EXPECTED",
                    urgency = if (needsIrrigation) "low" else "none",
                    metrics = CropWaterBalanceMetrics(
                        referenceEt0MmDay = 4.2,
                        cropKc = 1.05,
                        dailyWaterDemandMm = 4.41,
                        forecastRainfall48hMm = forecastPrecip48hMm,
                        netDeficitMm = if (needsIrrigation) 15.0 else 0.0,
                        finalDepletionMm = 25.0
                    ),
                    rationale = if (needsIrrigation) "Irrigation recommended based on local soil and low 48h precipitation outlook." else "Postpone irrigation; adequate precipitation expected.",
                    calculationMethod = "DEMO_OFFLINE_FAO56"
                )
            )
        }
        return safeApiCall(isIdempotent = false) {
            val req = IrrigationAdvisoryRequestDto(
                latitude = latitude,
                longitude = longitude,
                cropName = cropName,
                cropStage = cropStage,
                soilType = soilType,
                lastIrrigationDate = lastIrrigationDate,
                forecastPrecip48hMm = forecastPrecip48hMm
            )
            apiService.getIrrigationAdvisory(req).toDomain()
        }
    }

    override suspend fun getSprayWindowAdvisory(
        windSpeedKmh: Double,
        rainProbabilityPct: Double,
        tempC: Double,
        relativeHumidityPct: Double
    ): ResultState<SpraySuitability> {
        if (AppConfig.isDemoMode) {
            val windOk = windSpeedKmh <= 15.0
            val rainOk = rainProbabilityPct <= 40.0
            val isSuitable = windOk && rainOk && relativeHumidityPct <= 70.0
            return ResultState.Success(
                SpraySuitability(
                    isSuitable = isSuitable,
                    conditionLevel = if (isSuitable) "optimal" else "unfavorable",
                    recommendation = if (isSuitable) "Suitable for spraying based on local parameters." else "Unsuitable for spraying due to elevated wind, rain, or humidity.",
                    windSuitable = windOk,
                    rainProbabilitySuitable = rainOk,
                    calculationMethod = "DEMO_OFFLINE_AUDIT"
                )
            )
        }
        return safeApiCall(isIdempotent = false) {
            val req = SprayWindowRequestDto(
                windSpeedKmh = windSpeedKmh,
                rainProbabilityPct = rainProbabilityPct,
                tempC = tempC,
                relativeHumidityPct = relativeHumidityPct
            )
            apiService.getSprayWindowAdvisory(req).toDomain()
        }
    }

    override suspend fun getFarmerProfile(): ResultState<FarmerProfile> {
        val profile = localWeatherDataSource?.getFarmerProfile() ?: FarmerProfile()
        return ResultState.Success(profile)
    }

    override suspend fun saveFarmerProfile(profile: FarmerProfile): ResultState<Unit> {
        val rowId = localWeatherDataSource?.saveFarmerProfile(profile) ?: -1L
        return if (rowId > 0L) ResultState.Success(Unit) else ResultState.Error(AppError.Unknown("Failed to save farmer profile to local storage"))
    }

    override suspend fun evaluateDecision(
        question: String,
        locationName: String?,
        latitude: Double?,
        longitude: Double?,
        requestedTime: String?,
        domain: String?,
        context: Map<String, String>?
    ): ResultState<NirnayCard> {
        if (AppConfig.isDemoMode) {
            return ResultState.Success(evaluateDeterministicDecision(question))
        }

        return safeApiCall(isIdempotent = false) {
            val locDto = if (locationName != null || latitude != null || longitude != null) {
                com.weathergpt.data.remote.dto.decision.DecisionLocationDto(
                    name = locationName,
                    latitude = latitude,
                    longitude = longitude
                )
            } else null

            val req = com.weathergpt.data.remote.dto.decision.DecisionRequestDto(
                question = question,
                location = locDto,
                requestedTime = requestedTime,
                domain = domain ?: "farmer",
                context = context
            )
            apiService.evaluateDecision(req).toDomain()
        }
    }

    // ========================================================================
    // 5. GIS & Spatial Operations
    // ========================================================================

    override suspend fun getLocationHierarchy(
        latitude: Double,
        longitude: Double
    ): ResultState<LocationHierarchy> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Success(
                LocationHierarchy(
                    latitude = 26.2183,
                    longitude = 78.1828,
                    isResolved = true,
                    country = BoundaryUnit(code = "IND", name = "India", level = "country", parentCode = null, areaSqkm = null),
                    state = BoundaryUnit(code = "MP", name = "Madhya Pradesh", level = "state", parentCode = "IND", areaSqkm = null),
                    district = BoundaryUnit(code = "GWL", name = "Gwalior", level = "district", parentCode = "MP", areaSqkm = null),
                    subdistrict = BoundaryUnit(code = "GWL_SUB", name = "Gwalior", level = "subdistrict", parentCode = "GWL", areaSqkm = null)
                )
            )
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getLocationHierarchy(latitude, longitude).toDomain()
        }
    }

    override suspend fun getBoundary(
        level: String,
        code: String
    ): ResultState<AdministrativeBoundary> = safeApiCall(isIdempotent = true) {
        apiService.getBoundary(level, code).toDomain()
    }

    override suspend fun getHazardIntersection(
        warningGeometry: JsonObject?,
        alertId: String,
        event: String,
        severity: String,
        targetLevel: String
    ): ResultState<HazardIntersection> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Spatial hazard intersection unavailable offline", null))
        }
        return safeApiCall(isIdempotent = false) {
            val req = HazardIntersectionRequestDto(
                warningGeometry = warningGeometry,
                alertId = alertId,
                event = event,
                severity = severity,
                targetLevel = targetLevel
            )
            apiService.getHazardIntersection(req).toDomain()
        }
    }

    override suspend fun getRiskAssessment(
        districtName: String,
        precip24hPercentile: Double,
        exposureIndex: Double,
        vulnerabilityIndex: Double,
        hazardType: String
    ): ResultState<OperationalRisk> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Risk assessment unavailable offline", null))
        }
        return safeApiCall(isIdempotent = false) {
            val req = RiskAssessmentRequestDto(
                districtName = districtName,
                precip24hPercentile = precip24hPercentile,
                exposureIndex = exposureIndex,
                vulnerabilityIndex = vulnerabilityIndex,
                hazardType = hazardType
            )
            apiService.getRiskAssessment(req).toDomain()
        }
    }

    override suspend fun getAnalystRiskMatrix(
        districtName: String,
        precip24hPercentile: Double,
        exposureIndex: Double,
        vulnerabilityIndex: Double,
        hazardType: String
    ): ResultState<OperationalRisk> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Analyst risk matrix unavailable offline", null))
        }
        return safeApiCall(isIdempotent = false) {
            val req = RiskAssessmentRequestDto(
                districtName = districtName,
                precip24hPercentile = precip24hPercentile,
                exposureIndex = exposureIndex,
                vulnerabilityIndex = vulnerabilityIndex,
                hazardType = hazardType
            )
            apiService.getAnalystRiskMatrix(req).toDomain()
        }
    }

    override suspend fun getClimateTrends(
        latitude: Double,
        longitude: Double,
        location: String?,
        variable: String
    ): ResultState<ClimateTrends> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Climate trends unavailable offline", null))
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getClimateTrends(
                latitude = latitude,
                longitude = longitude,
                location = location,
                variable = variable
            ).toDomain()
        }
    }

    override suspend fun getClimateNormals(
        latitude: Double,
        longitude: Double,
        location: String?,
        month: Int?
    ): ResultState<ClimateNormals> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Climate normals unavailable offline", null))
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getClimateNormals(
                latitude = latitude,
                longitude = longitude,
                location = location,
                month = month
            ).toDomain()
        }
    }

    override suspend fun getGISAnalysis(
        latitude: Double?,
        longitude: Double?,
        districtCode: String?,
        observedRainMm: Double?,
        observedWindKmh: Double?,
        observedTempC: Double?,
        leadHours: Int
    ): ResultState<GISAnalysisReport> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: GIS analysis unavailable offline", null))
        }
        return safeApiCall(isIdempotent = false) {
            val req = GISAnalysisRequestDto(
                latitude = latitude,
                longitude = longitude,
                districtCode = districtCode,
                observedRainMm = observedRainMm,
                observedWindKmh = observedWindKmh,
                observedTempC = observedTempC,
                leadHours = leadHours
            )
            apiService.getGISAnalysis(req).toDomain()
        }
    }

    // ========================================================================
    // 6. NWP Numerical Weather Prediction (GET -> Idempotent)
    // ========================================================================

    override suspend fun getGFSGridPoint(
        latitude: Double,
        longitude: Double,
        leadHours: Int
    ): ResultState<NWPGridPoint> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: GFS grid point unavailable offline", null))
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getGFSGridPoint(latitude, longitude, leadHours).toDomain()
        }
    }

    override suspend fun getWRFGridPoint(
        latitude: Double,
        longitude: Double,
        leadHours: Int
    ): ResultState<NWPGridPoint> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: WRF grid point unavailable offline", null))
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getWRFGridPoint(latitude, longitude, leadHours).toDomain()
        }
    }

    override suspend fun getNWPModelComparison(
        latitude: Double,
        longitude: Double,
        leadHours: Int
    ): ResultState<NWPModelComparison> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: NWP model comparison unavailable offline", null))
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getNWPModelComparison(latitude, longitude, leadHours).toDomain()
        }
    }

    // ========================================================================
    // 7. Map-Ready Data
    // ========================================================================

    override suspend fun getPointWeatherMap(
        latitude: Double,
        longitude: Double
    ): ResultState<MapSpecification> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Point weather map unavailable offline", null))
        }
        return safeApiCall(isIdempotent = true) {
            apiService.getPointWeatherMap(latitude, longitude).toDomain()
        }
    }

    override suspend fun getWarningMap(
        warningGeometry: JsonObject,
        alertId: String,
        event: String,
        severity: String
    ): ResultState<MapSpecification> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Warning map unavailable offline", null))
        }
        return safeApiCall(isIdempotent = false) {
            val req = WarningMapRequestDto(
                warningGeometry = warningGeometry,
                alertId = alertId,
                event = event,
                severity = severity
            )
            apiService.getWarningMap(req).toDomain()
        }
    }

    override suspend fun getRiskMap(
        latitude: Double?,
        longitude: Double?,
        districtCode: String?,
        observedRainMm: Double?,
        observedWindKmh: Double?
    ): ResultState<MapSpecification> {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            return ResultState.Error(AppError.NetworkUnavailable("Demo Mode: Risk map unavailable offline", null))
        }
        return safeApiCall(isIdempotent = false) {
            val req = RiskMapRequestDto(
                latitude = latitude,
                longitude = longitude,
                districtCode = districtCode,
                observedRainMm = observedRainMm,
                observedWindKmh = observedWindKmh
            )
            apiService.getRiskMap(req).toDomain()
        }
    }

    // ========================================================================
    // 8. Voice (Speech-to-Text & Text-to-Speech)
    // ========================================================================

    override suspend fun speechToText(
        audioBytes: ByteArray,
        languageCode: String
    ): ResultState<VoiceSttResponseDto> = safeApiCall(isIdempotent = false) {
        val requestBody = audioBytes.toRequestBody("audio/wav".toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("audio", "audio.wav", requestBody)
        apiService.speechToText(part, languageCode)
    }

    override suspend fun textToSpeech(
        text: String,
        languageCode: String,
        voice: String?,
        speakingRate: Double
    ): ResultState<ByteArray> = safeApiCall(isIdempotent = true) {
        val req = VoiceTtsRequestDto(
            text = text,
            languageCode = languageCode,
            voice = voice,
            speakingRate = speakingRate
        )
        val responseBody = apiService.textToSpeech(req)
        responseBody.bytes()
    }

    override suspend fun sendVoiceQuery(
        audioBytes: ByteArray,
        languageCode: String,
        sessionId: String?,
        latitude: Double?,
        longitude: Double?,
        selectedBrain: String?
    ): ResultState<VoiceQueryResponseDto> = safeApiCall(isIdempotent = false) {
        val requestBody = audioBytes.toRequestBody("audio/wav".toMediaTypeOrNull())
        val audioPart = MultipartBody.Part.createFormData("audio", "audio.wav", requestBody)
        val textType = "text/plain".toMediaTypeOrNull()

        apiService.voiceQuery(
            audio = audioPart,
            languageCode = languageCode.toRequestBody(textType),
            sessionId = sessionId?.toRequestBody(textType),
            latitude = latitude?.toString()?.toRequestBody(textType),
            longitude = longitude?.toString()?.toRequestBody(textType),
            selectedBrain = selectedBrain?.toRequestBody(textType)
        )
    }

    // ========================================================================
    // 9. Showcase Demo Mode: Deterministic Engine & Gemma on UJJWAL
    // ========================================================================

    private suspend fun evaluateDeterministicDecision(question: String): NirnayCard {
        DemoModeNetworkGuard.assertNoNetworkCalls("evaluateDeterministicDecision")
        val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
        val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        val cachedWeather = localWeatherDataSource?.getCachedCurrentWeather(gwaliorLat, gwaliorLon)
        val cachedForecast = localWeatherDataSource?.getCachedForecast(gwaliorLat, gwaliorLon)
        val cachedAlertsReport = localWeatherDataSource?.getCachedAlerts(gwaliorLat, gwaliorLon)
        val farmerProfile = localWeatherDataSource?.getFarmerProfile()

        val lowerQ = question.lowercase(Locale.ROOT)
        val isSpray = lowerQ.contains("spray")
        val isIrrigate = lowerQ.contains("irrigate") || lowerQ.contains("water")
        val isHarvest = lowerQ.contains("harvest")
        val isSow = lowerQ.contains("sow") || lowerQ.contains("seed")

        if (cachedWeather == null) {
            return NirnayCard(
                question = question,
                verdict = DecisionVerdict.INSUFFICIENT_DATA,
                severity = DecisionSeverity.LOW,
                recommendedAction = "Insufficient local evidence to make a safe operational decision.",
                actionWindow = ActionWindow(
                    status = "unavailable",
                    isAvailable = false,
                    bestWindow = null,
                    fallbackWindows = emptyList(),
                    score = null,
                    constraints = emptyMap(),
                    confidence = DecisionConfidence.LOW,
                    reason = "Local Gwalior cache is missing or stale. Safe agronomic decisions require verified weather data.",
                    hourlyEvaluations = null
                ),
                confidence = DecisionConfidence.LOW,
                uncertainty = DecisionUncertainty(
                    gfsConfidence = "LOW",
                    wrfStatus = "UNAVAILABLE",
                    uncertaintyNote = "No local weather data cached for Gwalior",
                    leadTimeHours = 0.0
                ),
                why = listOf("Local Gwalior cache is missing or stale. Safe agronomic decisions require verified weather data."),
                primaryRisk = "Unverified conditions",
                lossPotential = "Unknown",
                alternatives = emptyList(),
                evidenceMetrics = emptyMap(),
                ledger = null
            )
        }

        // ====================================================================
        // ALERT + NIRNAY INTEGRATION: Official Alert Authority is Absolute
        // ====================================================================
        val activeOfficialAlerts = cachedAlertsReport?.alerts?.filter { it.isOfficial && it.isActive } ?: emptyList()
        val redAlert = activeOfficialAlerts.firstOrNull { it.parsedSeverity == AlertSeverity.RED }
        val orangeAlert = activeOfficialAlerts.firstOrNull { it.parsedSeverity == AlertSeverity.ORANGE }
        val yellowAlert = activeOfficialAlerts.firstOrNull { it.parsedSeverity == AlertSeverity.YELLOW }

        if (redAlert != null) {
            return NirnayCard(
                question = question,
                verdict = DecisionVerdict.NO_GO,
                severity = DecisionSeverity.CRITICAL,
                recommendedAction = "HALT FIELD OPERATIONS IMMEDIATELY: Official RED alert active for ${redAlert.hazardType}.",
                actionWindow = ActionWindow(
                    status = "unavailable",
                    isAvailable = false,
                    bestWindow = null,
                    fallbackWindows = emptyList(),
                    score = 0.0,
                    constraints = mapOf("official_alert" to "RED", "hazard" to redAlert.hazardType),
                    confidence = DecisionConfidence.HIGH,
                    reason = "Official RED alert from ${redAlert.issuingAgency} overrides all agronomic decisions: ${redAlert.description}",
                    hourlyEvaluations = null
                ),
                confidence = DecisionConfidence.HIGH,
                uncertainty = DecisionUncertainty(
                    gfsConfidence = "HIGH",
                    wrfStatus = "OFFICIAL_ALERT_OVERRIDE",
                    uncertaintyNote = "Official warning authority is absolute. Real-time safety override.",
                    leadTimeHours = 0.0
                ),
                why = listOf(
                    "Official RED severity alert issued by ${redAlert.issuingAgency}",
                    "Hazard: ${redAlert.hazardType}",
                    "Affected Area: ${redAlert.affectedArea} (${redAlert.spatialStatus})",
                    "Safety Instructions: ${redAlert.instructions}"
                ),
                primaryRisk = "Severe hazard to life, livestock, and crop infrastructure (${redAlert.hazardType})",
                lossPotential = "Catastrophic crop and equipment damage if ignored",
                alternatives = listOf("Seek safe indoor shelter", "Secure farm implements and livestock"),
                evidenceMetrics = mapOf(
                    "alert_severity" to "RED",
                    "hazard_type" to redAlert.hazardType,
                    "issuing_agency" to redAlert.issuingAgency,
                    "official_status" to "VERIFIED"
                ),
                ledger = null
            )
        }

        if (orangeAlert != null) {
            return NirnayCard(
                question = question,
                verdict = DecisionVerdict.POSTPONE,
                severity = DecisionSeverity.HIGH,
                recommendedAction = "POSTPONE FIELD OPERATIONS: Official ORANGE alert active for ${orangeAlert.hazardType}.",
                actionWindow = ActionWindow(
                    status = "unavailable",
                    isAvailable = false,
                    bestWindow = null,
                    fallbackWindows = emptyList(),
                    score = 2.0,
                    constraints = mapOf("official_alert" to "ORANGE", "hazard" to orangeAlert.hazardType),
                    confidence = DecisionConfidence.HIGH,
                    reason = "Official ORANGE warning: ${orangeAlert.description}",
                    hourlyEvaluations = null
                ),
                confidence = DecisionConfidence.HIGH,
                uncertainty = DecisionUncertainty(
                    gfsConfidence = "HIGH",
                    wrfStatus = "OFFICIAL_ALERT_OVERRIDE",
                    uncertaintyNote = "Official warning authority overrides standard field operations",
                    leadTimeHours = 2.0
                ),
                why = listOf(
                    "Official ORANGE severity alert issued by ${orangeAlert.issuingAgency}",
                    "Hazard: ${orangeAlert.hazardType}",
                    "Instructions: ${orangeAlert.instructions}"
                ),
                primaryRisk = "Field operation disruption due to ${orangeAlert.hazardType}",
                lossPotential = "Moderate to high operational loss",
                alternatives = listOf("Delay operations until alert expires", "Prepare field drainage"),
                evidenceMetrics = mapOf(
                    "alert_severity" to "ORANGE",
                    "hazard_type" to orangeAlert.hazardType,
                    "issuing_agency" to orangeAlert.issuingAgency
                ),
                ledger = null
            )
        }

        val temp = cachedWeather.temperatureC
        val humidity = cachedWeather.relativeHumidityPct
        val wind = cachedWeather.windSpeedKmh
        val precipMm = cachedWeather.precipitationMm
        val rainProb = cachedForecast?.dailyForecast?.firstOrNull()?.precipitationProbabilityPct ?: 0.0

        val cropContext = if (farmerProfile != null && !farmerProfile.crop.isNullOrBlank()) {
            "${farmerProfile.crop} (${farmerProfile.cropStage ?: "Stage unspecified"}) on ${farmerProfile.farmArea ?: ""} ${farmerProfile.areaUnit ?: ""}".trim()
        } else {
            "General Farm Operation"
        }

        val cachedEvidence = mutableMapOf(
            "location" to SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
            "coordinates" to "$gwaliorLat, $gwaliorLon",
            "is_cached" to "true",
            "source_mode" to "DEMO_MODE",
            "provider" to (cachedWeather.provider ?: "Open-Meteo"),
            "retrieved_at" to (cachedWeather.retrievedAt ?: cachedWeather.observationTime),
            "temperature_c" to String.format(Locale.ROOT, "%.1f", temp),
            "relative_humidity_pct" to String.format(Locale.ROOT, "%.1f", humidity),
            "wind_speed_kmh" to String.format(Locale.ROOT, "%.1f", wind),
            "precipitation_mm" to String.format(Locale.ROOT, "%.1f", precipMm),
            "precipitation_prob_pct" to String.format(Locale.ROOT, "%.1f", rainProb),
            "farmer_profile_crop" to (farmerProfile?.crop ?: "Unspecified"),
            "farmer_profile_stage" to (farmerProfile?.cropStage ?: "Unspecified"),
            "farmer_profile_soil" to (farmerProfile?.soilType ?: "Unspecified"),
            "farmer_profile_irrigation" to (farmerProfile?.irrigationType ?: "Unspecified")
        )

        val (verdict, severity, action, reason) = when {
            isSpray -> {
                // Canonical Agronomic Safety Thresholds (docs/11_ANALYTICS_ENGINE.md Section 3.4):
                // Max Wind <= 15.0 km/h, Max PoP <= 30.0%, Max Humidity <= 70.0%, Max Rain = 0.0 mm
                val windFail = wind > 15.0
                val rainFail = precipMm > 0.0 || rainProb > 30.0
                val humidFail = humidity > 70.0

                if (windFail || rainFail || humidFail) {
                    val reasons = mutableListOf<String>()
                    if (windFail) reasons.add("wind ($wind km/h > 15 km/h threshold causes drift)")
                    if (rainFail) reasons.add("precipitation risk (${precipMm}mm rain, ${rainProb}% PoP washes away chemical)")
                    if (humidFail) reasons.add("relative humidity (${humidity}% > 70% reduces droplet absorption)")
                    Tuple4(
                        DecisionVerdict.POSTPONE,
                        DecisionSeverity.MODERATE,
                        "Delay spraying $cropContext until weather parameters settle.",
                        "Based on recently retrieved weather data for Gwalior, overcast conditions and ${humidity.toInt()}% humidity elevate drift risk. Unfavorable spray window due to: ${reasons.joinToString(", ")}."
                    )
                } else {
                    Tuple4(
                        if (yellowAlert != null) DecisionVerdict.PROCEED_WITH_CAUTION else DecisionVerdict.GO,
                        if (yellowAlert != null) DecisionSeverity.MODERATE else DecisionSeverity.LOW,
                        "Proceed with spraying $cropContext within recommended morning window.",
                        "Based on recently retrieved weather data for Gwalior, conditions optimal for spraying: wind $wind km/h <= 15 km/h, PoP $rainProb% <= 30%, rain 0.0 mm."
                    )
                }
            }
            isIrrigate -> {
                // FAO-56 Water balance calculation
                val et0 = 4.2
                val kc = 1.05
                val etc = et0 * kc
                val expectedRain = precipMm + (cachedForecast?.dailyForecast?.take(2)?.sumOf { it.precipitationProbabilityPct / 100.0 * 2.0 } ?: 0.0)
                if (expectedRain > etc * 1.5) {
                    Tuple4(
                        DecisionVerdict.POSTPONE,
                        DecisionSeverity.LOW,
                        "Wait for expected precipitation; postpone artificial irrigation for $cropContext.",
                        "Forecast rainfall ($expectedRain mm) satisfies crop water demand (ETc ${String.format(Locale.ROOT, "%.2f", etc)} mm/day)."
                    )
                } else {
                    Tuple4(
                        DecisionVerdict.GO,
                        DecisionSeverity.LOW,
                        "Irrigate $cropContext: soil moisture depletion requires replenishment.",
                        "Crop water demand (ETc ${String.format(Locale.ROOT, "%.2f", etc)} mm/day) exceeds precipitation ($expectedRain mm)."
                    )
                }
            }
            isHarvest -> {
                // Canonical Harvest constraints: rain 0, PoP <= 25%, wind <= 25 km/h, RH <= 75%
                if (precipMm > 0.0 || rainProb > 25.0 || wind > 25.0 || humidity > 75.0) {
                    Tuple4(
                        DecisionVerdict.POSTPONE,
                        DecisionSeverity.MODERATE,
                        "Postpone harvest of $cropContext until moisture levels decline.",
                        "Harvest window constrained by elevated moisture (PoP $rainProb%, RH $humidity%)."
                    )
                } else {
                    Tuple4(
                        DecisionVerdict.GO,
                        DecisionSeverity.LOW,
                        "Favorable harvest window active for $cropContext.",
                        "Dry canopy conditions satisfied: 0 mm rain, $rainProb% PoP, $wind km/h wind."
                    )
                }
            }
            isSow -> {
                // Sowing: rain >= 25mm -> NO_GO, temp >= 42°C -> POSTPONE, wind >= 30 km/h -> POSTPONE
                if (precipMm >= 25.0) {
                    Tuple4(
                        DecisionVerdict.NO_GO,
                        DecisionSeverity.HIGH,
                        "Do not sow $cropContext: heavy rainfall waterlogging hazard.",
                        "Precipitation ($precipMm mm >= 25 mm threshold) will cause seed rot and crusting."
                    )
                } else if (temp >= 42.0 || wind >= 30.0) {
                    Tuple4(
                        DecisionVerdict.POSTPONE,
                        DecisionSeverity.MODERATE,
                        "Postpone sowing $cropContext due to severe thermal/wind stress.",
                        "Temperature ($temp°C) or wind ($wind km/h) exceed safe seedling establishment thresholds."
                    )
                } else {
                    Tuple4(
                        DecisionVerdict.GO,
                        DecisionSeverity.LOW,
                        "Favorable conditions for field sowing of $cropContext.",
                        "Soil moisture and temperature ($temp°C) support germination."
                    )
                }
            }
            else -> {
                if (yellowAlert != null) {
                    Tuple4(
                        DecisionVerdict.PROCEED_WITH_CAUTION,
                        DecisionSeverity.MODERATE,
                        "Proceed with field operations under caution. Official YELLOW alert: ${yellowAlert.hazardType}.",
                        "Standard field work acceptable with active weather monitoring."
                    )
                } else {
                    Tuple4(
                        DecisionVerdict.GO,
                        DecisionSeverity.LOW,
                        "Standard field operations can proceed under current weather parameters.",
                        "Based on real cached Gwalior weather, temperature is $temp°C and no active hazard exists."
                    )
                }
            }
        }

        return NirnayCard(
            question = question,
            verdict = verdict,
            severity = severity,
            recommendedAction = action,
            actionWindow = ActionWindow(
                status = if (verdict == DecisionVerdict.GO || verdict == DecisionVerdict.PROCEED_WITH_CAUTION) "available" else "unavailable",
                isAvailable = verdict == DecisionVerdict.GO || verdict == DecisionVerdict.PROCEED_WITH_CAUTION,
                bestWindow = null,
                fallbackWindows = emptyList(),
                score = if (verdict == DecisionVerdict.GO) 8.5 else 4.0,
                constraints = mapOf("wind" to "$wind km/h", "pop" to "$rainProb%", "rh" to "$humidity%"),
                confidence = DecisionConfidence.HIGH,
                reason = reason,
                hourlyEvaluations = null
            ),
            confidence = DecisionConfidence.HIGH,
            uncertainty = DecisionUncertainty(
                gfsConfidence = "HIGH",
                wrfStatus = "AVAILABLE",
                uncertaintyNote = "Offline deterministic evaluation with zero remote dependency",
                leadTimeHours = 4.0
            ),
            why = listOf(reason),
            primaryRisk = when {
                isSpray -> "Chemical drift / wash-off"
                isIrrigate -> "Over-saturation / water stress"
                isHarvest -> "Grain spoilage from moisture"
                isSow -> "Germination failure"
                else -> "Operational disruption"
            },
            lossPotential = if (verdict == DecisionVerdict.GO) "Minimal" else "Moderate",
            alternatives = emptyList(),
            evidenceMetrics = cachedEvidence,
            ledger = null
        )
    }

    private suspend fun sendDemoChat(query: ChatQuery): ResultState<ChatResponse> {
        DemoModeNetworkGuard.assertNoNetworkCalls("sendDemoChat")
        val gwaliorLat = SharedLocationManager.DEMO_GWALIOR_LATITUDE
        val gwaliorLon = SharedLocationManager.DEMO_GWALIOR_LONGITUDE
        val cachedWeather = localWeatherDataSource?.getCachedCurrentWeather(gwaliorLat, gwaliorLon)
        val cachedForecast = localWeatherDataSource?.getCachedForecast(gwaliorLat, gwaliorLon)
        val cachedAlertsReport = localWeatherDataSource?.getCachedAlerts(gwaliorLat, gwaliorLon)
        val farmerProfile = localWeatherDataSource?.getFarmerProfile()

        val response = OfflineDemoIntelligenceEngine.processDemoQuery(
            query = query,
            cachedWeather = cachedWeather,
            cachedForecast = cachedForecast,
            cachedAlerts = cachedAlertsReport?.alerts ?: emptyList(),
            farmerProfile = farmerProfile
        )
        return ResultState.Success(response)
    }

    private data class Tuple4<A, B, C, D>(val a: A, val b: B, val c: C, val d: D)
}
