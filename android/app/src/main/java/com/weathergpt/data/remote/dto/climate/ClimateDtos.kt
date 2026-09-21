package com.weathergpt.data.remote.dto.climate

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class ClimateTrendsResponseDto(
    @SerialName("location")
    val location: String,
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("variable")
    val variable: String,
    @SerialName("trend_slope")
    val trendSlope: Double,
    @SerialName("p_value")
    val pValue: Double,
    @SerialName("is_significant")
    val isSignificant: Boolean,
    @SerialName("direction")
    val direction: String,
    @SerialName("sample_size")
    val sampleSize: Int,
    @SerialName("period")
    val period: String,
    @SerialName("method")
    val method: String = "Mann-Kendall & Sen's Slope",
    @SerialName("provenance")
    val provenance: JsonObject? = null
)

@Serializable
data class ClimateNormalsResponseDto(
    @SerialName("location")
    val location: String,
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("month")
    val month: Int,
    @SerialName("normal_rainfall_mm")
    val normalRainfallMm: Double? = null,
    @SerialName("actual_rainfall_mm")
    val actualRainfallMm: Double? = null,
    @SerialName("rainfall_anomaly_pct")
    val rainfallAnomalyPct: Double? = null,
    @SerialName("normal_temp_c")
    val normalTempC: Double? = null,
    @SerialName("actual_temp_c")
    val actualTempC: Double? = null,
    @SerialName("temp_anomaly_c")
    val tempAnomalyC: Double? = null,
    @SerialName("category")
    val category: String = "Near Normal",
    @SerialName("source")
    val source: String = "IMD Climatological Tables of Observatories in India (1991-2020)",
    @SerialName("reference_period")
    val referencePeriod: String = "1991-2020",
    @SerialName("provenance")
    val provenance: JsonObject? = null
)
