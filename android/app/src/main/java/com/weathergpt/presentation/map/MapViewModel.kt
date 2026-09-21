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

data class MapCity(
    val name: String,
    val latitude: Double,
    val longitude: Double
)

data class MapUiState(
    val selectedLayer: WeatherMapLayer = WeatherMapLayer.RAIN,
    val centerCoordinates: MapLatLng = MapLatLng(22.72, 78.65),
    val zoomLevel: Double = 5.0,
    val selectedCityName: String = "Indore",
    val defaultCities: List<MapCity> = listOf(
        MapCity("Indore", 22.7196, 75.8577),
        MapCity("Delhi", 28.6139, 77.2090),
        MapCity("Mumbai", 19.0760, 72.8777),
        MapCity("Chennai", 13.0827, 80.2707)
    ),
    val timelineStepMinutes: Int = 0,
    val isPlaying: Boolean = false,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val mapSpec: RenderableMapSpecification = RenderableMapSpecification(
        id = "radar_composite_india",
        title = "National Meteorological Radar Composite",
        center = MapLatLng(22.72, 78.65),
        zoom = 5.0,
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
                    centerCoordinates = MapLatLng(loc.latitude, loc.longitude),
                    selectedCityName = loc.districtName
                )
                loadMapSpec()
            }
        }
    }

    fun onLocationSelected(latitude: Double, longitude: Double, label: String) {
        viewModelScope.launch {
            val dist = if (label.isNotBlank() && label != "Selected location" && label != "Your Location") {
                label
            } else {
                _uiState.value.selectedCityName
            }
            _uiState.value = _uiState.value.copy(
                centerCoordinates = MapLatLng(latitude, longitude),
                selectedCityName = dist
            )
            locationManager.updateLocation(
                district = dist,
                state = locationManager.locationState.value.stateName,
                latitude = latitude,
                longitude = longitude
            )
            locationManager.resolveLocationHierarchy(repository)
        }
    }

    fun selectCity(city: MapCity) {
        onLocationSelected(city.latitude, city.longitude, city.name)
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
        fun getWeatherVisual(code: Int): String {
            return when (code) {
                0 -> "☀️"
                1, 2, 3 -> if (code == 2) "⛅" else "☁️"
                45, 48 -> "🌫️"
                in 51..57 -> "🌦️"
                in 61..67, in 80..82 -> "🌧️"
                in 71..77 -> "🌨️"
                in 95..99 -> "⛈️"
                else -> "☁️"
            }
        }

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
