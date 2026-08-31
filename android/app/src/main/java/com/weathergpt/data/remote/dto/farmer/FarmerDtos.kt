package com.weathergpt.data.remote.dto.farmer

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class IrrigationAdvisoryRequestDto(
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("crop_name")
    val cropName: String,
    @SerialName("crop_stage")
    val cropStage: String = "mid_season",
    @SerialName("soil_type")
    val soilType: String = "alluvial_loam",
    @SerialName("last_irrigation_date")
    val lastIrrigationDate: String? = null,
    @SerialName("forecast_precip_48h_mm")
    val forecastPrecip48hMm: Double = 0.0
)

@Serializable
data class CropWaterMetricsDto(
    @SerialName("reference_et0_mm_day")
    val referenceEt0MmDay: Double,
    @SerialName("crop_kc")
    val cropKc: Double,
    @SerialName("daily_water_demand_mm")
    val dailyWaterDemandMm: Double,
    @SerialName("forecast_rainfall_48h_mm")
    val forecastRainfall48hMm: Double,
    @SerialName("net_deficit_mm")
    val netDeficitMm: Double,
    @SerialName("final_depletion_mm")
    val finalDepletionMm: Double
)

@Serializable
data class FarmerProvenanceDto(
    @SerialName("calculation_method")
    val calculationMethod: String,
    @SerialName("soil_water_balance")
    val soilWaterBalance: String? = null,
    @SerialName("engine_version")
    val engineVersion: String = "1.0.0"
)

@Serializable
data class IrrigationAdvisoryResponseDto(
    @SerialName("action")
    val action: String, // "IRRIGATE", "WAIT_RAIN_EXPECTED", "MONITOR", "DRAIN_EXCESS"
    @SerialName("urgency")
    val urgency: String = "medium",
    @SerialName("metrics")
    val metrics: CropWaterMetricsDto,
    @SerialName("rationale")
    val rationale: String,
    @SerialName("provenance")
    val provenance: FarmerProvenanceDto? = null
)

@Serializable
data class SprayWindowRequestDto(
    @SerialName("wind_speed_kmh")
    val windSpeedKmh: Double,
    @SerialName("rain_probability_pct")
    val rainProbabilityPct: Double,
    @SerialName("temp_c")
    val tempC: Double = 28.0,
    @SerialName("relative_humidity_pct")
    val relativeHumidityPct: Double = 60.0
)

@Serializable
data class SprayWindowResponseDto(
    @SerialName("is_suitable")
    val isSuitable: Boolean,
    @SerialName("condition_level")
    val conditionLevel: String, // "optimal", "unfavorable"
    @SerialName("recommendation")
    val recommendation: String,
    @SerialName("wind_suitable")
    val windSuitable: Boolean,
    @SerialName("rain_probability_suitable")
    val rainProbabilitySuitable: Boolean,
    @SerialName("provenance")
    val provenance: FarmerProvenanceDto? = null
)
