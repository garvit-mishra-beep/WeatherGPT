package com.weathergpt.presentation.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

import androidx.annotation.StringRes
import com.weathergpt.R

enum class AlertCategory(@StringRes val titleResId: Int) {
    ALL(R.string.filter_all),
    WEATHER(R.string.filter_weather),
    AGRICULTURE(R.string.filter_agri),
    GOVERNMENT(R.string.filter_govt)
}

data class AlertsUiState(
    val selectedCategoryIndex: Int = 0,
    val selectedDistrict: String = "Jhansi",
    val locationName: String = "Jhansi, Uttar Pradesh",
    val latitude: Double = 25.4484,
    val longitude: Double = 78.5685
)

class AlertsViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AlertsUiState())
    val uiState: StateFlow<AlertsUiState> = _uiState.asStateFlow()

    private val _alertsState = MutableStateFlow<ResultState<WeatherAlertsReport>>(ResultState.Idle)
    val alertsState: StateFlow<ResultState<WeatherAlertsReport>> = _alertsState.asStateFlow()

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    selectedDistrict = loc.districtName,
                    locationName = loc.formattedAddress,
                    latitude = loc.latitude,
                    longitude = loc.longitude
                )
                loadAlerts()
            }
        }
    }

    fun loadAlerts() {
        viewModelScope.launch {
            _alertsState.value = ResultState.Loading
            _alertsState.value = repository.getWeatherAlerts(
                district = _uiState.value.selectedDistrict,
                latitude = _uiState.value.latitude,
                longitude = _uiState.value.longitude
            )
        }
    }

    fun selectCategoryIndex(index: Int) {
        _uiState.value = _uiState.value.copy(selectedCategoryIndex = index)
    }

    fun setDistrict(district: String) {
        _uiState.value = _uiState.value.copy(
            selectedDistrict = district,
            locationName = "$district, Uttar Pradesh"
        )
        loadAlerts()
    }

    val availableLocations get() = locationManager.availableLocations

    fun selectPredefinedLocation(location: com.weathergpt.core.location.PredefinedLocation) {
        locationManager.selectPredefinedLocation(location)
    }

    fun getFilteredAlerts(report: WeatherAlertsReport): List<OfficialAlert> {
        val category = AlertCategory.entries.getOrElse(_uiState.value.selectedCategoryIndex) { AlertCategory.ALL }
        return when (category) {
            AlertCategory.ALL -> report.alerts
            AlertCategory.WEATHER -> report.alerts.filter { alert ->
                isWeatherAlert(alert)
            }
            AlertCategory.AGRICULTURE -> report.alerts.filter { alert ->
                isAgricultureAlert(alert)
            }
            AlertCategory.GOVERNMENT -> report.alerts.filter { alert ->
                isGovernmentAlert(alert, report.authority)
            }
        }
    }

    fun sortAlerts(alerts: List<OfficialAlert>): List<OfficialAlert> {
        val severityRank = mapOf(
            com.weathergpt.domain.model.weather.AlertSeverity.RED to 1,
            com.weathergpt.domain.model.weather.AlertSeverity.ORANGE to 2,
            com.weathergpt.domain.model.weather.AlertSeverity.YELLOW to 3,
            com.weathergpt.domain.model.weather.AlertSeverity.GREEN to 4
        )
        return alerts.sortedWith(
            compareBy<OfficialAlert> { severityRank[it.parsedSeverity] ?: 5 }
                .thenByDescending { it.isActive }
                .thenBy { it.validUntil.ifBlank { it.expiresAt } }
                .thenByDescending { it.issuedAt }
        )
    }

    fun getSortedFilteredAlerts(report: WeatherAlertsReport): List<OfficialAlert> {
        return sortAlerts(getFilteredAlerts(report))
    }

    private fun isWeatherAlert(alert: OfficialAlert): Boolean {
        val weatherKeywords = listOf(
            "Rain", "Flood", "Storm", "Thunderstorm", "Lightning", "Wind", "Squall",
            "Heat", "Heatwave", "Cold", "Coldwave", "Cyclone", "Fog", "Smog", "Frost",
            "Snow", "Hail", "Gale", "Blizzard", "Monsoon", "Weather", "Depression"
        )
        val text = "${alert.hazard} ${alert.headline} ${alert.description}"
        return weatherKeywords.any { text.contains(it, ignoreCase = true) }
    }

    private fun isAgricultureAlert(alert: OfficialAlert): Boolean {
        val agriKeywords = listOf(
            "Crop", "Harvest", "Sowing", "Pest", "Agri", "Agriculture", "Irrigation",
            "Fertilizer", "Livestock", "Soil", "Mandi", "Kisan", "Farming", "Field"
        )
        val text = "${alert.hazard} ${alert.headline} ${alert.description} ${alert.instructions.orEmpty()}"
        return agriKeywords.any { text.contains(it, ignoreCase = true) }
    }

    private fun isGovernmentAlert(alert: OfficialAlert, authority: String): Boolean {
        val govtKeywords = listOf(
            "NDMA", "SDRF", "NDRF", "Disaster Management", "Administration", "Collector",
            "Magistrate", "Evacuation", "Curfew", "Relief", "Civil Defense", "Public Safety",
            "Municipal", "Govt", "Government", "Emergency Advisory", "Order"
        )
        val alertText = "${alert.hazard} ${alert.headline} ${alert.description} ${alert.instructions.orEmpty()}"
        return govtKeywords.any { alertText.contains(it, ignoreCase = true) || authority.contains(it, ignoreCase = true) }
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                AlertsViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
