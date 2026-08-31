package com.weathergpt.data.remote.dto.nwp

import com.weathergpt.data.remote.dto.weather.LocationCoordDto
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class GFSAtmosphericVariablesDto(
    @SerialName("temperature_2m_c")
    val temperature2mC: Double,
    @SerialName("relative_humidity_2m_pct")
    val relativeHumidity2mPct: Double,
    @SerialName("accumulated_precip_mm")
    val accumulatedPrecipMm: Double,
    @SerialName("wind_speed_kmh")
    val windSpeedKmh: Double,
    @SerialName("wind_direction_deg")
    val windDirectionDeg: Double,
    @SerialName("wind_gust_kmh")
    val windGustKmh: Double? = null,
    @SerialName("pressure_msl_hpa")
    val pressureMslHpa: Double,
    @SerialName("total_cloud_cover_pct")
    val totalCloudCoverPct: Double
)

@Serializable
data class GFSGridPointResponseDto(
    @SerialName("model")
    val model: String = "GFS_0p25",
    @SerialName("grid_resolution_deg")
    val gridResolutionDeg: Double = 0.25,
    @SerialName("location")
    val location: LocationCoordDto,
    @SerialName("forecast_lead_hours")
    val forecastLeadHours: Int,
    @SerialName("valid_time")
    val validTime: String,
    @SerialName("atmospheric_variables")
    val atmosphericVariables: GFSAtmosphericVariablesDto,
    @SerialName("provenance")
    val provenance: JsonObject? = null
)

@Serializable
data class DivergenceAnalysisDto(
    @SerialName("variable")
    val variable: String,
    @SerialName("units")
    val units: String,
    @SerialName("models_compared")
    val modelsCompared: List<String> = emptyList(),
    @SerialName("mean_forecast")
    val meanForecast: Double = 0.0,
    @SerialName("std_dev")
    val stdDev: Double = 0.0,
    @SerialName("divergence_ratio")
    val divergenceRatio: Double = 0.0,
    @SerialName("agreement_category")
    val agreementCategory: String = "HIGH_AGREEMENT",
    @SerialName("is_actionable")
    val isActionable: Boolean = true
)

@Serializable
data class NWPModelComparisonResponseDto(
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("forecast_lead_hours")
    val forecastLeadHours: Int,
    @SerialName("variable")
    val variable: String = "precipitation_mm",
    @SerialName("models")
    val models: Map<String, Double> = emptyMap(),
    @SerialName("divergence_analysis")
    val divergenceAnalysis: DivergenceAnalysisDto? = null
)
