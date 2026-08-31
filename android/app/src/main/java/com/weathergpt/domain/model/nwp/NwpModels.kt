package com.weathergpt.domain.model.nwp

data class NWPGridPoint(
    val model: String,
    val gridResolutionDeg: Double,
    val latitude: Double,
    val longitude: Double,
    val forecastLeadHours: Int,
    val validTime: String,
    val temperature2mC: Double,
    val relativeHumidity2mPct: Double,
    val accumulatedPrecipMm: Double,
    val windSpeedKmh: Double,
    val windDirectionDeg: Double,
    val windGustKmh: Double?,
    val pressureMslHpa: Double,
    val totalCloudCoverPct: Double
)

data class DivergenceAnalysis(
    val variable: String,
    val units: String,
    val modelsCompared: List<String>,
    val meanForecast: Double,
    val stdDev: Double,
    val divergenceRatio: Double,
    val agreementCategory: String,
    val isActionable: Boolean
)

data class NWPModelComparison(
    val latitude: Double,
    val longitude: Double,
    val forecastLeadHours: Int,
    val variable: String,
    val models: Map<String, Double>,
    val divergenceAnalysis: DivergenceAnalysis?
)
