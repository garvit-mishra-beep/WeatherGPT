package com.weathergpt.presentation.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.presentation.components.IntelligenceBrain
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class HomeUiState(
    val selectedBrain: IntelligenceBrain = IntelligenceBrain.AUTO,
    val locationName: String = "Jhansi, Uttar Pradesh",
    val latitude: Double = 25.4484,
    val longitude: Double = 78.5685,
    val queryInput: String = "",
    val activeAlertsCount: Int = 0,
    val topAlertHeadline: String? = null,
    val topAlertLevel: String? = null,
    val userName: String = "Garvit"
)

class HomeViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager,
    private val brainManager: SharedBrainManager = SharedBrainManager()
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState(selectedBrain = brainManager.selectedBrain.value))
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private val _weatherState = MutableStateFlow<ResultState<CurrentWeather>>(ResultState.Idle)
    val weatherState: StateFlow<ResultState<CurrentWeather>> = _weatherState.asStateFlow()

    init {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            _uiState.value = _uiState.value.copy(
                locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
            )
            loadWeather()
            loadAlerts(com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_DISTRICT)
        } else {
            viewModelScope.launch {
                locationManager.locationState.collectLatest { loc ->
                    _uiState.value = _uiState.value.copy(
                        locationName = loc.formattedAddress,
                        latitude = loc.latitude,
                        longitude = loc.longitude
                    )
                    loadWeather()
                    loadAlerts(loc.districtName)
                }
            }
        }

        viewModelScope.launch {
            brainManager.selectedBrain.collectLatest { brain ->
                _uiState.value = _uiState.value.copy(selectedBrain = brain)
            }
        }
    }

    fun loadWeather() {
        viewModelScope.launch {
            val previousData = (_weatherState.value as? ResultState.Success<CurrentWeather>)?.data
            if (previousData == null) {
                _weatherState.value = ResultState.Loading
            }

            val isDemo = com.weathergpt.core.config.AppConfig.isDemoMode
            val currentLat = if (isDemo) com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE else _uiState.value.latitude
            val currentLon = if (isDemo) com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE else _uiState.value.longitude

            if (isDemo) {
                _uiState.value = _uiState.value.copy(
                    locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                    latitude = currentLat,
                    longitude = currentLon
                )
            }

            val state = repository.getCurrentWeather(
                latitude = currentLat,
                longitude = currentLon
            )
            when (state) {
                is ResultState.Success -> {
                    if (state.data.sourceMode == com.weathergpt.domain.model.weather.WeatherDataSourceMode.LIVE) {
                        _weatherState.value = state
                        // When online and not in demo mode, prefetch real Gwalior weather in background
                        if (!isDemo) {
                            launch { repository.prefetchDemoWeather() }
                        }
                    } else {
                        // Repository returned cached weather (offline / API failure / Demo Mode)
                        _weatherState.value = state
                        _uiState.value = _uiState.value.copy(
                            locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                            latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                            longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
                        )
                    }
                }
                is ResultState.Error -> {
                    if (previousData != null && isGwaliorLocation(previousData.location.latitude, previousData.location.longitude)) {
                        // Live retry failed: remain in DEMO_MODE with Gwalior, keep cached weather visible
                        _weatherState.value = ResultState.Success(
                            previousData.copy(sourceMode = com.weathergpt.domain.model.weather.WeatherDataSourceMode.DEMO_MODE)
                        )
                        _uiState.value = _uiState.value.copy(
                            locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                            latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                            longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
                        )
                    } else {
                        // Demo Mode showcase fallback: query Gwalior cache
                        val gwaliorState = repository.getCurrentWeather(
                            latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                            longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
                        )
                        _weatherState.value = gwaliorState
                        _uiState.value = _uiState.value.copy(
                            locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                            latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                            longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
                        )
                        if (gwaliorState is ResultState.Success) {
                            loadAlerts(com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_DISTRICT)
                        }
                    }
                }
                else -> {
                    _weatherState.value = state
                }
            }
        }
    }

    private fun isGwaliorLocation(lat: Double, lon: Double): Boolean {
        return kotlin.math.abs(lat - com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE) < 0.05 &&
               kotlin.math.abs(lon - com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE) < 0.05
    }

    fun loadAlerts(district: String = _uiState.value.locationName.substringBefore(",").trim()) {
        viewModelScope.launch {
            when (val res = repository.getWeatherAlerts(
                district = district,
                latitude = _uiState.value.latitude,
                longitude = _uiState.value.longitude
            )) {
                is ResultState.Success<WeatherAlertsReport> -> {
                    val topAlert = res.data.alerts.firstOrNull()
                    _uiState.value = _uiState.value.copy(
                        activeAlertsCount = res.data.activeAlertsCount,
                        topAlertHeadline = topAlert?.headline,
                        topAlertLevel = topAlert?.warningColor
                    )
                }
                else -> { /* Retain current */ }
            }
        }
    }

    fun setQueryInput(query: String) {
        _uiState.value = _uiState.value.copy(queryInput = query)
    }

    fun selectBrain(brain: IntelligenceBrain) {
        _uiState.value = _uiState.value.copy(selectedBrain = brain)
        brainManager.selectBrain(brain)
    }

    val availableLocations get() = locationManager.availableLocations

    fun selectPredefinedLocation(loc: com.weathergpt.core.location.PredefinedLocation) {
        locationManager.selectPredefinedLocation(loc)
    }

    fun setLocation(name: String, lat: Double, lon: Double) {
        locationManager.updateLocation(
            district = name.substringBefore(",").trim(),
            state = name.substringAfter(",", "Gujarat").trim(),
            latitude = lat,
            longitude = lon
        )
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                HomeViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager,
                    brainManager = app.container.sharedBrainManager
                )
            }
        }
    }
}
