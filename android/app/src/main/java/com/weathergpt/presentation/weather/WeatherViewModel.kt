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

    fun loadData() {
        viewModelScope.launch {
            val lat = _uiState.value.latitude
            val lon = _uiState.value.longitude

            _currentWeatherState.value = ResultState.Loading
            _forecastState.value = ResultState.Loading
            _intelligenceState.value = ResultState.Loading

            _currentWeatherState.value = repository.getCurrentWeather(lat, lon)
            _forecastState.value = repository.getWeatherForecast(lat, lon, days = 7, hourly = true)
            _intelligenceState.value = repository.getWeatherIntelligence(lat, lon, leadHours = 24, includeNwp = true)
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
