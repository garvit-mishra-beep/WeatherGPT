package com.weathergpt.presentation.analyst

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.PredefinedLocation
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class AnalystDashboardUiState(
    val locationName: String = "Gwalior, Madhya Pradesh",
    val districtName: String = "Gwalior",
    val stateName: String = "Madhya Pradesh",
    val latitude: Double = 26.2183,
    val longitude: Double = 78.1828,
    val rainfallMm: Double = 0.0,
    val rainfallAnomaly: String = "Normal",
    val temperatureC: Double = 0.0,
    val tempAnomaly: String = "Normal",
    val hazardType: String = "Monitoring",
    val hazardSeverity: Double = 0.0,
    val exposureIndex: Double = 0.0,
    val vulnerabilityIndex: Double = 0.0,
    val compositeRiskScore: Double = 0.0,
    val riskCategory: String = "PENDING",
    val actionPriority: String = "Evaluating operational risk...",
    val floodRiskLevel: String = "LOW",
    val droughtRiskLevel: String = "LOW",
    val squallRiskLevel: String = "LOW",
    val provenanceProvider: String = "Vayubodhak Analyst Engine • /api/v1/analyst/risk-matrix",
    val lastUpdated: String = "",
    val riskAssessmentState: ResultState<OperationalRisk> = ResultState.Idle,
    val gisAnalysisState: ResultState<GISAnalysisReport> = ResultState.Idle,
    val weatherState: ResultState<CurrentWeather> = ResultState.Idle,
    val gfsState: ResultState<NWPGridPoint> = ResultState.Idle,
    val forecastState: ResultState<WeatherForecast> = ResultState.Idle
)

class AnalystDashboardViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AnalystDashboardUiState())
    val uiState: StateFlow<AnalystDashboardUiState> = _uiState.asStateFlow()

    val availableLocations: List<PredefinedLocation> get() = locationManager.availableLocations

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    locationName = loc.formattedAddress,
                    districtName = loc.districtName,
                    stateName = loc.stateName,
                    latitude = loc.latitude,
                    longitude = loc.longitude,
                    // Invalidate old location dependent data immediately
                    riskAssessmentState = ResultState.Loading,
                    gisAnalysisState = ResultState.Loading,
                    weatherState = ResultState.Loading,
                    gfsState = ResultState.Loading
                )
                loadAnalysis()
            }
        }
    }

    fun selectPredefinedLocation(location: PredefinedLocation) {
        locationManager.selectPredefinedLocation(location)
    }

    fun loadAnalysis() {
        viewModelScope.launch {
            val dist = _uiState.value.districtName
            val lat = _uiState.value.latitude
            val lon = _uiState.value.longitude

            _uiState.value = _uiState.value.copy(
                riskAssessmentState = ResultState.Loading,
                gisAnalysisState = ResultState.Loading,
                weatherState = ResultState.Loading,
                gfsState = ResultState.Loading,
                forecastState = ResultState.Loading
            )

            // 1. Fetch live Current Weather
            val weatherResult = repository.getCurrentWeather(latitude = lat, longitude = lon)

            // 2. Fetch live GFS NWP grid point (24h lead)
            val gfsResult = repository.getGFSGridPoint(latitude = lat, longitude = lon, leadHours = 24)

            // 3. Fetch Forecast for dynamic trend line
            val forecastResult = repository.getWeatherForecast(latitude = lat, longitude = lon)

            // Derive dynamic meteorological values
            val liveTemp = when {
                weatherResult is ResultState.Success<CurrentWeather> -> weatherResult.data.temperatureC
                gfsResult is ResultState.Success<NWPGridPoint> -> gfsResult.data.temperature2mC
                else -> 0.0
            }

            val livePrecip = when {
                gfsResult is ResultState.Success<NWPGridPoint> -> gfsResult.data.accumulatedPrecipMm
                weatherResult is ResultState.Success<CurrentWeather> -> weatherResult.data.precipitationMm
                else -> 0.0
            }

            val liveWind = when {
                weatherResult is ResultState.Success<CurrentWeather> -> weatherResult.data.windSpeedKmh
                gfsResult is ResultState.Success<NWPGridPoint> -> gfsResult.data.windSpeedKmh
                else -> 0.0
            }

            // Derive dynamic precipitation percentile from real observations
            val dynamicPercentile = when {
                livePrecip >= 100.0 -> 99.0
                livePrecip >= 50.0 -> 90.0
                livePrecip >= 25.0 -> 75.0
                livePrecip >= 10.0 -> 60.0
                livePrecip >= 2.5 -> 40.0
                else -> 20.0
            }

            val dynamicHazardType = when {
                livePrecip >= 25.0 -> "heavy_rainfall"
                liveWind >= 35.0 -> "squall"
                liveTemp >= 40.0 -> "heatwave"
                else -> "monitoring"
            }

            // 4. Fetch Operational Risk Assessment from /api/v1/analyst/risk-matrix
            val riskResult = repository.getAnalystRiskMatrix(
                districtName = dist,
                precip24hPercentile = dynamicPercentile,
                exposureIndex = _uiState.value.exposureIndex,
                vulnerabilityIndex = _uiState.value.vulnerabilityIndex,
                hazardType = dynamicHazardType
            )

            // 5. Fetch Spatial GIS Analysis
            val gisResult = repository.getGISAnalysis(
                latitude = lat,
                longitude = lon,
                districtCode = null,
                observedRainMm = livePrecip,
                observedWindKmh = liveWind,
                observedTempC = liveTemp,
                leadHours = 24
            )

            // Derive dynamic GIS & Risk scores strictly from backend responses
            val compScore = when {
                riskResult is ResultState.Success<OperationalRisk> -> riskResult.data.compositeRiskScore
                gisResult is ResultState.Success<GISAnalysisReport> -> gisResult.data.impactScore
                else -> 0.0
            }

            val category = when {
                riskResult is ResultState.Success<OperationalRisk> -> riskResult.data.riskLevel
                gisResult is ResultState.Success<GISAnalysisReport> -> gisResult.data.riskCategory
                riskResult is ResultState.Error -> "UNAVAILABLE"
                else -> "PENDING"
            }

            val hazardScore = when {
                riskResult is ResultState.Success<OperationalRisk> -> riskResult.data.hazardIndex
                gisResult is ResultState.Success<GISAnalysisReport> -> gisResult.data.hazardScore
                else -> 0.0
            }

            val exposureScore = when {
                riskResult is ResultState.Success<OperationalRisk> -> riskResult.data.exposureIndex
                gisResult is ResultState.Success<GISAnalysisReport> -> gisResult.data.exposureScore
                else -> 0.0
            }

            val vulnScore = when {
                riskResult is ResultState.Success<OperationalRisk> -> riskResult.data.vulnerabilityIndex
                gisResult is ResultState.Success<GISAnalysisReport> -> gisResult.data.vulnerabilityScore
                else -> 0.0
            }

            val actionPri = when {
                riskResult is ResultState.Success<OperationalRisk> -> riskResult.data.actionPriority
                riskResult is ResultState.Error -> "Risk assessment unavailable: ${riskResult.error.message ?: "Backend error"}"
                else -> "Awaiting backend telemetry"
            }

            val floodRisk = when {
                livePrecip >= 50.0 -> "HIGH"
                livePrecip >= 15.0 -> "MODERATE"
                else -> "LOW"
            }

            val droughtRisk = when {
                livePrecip < 2.0 && liveTemp > 35.0 -> "HIGH"
                livePrecip < 5.0 -> "MODERATE"
                else -> "LOW"
            }

            val squallRisk = when {
                liveWind >= 45.0 -> "HIGH"
                liveWind >= 25.0 -> "MODERATE"
                else -> "LOW"
            }

            val nowFormatted = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date())

            _uiState.value = _uiState.value.copy(
                rainfallMm = livePrecip,
                rainfallAnomaly = if (livePrecip > 20.0) "↑ ${((livePrecip - 15.0) / 15.0 * 100).toInt()}%" else "Normal",
                temperatureC = liveTemp,
                tempAnomaly = if (liveTemp > 32.0) "↑ 1.5°C" else if (liveTemp > 0.0 && liveTemp < 24.0) "↓ 1.2°C" else "Normal",
                hazardType = if (riskResult is ResultState.Success<OperationalRisk>) riskResult.data.hazardType else dynamicHazardType,
                hazardSeverity = hazardScore,
                exposureIndex = exposureScore,
                vulnerabilityIndex = vulnScore,
                compositeRiskScore = compScore,
                riskCategory = category,
                actionPriority = actionPri,
                floodRiskLevel = floodRisk,
                droughtRiskLevel = droughtRisk,
                squallRiskLevel = squallRisk,
                lastUpdated = nowFormatted,
                riskAssessmentState = riskResult,
                gisAnalysisState = gisResult,
                weatherState = weatherResult,
                gfsState = gfsResult,
                forecastState = forecastResult
            )
        }
    }

    fun updateScores(hazard: Double, exposure: Double, vulnerability: Double) {
        viewModelScope.launch {
            val dist = _uiState.value.districtName
            val riskResult = repository.getAnalystRiskMatrix(
                districtName = dist,
                precip24hPercentile = 50.0,
                exposureIndex = exposure,
                vulnerabilityIndex = vulnerability,
                hazardType = _uiState.value.hazardType
            )
            if (riskResult is ResultState.Success<OperationalRisk>) {
                _uiState.value = _uiState.value.copy(
                    hazardSeverity = riskResult.data.hazardIndex,
                    exposureIndex = riskResult.data.exposureIndex,
                    vulnerabilityIndex = riskResult.data.vulnerabilityIndex,
                    compositeRiskScore = riskResult.data.compositeRiskScore,
                    riskCategory = riskResult.data.riskLevel,
                    actionPriority = riskResult.data.actionPriority,
                    riskAssessmentState = riskResult
                )
            } else {
                loadAnalysis()
            }
        }
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                AnalystDashboardViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
