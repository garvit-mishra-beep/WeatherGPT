package com.weathergpt.domain.model.farmer

data class CropWaterBalanceMetrics(
    val referenceEt0MmDay: Double,
    val cropKc: Double,
    val dailyWaterDemandMm: Double,
    val forecastRainfall48hMm: Double,
    val netDeficitMm: Double,
    val finalDepletionMm: Double
)

data class IrrigationAdvisory(
    val action: String, // e.g. "IRRIGATE", "WAIT_RAIN_EXPECTED", "MONITOR"
    val urgency: String, // "high", "medium", "low"
    val metrics: CropWaterBalanceMetrics,
    val rationale: String,
    val calculationMethod: String
)

data class SpraySuitability(
    val isSuitable: Boolean,
    val conditionLevel: String, // "optimal", "unfavorable"
    val recommendation: String,
    val windSuitable: Boolean,
    val rainProbabilitySuitable: Boolean,
    val calculationMethod: String
)
