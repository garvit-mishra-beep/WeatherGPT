package com.weathergpt.presentation.analyst

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class AnalystDashboardUiState(
    val districtName: String = "New Delhi",
    val hazardType: String = "Heavy Rainfall / Squall",
    val hazardSeverity: Double = 6.5,
    val exposureIndex: Double = 8.0,
    val vulnerabilityIndex: Double = 7.0,
    val compositeRiskScore: Double = 7.05,
    val riskCategory: String = "HIGH",
    val actionPriority: String = "Priority 1 — Immediate Drainage Clearance",
    val latitude: Double = 28.6139,
    val longitude: Double = 77.2090,
    val riskAssessmentState: ResultState<OperationalRisk> = ResultState.Idle,
    val gisAnalysisState: ResultState<GISAnalysisReport> = ResultState.Idle
)

class AnalystDashboardViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AnalystDashboardUiState())
    val uiState: StateFlow<AnalystDashboardUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    districtName = loc.districtName,
                    latitude = loc.latitude,
                    longitude = loc.longitude
                )
                loadAnalysis()
            }
        }
    }

    fun loadAnalysis() {
        viewModelScope.launch {
            val dist = _uiState.value.districtName
            val lat = _uiState.value.latitude
            val lon = _uiState.value.longitude

            _uiState.value = _uiState.value.copy(
                riskAssessmentState = ResultState.Loading,
                gisAnalysisState = ResultState.Loading
            )

            val riskResult = repository.getRiskAssessment(
                districtName = dist,
                precip24hPercentile = 85.0,
                exposureIndex = _uiState.value.exposureIndex,
                vulnerabilityIndex = _uiState.value.vulnerabilityIndex,
                hazardType = "heavy_rainfall"
            )

            val gisResult = repository.getGISAnalysis(
                latitude = lat,
                longitude = lon,
                districtCode = null,
                leadHours = 24
            )

            val updatedComposite = if (riskResult is ResultState.Success<OperationalRisk>) {
                riskResult.data.compositeRiskScore
            } else _uiState.value.compositeRiskScore

            val updatedCategory = if (riskResult is ResultState.Success<OperationalRisk>) {
                riskResult.data.riskLevel
            } else _uiState.value.riskCategory

            _uiState.value = _uiState.value.copy(
                riskAssessmentState = riskResult,
                gisAnalysisState = gisResult,
                compositeRiskScore = updatedComposite,
                riskCategory = updatedCategory
            )
        }
    }

    fun updateScores(hazard: Double, exposure: Double, vulnerability: Double) {
        val composite = 0.50 * hazard + 0.30 * exposure + 0.20 * vulnerability
        val category = when {
            composite >= 7.0 -> "HIGH"
            composite >= 4.0 -> "MODERATE"
            else -> "LOW"
        }
        _uiState.value = _uiState.value.copy(
            hazardSeverity = hazard,
            exposureIndex = exposure,
            vulnerabilityIndex = vulnerability,
            compositeRiskScore = composite,
            riskCategory = category
        )
        loadAnalysis()
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                AnalystDashboardViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
