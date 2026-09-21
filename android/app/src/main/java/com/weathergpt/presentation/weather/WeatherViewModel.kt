package com.weathergpt.presentation.weather

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

import androidx.annotation.StringRes
import com.weathergpt.R

enum class ForecastInterval(@StringRes val titleResId: Int) {
    HOURLY(R.string.tab_hourly),
    THREE_DAYS(R.string.tab_3day),
    FIVE_DAYS(R.string.tab_5day),
    TEN_DAYS(R.string.tab_10day)
}

data class WeatherScreenUiState(
    val locationName: String = "Jhansi, Uttar Pradesh",
    val latitude: Double = 25.4484,
    val longitude: Double = 78.5685,
    val selectedInterval: ForecastInterval = ForecastInterval.HOURLY
)

class WeatherViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(WeatherScreenUiState())
    val uiState: StateFlow<WeatherScreenUiState> = _uiState.asStateFlow()

    private val _currentWeatherState = MutableStateFlow<ResultState<CurrentWeather>>(ResultState.Idle)
    val currentWeatherState: StateFlow<ResultState<CurrentWeather>> = _currentWeatherState.asStateFlow()

    private val _forecastState = MutableStateFlow<ResultState<WeatherForecast>>(ResultState.Idle)
    val forecastState: StateFlow<ResultState<WeatherForecast>> = _forecastState.asStateFlow()

    private val _intelligenceState = MutableStateFlow<ResultState<WeatherIntelligence>>(ResultState.Idle)
    val intelligenceState: StateFlow<ResultState<WeatherIntelligence>> = _intelligenceState.asStateFlow()

    init {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            _uiState.value = _uiState.value.copy(
                locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE,
                selectedInterval = ForecastInterval.TEN_DAYS
            )
            loadData()
        } else {
            viewModelScope.launch {
                locationManager.locationState.collectLatest { loc ->
                    _uiState.value = _uiState.value.copy(
                        locationName = loc.formattedAddress,
                        latitude = loc.latitude,
                        longitude = loc.longitude
                    )
                    loadData()
                }
            }
        }
    }

    fun loadData() {
        viewModelScope.launch {
            val isDemo = com.weathergpt.core.config.AppConfig.isDemoMode
            val lat = if (isDemo) com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE else _uiState.value.latitude
            val lon = if (isDemo) com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE else _uiState.value.longitude

            if (isDemo) {
                _uiState.value = _uiState.value.copy(
                    locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                    latitude = lat,
                    longitude = lon
                )
            }

            val prevWeather = (_currentWeatherState.value as? ResultState.Success<CurrentWeather>)?.data
            val prevForecast = (_forecastState.value as? ResultState.Success<WeatherForecast>)?.data

            if (prevWeather == null) _currentWeatherState.value = ResultState.Loading
            if (prevForecast == null) _forecastState.value = ResultState.Loading
            _intelligenceState.value = ResultState.Loading

            val weatherRes = repository.getCurrentWeather(lat, lon)
            val finalWeatherRes = if (weatherRes is ResultState.Success) {
                if (weatherRes.data.sourceMode == com.weathergpt.domain.model.weather.WeatherDataSourceMode.LIVE) {
                    weatherRes
                } else {
                    weatherRes
                }
            } else if (prevWeather != null && isGwaliorLocation(prevWeather.location.latitude, prevWeather.location.longitude)) {
                ResultState.Success(
                    prevWeather.copy(sourceMode = com.weathergpt.domain.model.weather.WeatherDataSourceMode.DEMO_MODE)
                )
            } else {
                repository.getCurrentWeather(
                    com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                    com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
                )
            }
            _currentWeatherState.value = finalWeatherRes
            if (finalWeatherRes is ResultState.Success && finalWeatherRes.data.sourceMode == com.weathergpt.domain.model.weather.WeatherDataSourceMode.DEMO_MODE) {
                _uiState.value = _uiState.value.copy(
                    locationName = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LOCATION_NAME,
                    latitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE,
                    longitude = com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE
                )
            }

            val targetLat = _uiState.value.latitude
            val targetLon = _uiState.value.longitude
            val forecastRes = repository.getWeatherForecast(targetLat, targetLon, days = 10, hourly = true)
            if (forecastRes is ResultState.Error && prevForecast != null) {
                _forecastState.value = ResultState.Success(
                    prevForecast.copy(sourceMode = com.weathergpt.domain.model.weather.WeatherDataSourceMode.DEMO_MODE)
                )
            } else {
                _forecastState.value = forecastRes
            }

            _intelligenceState.value = repository.getWeatherIntelligence(targetLat, targetLon, leadHours = 24, includeNwp = true)
        }
    }

    val availableLocations get() = locationManager.availableLocations

    fun selectPredefinedLocation(loc: com.weathergpt.core.location.PredefinedLocation) {
        locationManager.selectPredefinedLocation(loc)
    }

    fun setInterval(interval: ForecastInterval) {
        _uiState.value = _uiState.value.copy(selectedInterval = interval)
    }

    fun setLocation(name: String, lat: Double, lon: Double) {
        locationManager.updateLocation(
            district = name.substringBefore(",").trim(),
            state = name.substringAfter(",", "Uttar Pradesh").trim(),
            latitude = lat,
            longitude = lon
        )
    }

    private fun isGwaliorLocation(lat: Double, lon: Double): Boolean {
        return kotlin.math.abs(lat - com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LATITUDE) < 0.05 &&
               kotlin.math.abs(lon - com.weathergpt.core.location.SharedLocationManager.DEMO_GWALIOR_LONGITUDE) < 0.05
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                WeatherViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
