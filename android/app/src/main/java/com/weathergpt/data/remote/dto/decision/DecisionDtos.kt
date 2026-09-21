package com.weathergpt.data.remote.dto.decision

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

@Serializable
data class DecisionLocationDto(
    @SerialName("name")
    val name: String? = null,
    @SerialName("latitude")
    val latitude: Double? = null,
    @SerialName("longitude")
    val longitude: Double? = null,
    @SerialName("district")
    val district: String? = null,
    @SerialName("state")
    val state: String? = null
)

@Serializable
data class DecisionRequestDto(
    @SerialName("question")
    val question: String,
    @SerialName("location")
    val location: DecisionLocationDto? = null,
    @SerialName("requested_time")
    val requestedTime: String? = null,
    @SerialName("domain")
    val domain: String? = "farmer",
    @SerialName("context")
    val context: Map<String, String>? = null
)

@Serializable
data class CandidateHourEvaluationDto(
    @SerialName("time_iso")
    val timeIso: String,
    @SerialName("wind_speed_kmh")
    val windSpeedKmh: Double,
    @SerialName("rain_probability_pct")
    val rainProbabilityPct: Double,
    @SerialName("precipitation_mm")
    val precipitationMm: Double,
    @SerialName("temperature_c")
    val temperatureC: Double? = null,
    @SerialName("passed")
    val passed: Boolean,
    @SerialName("failed_reasons")
    val failedReasons: List<String> = emptyList()
)

@Serializable
data class ActionWindowPeriodDto(
    @SerialName("window_id")
    val windowId: String,
    @SerialName("start_time_iso")
    val startTimeIso: String,
    @SerialName("end_time_iso")
    val endTimeIso: String,
    @SerialName("duration_hours")
    val durationHours: Int,
    @SerialName("score")
    val score: Double,
    @SerialName("avg_wind_speed_kmh")
    val avgWindSpeedKmh: Double,
    @SerialName("max_wind_speed_kmh")
    val maxWindSpeedKmh: Double,
    @SerialName("max_rain_probability_pct")
    val maxRainProbabilityPct: Double,
    @SerialName("total_rainfall_mm")
    val totalRainfallMm: Double,
    @SerialName("summary")
    val summary: String,
    @SerialName("recommended")
    val recommended: Boolean = false
)

@Serializable
data class ActionWindowDto(
    @SerialName("status")
    val status: String,
    @SerialName("best_window")
    val bestWindow: ActionWindowPeriodDto? = null,
    @SerialName("fallback_windows")
    val fallbackWindows: List<ActionWindowPeriodDto> = emptyList(),
    @SerialName("score")
    val score: Double? = null,
    @SerialName("constraints")
    val constraints: Map<String, JsonElement>? = null,
    @SerialName("confidence")
    val confidence: String? = "high",
    @SerialName("reason")
    val reason: String,
    @SerialName("evidence")
    val evidence: JsonObject? = null,
    @SerialName("hourly_evaluations")
    val hourlyEvaluations: List<CandidateHourEvaluationDto>? = null
)

@Serializable
data class LedgerRuleEvaluationDto(
    @SerialName("rule_name")
    val ruleName: String,
    @SerialName("threshold")
    val threshold: JsonElement? = null,
    @SerialName("observed_value")
    val observedValue: JsonElement? = null,
    @SerialName("unit")
    val unit: String = "",
    @SerialName("operator")
    val operator: String = "<=",
    @SerialName("satisfied")
    val satisfied: Boolean,
    @SerialName("rationale")
    val rationale: String = ""
)

@Serializable
data class EvidenceLedgerDto(
    @SerialName("decision_id")
    val decisionId: String,
    @SerialName("timestamp")
    val timestamp: String,
    @SerialName("question")
    val question: String,
    @SerialName("inputs")
    val inputs: JsonObject? = null,
    @SerialName("rules")
    val rules: List<LedgerRuleEvaluationDto> = emptyList(),
    @SerialName("calculations")
    val calculations: JsonObject? = null,
    @SerialName("sources")
    val sources: List<JsonObject>? = null,
    @SerialName("timestamps")
    val timestamps: Map<String, String>? = null,
    @SerialName("output")
    val output: JsonObject? = null
)

@Serializable
data class NirnayCardDto(
    @SerialName("question")
    val question: String,
    @SerialName("verdict")
    val verdict: String,
    @SerialName("severity")
    val severity: String,
    @SerialName("recommended_action")
    val recommendedAction: String,
    @SerialName("action_window")
    val actionWindow: ActionWindowDto,
    @SerialName("confidence")
    val confidence: String,
    @SerialName("uncertainty")
    val uncertainty: JsonObject? = null,
    @SerialName("why")
    val why: List<String> = emptyList(),
    @SerialName("impact")
    val impact: JsonObject? = null,
    @SerialName("alternatives")
    val alternatives: List<String> = emptyList(),
    @SerialName("evidence")
    val evidence: JsonObject? = null,
    @SerialName("ledger")
    val ledger: EvidenceLedgerDto? = null,
    @SerialName("explanation")
    val explanation: String? = null
)
