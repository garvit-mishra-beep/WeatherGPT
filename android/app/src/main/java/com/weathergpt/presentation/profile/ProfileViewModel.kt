package com.weathergpt.presentation.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.PredefinedLocation
import com.weathergpt.core.location.SharedLocationManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class ProfileUiState(
    val userName: String = "Garvit Mishra",
    val userRole: String = "Agricultural Specialist & Researcher",
    val primaryLocation: String = "Surat, Gujarat",
    val planTier: String = "WeatherGPT Enterprise Intelligence Plan",
    val savedLocationsCount: Int = 11
)

class ProfileViewModel(
    private val locationManager: SharedLocationManager = SharedLocationManager()
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    val availableLocations: List<PredefinedLocation> get() = locationManager.availableLocations

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    primaryLocation = loc.formattedAddress,
                    savedLocationsCount = locationManager.availableLocations.size
                )
            }
        }
    }

    fun selectLocation(location: PredefinedLocation) {
        locationManager.selectPredefinedLocation(location)
    }

    fun updateUserName(name: String) {
        _uiState.value = _uiState.value.copy(userName = name)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as? WeatherGPTApplication)
                ProfileViewModel(
                    locationManager = app?.container?.sharedLocationManager ?: SharedLocationManager()
                )
            }
        }
    }
}
