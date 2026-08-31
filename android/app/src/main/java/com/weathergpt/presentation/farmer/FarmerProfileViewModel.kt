package com.weathergpt.presentation.farmer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class FarmerProfileUiState(
    val cropName: String = "Wheat",
    val cropStage: String = "Vegetative",
    val soilType: String = "Alluvial / Loam",
    val fieldAreaText: String = "2.5",
    val areaUnit: String = "Hectares",
    val validationError: String? = null,
    val isSavedSuccessfully: Boolean = false,
    val latitude: Double = 28.6139,
    val longitude: Double = 77.2090,
    val irrigationState: ResultState<IrrigationAdvisory> = ResultState.Idle,
    val sprayState: ResultState<SpraySuitability> = ResultState.Idle
)

class FarmerProfileViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(FarmerProfileUiState())
    val uiState: StateFlow<FarmerProfileUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    latitude = loc.latitude,
                    longitude = loc.longitude
                )
                loadAdvisories()
            }
        }
    }

    fun loadAdvisories() {
        viewModelScope.launch {
            val lat = _uiState.value.latitude
            val lon = _uiState.value.longitude

            _uiState.value = _uiState.value.copy(
                irrigationState = ResultState.Loading,
                sprayState = ResultState.Loading
            )

            val stageNormalized = when (_uiState.value.cropStage.lowercase()) {
                "sowing" -> "initial"
                "vegetative" -> "crop_development"
                "flowering" -> "mid_season"
                "maturity" -> "late_season"
                else -> "mid_season"
            }

            val soilNormalized = when {
                _uiState.value.soilType.contains("Alluvial", ignoreCase = true) -> "alluvial_loam"
                _uiState.value.soilType.contains("Black", ignoreCase = true) -> "black_cotton"
                _uiState.value.soilType.contains("Red", ignoreCase = true) -> "red_sandy"
                _uiState.value.soilType.contains("Clay", ignoreCase = true) -> "clay"
                else -> "alluvial_loam"
            }

            val irrResult = repository.getIrrigationAdvisory(
                latitude = lat,
                longitude = lon,
                cropName = _uiState.value.cropName.lowercase(),
                cropStage = stageNormalized,
                soilType = soilNormalized
            )

            val currentWeatherRes = repository.getCurrentWeather(lat, lon)
            val currentTemp = (currentWeatherRes as? ResultState.Success)?.data?.temperatureC ?: 28.0
            val currentWind = (currentWeatherRes as? ResultState.Success)?.data?.windSpeedKmh ?: 12.0
            val currentHumidity = (currentWeatherRes as? ResultState.Success)?.data?.relativeHumidityPct ?: 60.0

            val sprayResult = repository.getSprayWindowAdvisory(
                windSpeedKmh = currentWind,
                rainProbabilityPct = 10.0,
                tempC = currentTemp,
                relativeHumidityPct = currentHumidity
            )

            _uiState.value = _uiState.value.copy(
                irrigationState = irrResult,
                sprayState = sprayResult
            )
        }
    }

    fun setCrop(crop: String) {
        _uiState.value = _uiState.value.copy(cropName = crop, validationError = null)
        loadAdvisories()
    }

    fun setCropStage(stage: String) {
        _uiState.value = _uiState.value.copy(cropStage = stage, validationError = null)
        loadAdvisories()
    }

    fun setSoilType(soil: String) {
        _uiState.value = _uiState.value.copy(soilType = soil, validationError = null)
        loadAdvisories()
    }

    fun setFieldArea(area: String) {
        _uiState.value = _uiState.value.copy(fieldAreaText = area, validationError = null)
    }

    fun saveProfile(): Boolean {
        val area = _uiState.value.fieldAreaText.toDoubleOrNull()
        if (area == null || area <= 0.0) {
            _uiState.value = _uiState.value.copy(
                validationError = "Please enter a valid positive field area"
            )
            return false
        }

        _uiState.value = _uiState.value.copy(
            validationError = null,
            isSavedSuccessfully = true
        )
        loadAdvisories()
        return true
    }

    fun resetSaveState() {
        _uiState.value = _uiState.value.copy(isSavedSuccessfully = false)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                FarmerProfileViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
