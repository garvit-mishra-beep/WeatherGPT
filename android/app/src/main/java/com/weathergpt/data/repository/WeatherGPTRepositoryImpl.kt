package com.weathergpt.data.repository

import com.weathergpt.core.error.AppError
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
import com.weathergpt.data.remote.dto.gis.GISAnalysisRequestDto
import com.weathergpt.data.remote.dto.gis.HazardIntersectionRequestDto
import com.weathergpt.data.remote.dto.gis.RiskAssessmentRequestDto
import com.weathergpt.data.remote.dto.map.RiskMapRequestDto
import com.weathergpt.data.remote.dto.map.WarningMapRequestDto
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
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject

/**
 * Hardened production-grade implementation of [WeatherGPTRepository].
 *
 * Guarantees:
 * 1. Offline fast-fail via [NetworkMonitor].
 * 2. Bounded transient retries for idempotent GET requests.
 * 3. Zero automatic retries for non-idempotent POST operations.
 * 4. Cancellation-safe coroutines: [CancellationException] is NEVER swallowed.
 * 5. Structured RFC 7807 problem details and request ID preservation.
 */
class WeatherGPTRepositoryImpl(
    private val apiService: WeatherGPTApiService,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val networkMonitor: NetworkMonitor? = null
) : WeatherGPTRepository {

    private suspend fun <T> safeApiCall(
        isIdempotent: Boolean = false,
        block: suspend () -> T
    ): ResultState<T> {
        // Fast-fail if network monitor reports offline (unless using custom LAN/USB reverse server)
        if (networkMonitor != null && !networkMonitor.isOnline && !com.weathergpt.core.config.AppConfig.isCustomBaseUrl) {
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

    override suspend fun sendChat(query: ChatQuery): ResultState<ChatResponse> = safeApiCall(isIdempotent = false) {
        val deviceContext = if (query.latitude != null && query.longitude != null) {
            DeviceContextDto(
                gpsLocation = GPSLocationDto(
                    latitude = query.latitude,
                    longitude = query.longitude
                )
            )
        } else null

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

    // ========================================================================
    // 3. Weather & Official Alerts (GET -> Idempotent)
    // ========================================================================

    override suspend fun getCurrentWeather(
        latitude: Double,
        longitude: Double
    ): ResultState<CurrentWeather> = safeApiCall(isIdempotent = true) {
        apiService.getCurrentWeather(latitude, longitude).toDomain()
    }

    override suspend fun getWeatherForecast(
        latitude: Double,
        longitude: Double,
        days: Int,
        hourly: Boolean
    ): ResultState<WeatherForecast> = safeApiCall(isIdempotent = true) {
        apiService.getWeatherForecast(latitude, longitude, days, hourly).toDomain()
    }

    override suspend fun getWeatherAlerts(
        district: String?,
        latitude: Double?,
        longitude: Double?
    ): ResultState<WeatherAlertsReport> = safeApiCall(isIdempotent = true) {
        apiService.getWeatherAlerts(district, latitude, longitude).toDomain()
    }

    override suspend fun getWeatherIntelligence(
        latitude: Double,
        longitude: Double,
        leadHours: Int,
        includeNwp: Boolean
    ): ResultState<WeatherIntelligence> = safeApiCall(isIdempotent = true) {
        apiService.getWeatherIntelligence(latitude, longitude, leadHours, includeNwp).toDomain()
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
    ): ResultState<IrrigationAdvisory> = safeApiCall(isIdempotent = false) {
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

    override suspend fun getSprayWindowAdvisory(
        windSpeedKmh: Double,
        rainProbabilityPct: Double,
        tempC: Double,
        relativeHumidityPct: Double
    ): ResultState<SpraySuitability> = safeApiCall(isIdempotent = false) {
        val req = SprayWindowRequestDto(
            windSpeedKmh = windSpeedKmh,
            rainProbabilityPct = rainProbabilityPct,
            tempC = tempC,
            relativeHumidityPct = relativeHumidityPct
        )
        apiService.getSprayWindowAdvisory(req).toDomain()
    }

    // ========================================================================
    // 5. GIS & Spatial Operations
    // ========================================================================

    override suspend fun getLocationHierarchy(
        latitude: Double,
        longitude: Double
    ): ResultState<LocationHierarchy> = safeApiCall(isIdempotent = true) {
        apiService.getLocationHierarchy(latitude, longitude).toDomain()
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
    ): ResultState<HazardIntersection> = safeApiCall(isIdempotent = false) {
        val req = HazardIntersectionRequestDto(
            warningGeometry = warningGeometry,
            alertId = alertId,
            event = event,
            severity = severity,
            targetLevel = targetLevel
        )
        apiService.getHazardIntersection(req).toDomain()
    }

    override suspend fun getRiskAssessment(
        districtName: String,
        precip24hPercentile: Double,
        exposureIndex: Double,
        vulnerabilityIndex: Double,
        hazardType: String
    ): ResultState<OperationalRisk> = safeApiCall(isIdempotent = false) {
        val req = RiskAssessmentRequestDto(
            districtName = districtName,
            precip24hPercentile = precip24hPercentile,
            exposureIndex = exposureIndex,
            vulnerabilityIndex = vulnerabilityIndex,
            hazardType = hazardType
        )
        apiService.getRiskAssessment(req).toDomain()
    }

    override suspend fun getGISAnalysis(
        latitude: Double?,
        longitude: Double?,
        districtCode: String?,
        observedRainMm: Double?,
        observedWindKmh: Double?,
        observedTempC: Double?,
        leadHours: Int
    ): ResultState<GISAnalysisReport> = safeApiCall(isIdempotent = false) {
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

    // ========================================================================
    // 6. NWP Numerical Weather Prediction (GET -> Idempotent)
    // ========================================================================

    override suspend fun getGFSGridPoint(
        latitude: Double,
        longitude: Double,
        leadHours: Int
    ): ResultState<NWPGridPoint> = safeApiCall(isIdempotent = true) {
        apiService.getGFSGridPoint(latitude, longitude, leadHours).toDomain()
    }

    override suspend fun getNWPModelComparison(
        latitude: Double,
        longitude: Double,
        leadHours: Int
    ): ResultState<NWPModelComparison> = safeApiCall(isIdempotent = true) {
        apiService.getNWPModelComparison(latitude, longitude, leadHours).toDomain()
    }

    // ========================================================================
    // 7. Map-Ready Data
    // ========================================================================

    override suspend fun getPointWeatherMap(
        latitude: Double,
        longitude: Double
    ): ResultState<MapSpecification> = safeApiCall(isIdempotent = true) {
        apiService.getPointWeatherMap(latitude, longitude).toDomain()
    }

    override suspend fun getWarningMap(
        warningGeometry: JsonObject,
        alertId: String,
        event: String,
        severity: String
    ): ResultState<MapSpecification> = safeApiCall(isIdempotent = false) {
        val req = WarningMapRequestDto(
            warningGeometry = warningGeometry,
            alertId = alertId,
            event = event,
            severity = severity
        )
        apiService.getWarningMap(req).toDomain()
    }

    override suspend fun getRiskMap(
        latitude: Double?,
        longitude: Double?,
        districtCode: String?,
        observedRainMm: Double?,
        observedWindKmh: Double?
    ): ResultState<MapSpecification> = safeApiCall(isIdempotent = false) {
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
