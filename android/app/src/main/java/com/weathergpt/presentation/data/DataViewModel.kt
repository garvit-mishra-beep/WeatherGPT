package com.weathergpt.presentation.data

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.climate.ClimateNormals
import com.weathergpt.domain.model.climate.ClimateTrends
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class DataScreenUiState(
    val selectedModel: String = "GFS (0.25°)",
    val selectedMetricTab: String = "Temperature",
    val divergenceRatio: Double = 0.0,
    val historicalTrendSlope: Double? = null,
    val rainfallAnomalyPct: Double? = null,
    val normalRainfallMm: Double? = null,
    val actualRainfallMm: Double? = null,
    val normalTempC: Double? = null,
    val actualTempC: Double? = null,
    val trendDirection: String = "PENDING",
    val climateNormalsCategory: String = "Near Normal",
    val latitude: Double = 28.6139,
    val longitude: Double = 77.2090,
    val climateTrendsState: ResultState<ClimateTrends> = ResultState.Idle,
    val climateNormalsState: ResultState<ClimateNormals> = ResultState.Idle,
    val gfsGridState: ResultState<NWPGridPoint> = ResultState.Idle,
    val wrfGridState: ResultState<NWPGridPoint> = ResultState.Idle,
    val nwpComparisonState: ResultState<NWPModelComparison> = ResultState.Idle,
    val forecastState: ResultState<WeatherForecast> = ResultState.Idle,
    val currentWeatherState: ResultState<CurrentWeather> = ResultState.Idle
)

class DataViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(DataScreenUiState())
    val uiState: StateFlow<DataScreenUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    latitude = loc.latitude,
                    longitude = loc.longitude
                )
                loadData()
            }
        }
    }

    fun loadData() {
        viewModelScope.launch {
            val lat = _uiState.value.latitude
            val lon = _uiState.value.longitude

            _uiState.value = _uiState.value.copy(
                climateTrendsState = ResultState.Loading,
                climateNormalsState = ResultState.Loading,
                gfsGridState = ResultState.Loading,
                wrfGridState = ResultState.Loading,
                nwpComparisonState = ResultState.Loading,
                forecastState = ResultState.Loading,
                currentWeatherState = ResultState.Loading
            )

            val gfsResult = repository.getGFSGridPoint(lat, lon, leadHours = 24)
            val wrfResult = repository.getWRFGridPoint(lat, lon, leadHours = 24)
            val compResult = repository.getNWPModelComparison(lat, lon, leadHours = 24)
            val forecastResult = repository.getWeatherForecast(lat, lon, days = 7)
            val weatherResult = repository.getCurrentWeather(lat, lon)
            val trendsResult = repository.getClimateTrends(lat, lon)
            val normalsResult = repository.getClimateNormals(lat, lon)

            val divergence = if (compResult is ResultState.Success<NWPModelComparison>) {
                compResult.data.divergenceAnalysis?.divergenceRatio ?: _uiState.value.divergenceRatio
            } else _uiState.value.divergenceRatio

            val trendSlope = if (trendsResult is ResultState.Success<ClimateTrends>) {
                trendsResult.data.trendSlope
            } else null

            val trendDir = if (trendsResult is ResultState.Success<ClimateTrends>) {
                trendsResult.data.direction
            } else if (trendsResult is ResultState.Error) "UNAVAILABLE" else "PENDING"

            val rainAnomaly = if (normalsResult is ResultState.Success<ClimateNormals>) {
                normalsResult.data.rainfallAnomalyPct
            } else null

            val normRain = if (normalsResult is ResultState.Success<ClimateNormals>) {
                normalsResult.data.normalRainfallMm
            } else null

            val actRain = if (normalsResult is ResultState.Success<ClimateNormals>) {
                normalsResult.data.actualRainfallMm
            } else null

            val normTemp = if (normalsResult is ResultState.Success<ClimateNormals>) {
                normalsResult.data.normalTempC
            } else null

            val actTemp = if (normalsResult is ResultState.Success<ClimateNormals>) {
                normalsResult.data.actualTempC
            } else null

            val normCat = if (normalsResult is ResultState.Success<ClimateNormals>) {
                normalsResult.data.category
            } else if (normalsResult is ResultState.Error) "UNAVAILABLE" else "Near Normal"

            _uiState.value = _uiState.value.copy(
                gfsGridState = gfsResult,
                wrfGridState = wrfResult,
                nwpComparisonState = compResult,
                forecastState = forecastResult,
                currentWeatherState = weatherResult,
                climateTrendsState = trendsResult,
                climateNormalsState = normalsResult,
                divergenceRatio = divergence,
                historicalTrendSlope = trendSlope,
                trendDirection = trendDir,
                rainfallAnomalyPct = rainAnomaly,
                normalRainfallMm = normRain,
                actualRainfallMm = actRain,
                normalTempC = normTemp,
                actualTempC = actTemp,
                climateNormalsCategory = normCat
            )
        }
    }

    fun selectModel(model: String) {
        _uiState.value = _uiState.value.copy(selectedModel = model)
    }

    fun selectMetricTab(metric: String) {
        _uiState.value = _uiState.value.copy(selectedMetricTab = metric)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                DataViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
