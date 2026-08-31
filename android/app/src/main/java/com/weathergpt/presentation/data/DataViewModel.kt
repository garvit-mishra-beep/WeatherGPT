package com.weathergpt.presentation.data

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class DataScreenUiState(
    val selectedModel: String = "GFS (0.25°)",
    val divergenceRatio: Double = 0.12,
    val historicalTrendSlope: Double = 1.45,
    val rainfallAnomalyPct: Double = 8.5,
    val latitude: Double = 28.6139,
    val longitude: Double = 77.2090,
    val gfsGridState: ResultState<NWPGridPoint> = ResultState.Idle,
    val wrfGridState: ResultState<NWPGridPoint> = ResultState.Idle,
    val nwpComparisonState: ResultState<NWPModelComparison> = ResultState.Idle
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
                gfsGridState = ResultState.Loading,
                wrfGridState = ResultState.Loading,
                nwpComparisonState = ResultState.Loading
            )

            val gfsResult = repository.getGFSGridPoint(lat, lon, leadHours = 24)
            val wrfResult = repository.getWRFGridPoint(lat, lon, leadHours = 24)
            val compResult = repository.getNWPModelComparison(lat, lon, leadHours = 24)

            val divergence = if (compResult is ResultState.Success<NWPModelComparison>) {
                compResult.data.divergenceAnalysis?.divergenceRatio ?: _uiState.value.divergenceRatio
            } else _uiState.value.divergenceRatio

            _uiState.value = _uiState.value.copy(
                gfsGridState = gfsResult,
                wrfGridState = wrfResult,
                nwpComparisonState = compResult,
                divergenceRatio = divergence
            )
        }
    }

    fun selectModel(model: String) {
        _uiState.value = _uiState.value.copy(selectedModel = model)
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
