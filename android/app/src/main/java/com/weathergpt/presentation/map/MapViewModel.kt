package com.weathergpt.presentation.map

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.map.MapBounds
import com.weathergpt.core.map.MapLatLng
import com.weathergpt.core.map.MapRendererAdapter
import com.weathergpt.core.map.RenderableLayer
import com.weathergpt.core.map.RenderableMapSpecification
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.map.LegendItem
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

enum class WeatherMapLayer(val id: String, val title: String) {
    RAIN("rain", "Precipitation Radar"),
    TEMPERATURE("temperature", "Temperature Surface"),
    WIND("wind", "Wind Vector Streamlines"),
    HUMIDITY("humidity", "Relative Humidity"),
    RISK("risk", "Operational Hazard Risk")
}

data class MapUiState(
    val selectedLayer: WeatherMapLayer = WeatherMapLayer.RAIN,
    val centerCoordinates: MapLatLng = MapLatLng(28.6139, 77.2090),
    val zoomLevel: Double = 6.0,
    val timelineStepMinutes: Int = 0,
    val isPlaying: Boolean = false,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val mapSpec: RenderableMapSpecification = RenderableMapSpecification(
        id = "radar_composite_india",
        title = "National Meteorological Radar Composite",
        center = MapLatLng(28.6139, 77.2090),
        zoom = 6.0,
        bounds = MapBounds(
            southWest = MapLatLng(6.0, 68.0),
            northEast = MapLatLng(38.0, 98.0)
        ),
        layers = listOf(
            RenderableLayer(
                id = "radar_layer",
                name = "IMD Radar Composite",
                type = "raster",
                visible = true
            )
        ),
        legend = listOf(
            LegendItem(label = "Light Rain", color = "#81D4FA", valueRange = "0.1 - 2.5 mm/h"),
            LegendItem(label = "Moderate Rain", color = "#0288D1", valueRange = "2.5 - 15.0 mm/h"),
            LegendItem(label = "Heavy Rain", color = "#D32F2F", valueRange = "> 15.0 mm/h")
        ),
        quality = "AVAILABLE"
    )
)

class MapViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(MapUiState())
    val uiState: StateFlow<MapUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    centerCoordinates = MapLatLng(loc.latitude, loc.longitude)
                )
                loadMapSpec()
            }
        }
    }

    fun loadMapSpec() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            val lat = _uiState.value.centerCoordinates.latitude
            val lon = _uiState.value.centerCoordinates.longitude

            val result: ResultState<MapSpecification> = if (_uiState.value.selectedLayer == WeatherMapLayer.RISK) {
                repository.getRiskMap(latitude = lat, longitude = lon)
            } else {
                repository.getPointWeatherMap(latitude = lat, longitude = lon)
            }

            when (result) {
                is ResultState.Success<MapSpecification> -> {
                    val renderable = MapRendererAdapter.toRenderable(result.data)
                    _uiState.value = _uiState.value.copy(
                        mapSpec = renderable,
                        isLoading = false,
                        errorMessage = null
                    )
                }
                is ResultState.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = result.error.message
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(isLoading = false)
                }
            }
        }
    }

    fun setLayer(layer: WeatherMapLayer) {
        _uiState.value = _uiState.value.copy(selectedLayer = layer)
        loadMapSpec()
    }

    fun togglePlayback() {
        _uiState.value = _uiState.value.copy(isPlaying = !_uiState.value.isPlaying)
    }

    fun setTimelineStep(stepMinutes: Int) {
        _uiState.value = _uiState.value.copy(timelineStepMinutes = stepMinutes)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                MapViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
