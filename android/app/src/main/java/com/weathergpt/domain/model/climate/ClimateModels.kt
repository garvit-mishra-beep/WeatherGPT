package com.weathergpt.domain.model.climate

import com.weathergpt.data.remote.dto.climate.ClimateNormalsResponseDto
import com.weathergpt.data.remote.dto.climate.ClimateTrendsResponseDto

data class ClimateTrends(
    val location: String,
    val latitude: Double,
    val longitude: Double,
    val variable: String,
    val trendSlope: Double,
    val pValue: Double,
    val isSignificant: Boolean,
    val direction: String,
    val sampleSize: Int,
    val period: String,
    val method: String
)

data class ClimateNormals(
    val location: String,
    val latitude: Double,
    val longitude: Double,
    val month: Int,
    val normalRainfallMm: Double?,
    val actualRainfallMm: Double?,
    val rainfallAnomalyPct: Double?,
    val normalTempC: Double?,
    val actualTempC: Double?,
    val tempAnomalyC: Double?,
    val category: String,
    val source: String,
    val referencePeriod: String
)

fun ClimateTrendsResponseDto.toDomain(): ClimateTrends {
    return ClimateTrends(
        location = location,
        latitude = latitude,
        longitude = longitude,
        variable = variable,
        trendSlope = trendSlope,
        pValue = pValue,
        isSignificant = isSignificant,
        direction = direction,
        sampleSize = sampleSize,
        period = period,
        method = method
    )
}

fun ClimateNormalsResponseDto.toDomain(): ClimateNormals {
    return ClimateNormals(
        location = location,
        latitude = latitude,
        longitude = longitude,
        month = month,
        normalRainfallMm = normalRainfallMm,
        actualRainfallMm = actualRainfallMm,
        rainfallAnomalyPct = rainfallAnomalyPct,
        normalTempC = normalTempC,
        actualTempC = actualTempC,
        tempAnomalyC = tempAnomalyC,
        category = category,
        source = source,
        referencePeriod = referencePeriod
    )
}
