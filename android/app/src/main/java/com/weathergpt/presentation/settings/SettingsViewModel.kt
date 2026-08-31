package com.weathergpt.presentation.settings

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.config.ValidationResult
import com.weathergpt.core.settings.AppLanguage
import com.weathergpt.core.settings.SharedSettingsManager
import com.weathergpt.core.settings.UnitSystem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class SettingsUiState(
    val language: AppLanguage = AppLanguage.HINDI,
    val unitSystem: UnitSystem = UnitSystem.METRIC,
    val notificationsEnabled: Boolean = true,
    val currentBaseUrl: String = AppConfig.apiBaseUrl,
    val urlValidationError: String? = null
) {
    val selectedLanguage: String
        get() = when (language) {
            AppLanguage.ENGLISH -> "English"
            AppLanguage.HINDI -> "हिन्दी"
        }

    val selectedUnits: String
        get() = when (unitSystem) {
            UnitSystem.METRIC -> "Metric (°C, km/h)"
            UnitSystem.IMPERIAL -> "Imperial (°F, mph)"
        }
}

class SettingsViewModel(
    private val settingsManager: SharedSettingsManager = SharedSettingsManager()
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        SettingsUiState(
            language = settingsManager.appLanguage.value,
            unitSystem = settingsManager.unitSystem.value,
            notificationsEnabled = settingsManager.notificationsEnabled.value
        )
    )
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            settingsManager.appLanguage.collectLatest { lang ->
                _uiState.value = _uiState.value.copy(language = lang)
            }
        }
        viewModelScope.launch {
            settingsManager.unitSystem.collectLatest { units ->
                _uiState.value = _uiState.value.copy(unitSystem = units)
            }
        }
        viewModelScope.launch {
            settingsManager.notificationsEnabled.collectLatest { enabled ->
                _uiState.value = _uiState.value.copy(notificationsEnabled = enabled)
            }
        }
    }

    fun setLanguage(language: AppLanguage) {
        _uiState.value = _uiState.value.copy(language = language)
        settingsManager.setLanguage(language)
    }

    fun setLanguage(languageName: String) {
        val lang = when {
            languageName.contains("English", ignoreCase = true) -> AppLanguage.ENGLISH
            else -> AppLanguage.HINDI
        }
        _uiState.value = _uiState.value.copy(language = lang)
        settingsManager.setLanguage(lang)
    }

    fun setUnits(unitSystem: UnitSystem) {
        _uiState.value = _uiState.value.copy(unitSystem = unitSystem)
        settingsManager.setUnitSystem(unitSystem)
    }

    fun setUnits(unitName: String) {
        val units = when {
            unitName.contains("Imperial", ignoreCase = true) || unitName.contains("इंपीरियल", ignoreCase = true) -> UnitSystem.IMPERIAL
            else -> UnitSystem.METRIC
        }
        _uiState.value = _uiState.value.copy(unitSystem = units)
        settingsManager.setUnitSystem(units)
    }

    fun toggleNotifications(enabled: Boolean) {
        _uiState.value = _uiState.value.copy(notificationsEnabled = enabled)
        settingsManager.setNotificationsEnabled(enabled)
    }

    fun updateBackendUrl(newUrl: String, context: Context? = null): Boolean {
        return when (val result = AppConfig.setCustomBaseUrl(newUrl, context)) {
            is ValidationResult.Success -> {
                _uiState.value = _uiState.value.copy(
                    currentBaseUrl = result.normalizedUrl,
                    urlValidationError = null
                )
                true
            }
            is ValidationResult.Error -> {
                _uiState.value = _uiState.value.copy(
                    urlValidationError = result.message
                )
                false
            }
        }
    }

    fun resetBackendUrl(context: Context? = null) {
        AppConfig.resetToDefault(context)
        _uiState.value = _uiState.value.copy(
            currentBaseUrl = AppConfig.apiBaseUrl,
            urlValidationError = null
        )
    }

    fun clearValidationError() {
        _uiState.value = _uiState.value.copy(urlValidationError = null)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as? WeatherGPTApplication)
                val manager = app?.container?.sharedSettingsManager ?: SharedSettingsManager()
                SettingsViewModel(settingsManager = manager)
            }
        }
    }
}
