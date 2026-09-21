package com.weathergpt.presentation.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.usecase.CheckHealthUseCase
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * Hardened ViewModel demonstrating asynchronous data flow, structured cancellation,
 * and lifecycle-safe network state monitoring.
 *
 * NOTE: Final UI/UX and feature ViewModels will be developed in collaboration with Pragya.
 */
class MainViewModel(
    private val checkHealthUseCase: CheckHealthUseCase,
    networkMonitor: NetworkMonitor,
    private val settingsManager: com.weathergpt.core.settings.SharedSettingsManager = com.weathergpt.core.settings.SharedSettingsManager()
) : ViewModel() {

    private val _healthState = MutableStateFlow<ResultState<HealthStatus>>(ResultState.Idle)
    val healthState: StateFlow<ResultState<HealthStatus>> = _healthState.asStateFlow()

    val appLanguage: StateFlow<com.weathergpt.core.settings.AppLanguage> = settingsManager.appLanguage

    val networkState: StateFlow<NetworkState> = networkMonitor.networkState.stateIn(
        scope = viewModelScope,
        started = SharingStarted.Eagerly,
        initialValue = if (networkMonitor.isOnline) NetworkState.Available else NetworkState.Unavailable
    )

    private val _currentBaseUrl = MutableStateFlow(com.weathergpt.core.config.AppConfig.apiBaseUrl)
    val currentBaseUrl: StateFlow<String> = _currentBaseUrl.asStateFlow()

    private val _urlValidationError = MutableStateFlow<String?>(null)
    val urlValidationError: StateFlow<String?> = _urlValidationError.asStateFlow()

    private val _pendingDestination = MutableStateFlow<com.weathergpt.presentation.navigation.ScreenDestination?>(null)
    val pendingDestination: StateFlow<com.weathergpt.presentation.navigation.ScreenDestination?> = _pendingDestination.asStateFlow()

    fun navigateTo(destination: com.weathergpt.presentation.navigation.ScreenDestination) {
        _pendingDestination.value = destination
    }

    fun clearPendingDestination() {
        _pendingDestination.value = null
    }

    private var activeJob: Job? = null

    init {
        verifyBackendConnectivity()
    }

    fun verifyBackendConnectivity() {
        // Cancel in-flight job to avoid stale response race conditions
        activeJob?.cancel()
        activeJob = viewModelScope.launch {
            _healthState.value = ResultState.Loading
            try {
                _healthState.value = checkHealthUseCase()
            } catch (_: CancellationException) {
                // Ignore intentional job cancellation without mutating state to an error
            }
        }
    }

    fun updateBackendUrl(newUrl: String, context: android.content.Context? = null): Boolean {
        when (val result = com.weathergpt.core.config.AppConfig.setCustomBaseUrl(newUrl, context)) {
            is com.weathergpt.core.config.ValidationResult.Success -> {
                _currentBaseUrl.value = result.normalizedUrl
                _urlValidationError.value = null
                verifyBackendConnectivity()
                return true
            }
            is com.weathergpt.core.config.ValidationResult.Error -> {
                _urlValidationError.value = result.message
                return false
            }
        }
    }

    fun resetBackendUrl(context: android.content.Context? = null) {
        com.weathergpt.core.config.AppConfig.resetToDefault(context)
        _currentBaseUrl.value = com.weathergpt.core.config.AppConfig.apiBaseUrl
        _urlValidationError.value = null
        verifyBackendConnectivity()
    }

    fun clearValidationError() {
        _urlValidationError.value = null
    }

    override fun onCleared() {
        super.onCleared()
        activeJob?.cancel()
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val application = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                MainViewModel(
                    checkHealthUseCase = application.container.checkHealthUseCase,
                    networkMonitor = application.container.networkMonitor,
                    settingsManager = application.container.sharedSettingsManager
                )
            }
        }
    }
}
