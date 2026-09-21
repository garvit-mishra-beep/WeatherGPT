package com.weathergpt.domain.model.decision

enum class DecisionVerdict(val raw: String) {
    GO("GO"),
    NO_GO("NO_GO"),
    POSTPONE("POSTPONE"),
    PROCEED_WITH_CAUTION("PROCEED_WITH_CAUTION"),
    MONITOR("MONITOR"),
    INSUFFICIENT_DATA("INSUFFICIENT_DATA");

    companion object {
        fun fromRaw(value: String): DecisionVerdict =
            entries.firstOrNull { it.raw.equals(value, ignoreCase = true) } ?: POSTPONE
    }
}

enum class DecisionSeverity(val raw: String) {
    LOW("low"),
    MODERATE("moderate"),
    HIGH("high"),
    CRITICAL("critical");

    companion object {
        fun fromRaw(value: String): DecisionSeverity =
            entries.firstOrNull { it.raw.equals(value, ignoreCase = true) } ?: MODERATE
    }
}

enum class DecisionConfidence(val raw: String) {
    HIGH("high"),
    MEDIUM("medium"),
    LOW("low"),
    INSUFFICIENT_DATA("insufficient_data");

    companion object {
        fun fromRaw(value: String): DecisionConfidence =
            entries.firstOrNull { it.raw.equals(value, ignoreCase = true) } ?: MEDIUM
    }
}

data class CandidateHourEvaluation(
    val timeIso: String,
    val windSpeedKmh: Double,
    val rainProbabilityPct: Double,
    val precipitationMm: Double,
    val temperatureC: Double?,
    val passed: Boolean,
    val failedReasons: List<String>
)

data class ActionWindowPeriod(
    val windowId: String,
    val startTimeIso: String,
    val endTimeIso: String,
    val durationHours: Int,
    val score: Double,
    val avgWindSpeedKmh: Double,
    val maxWindSpeedKmh: Double,
    val maxRainProbabilityPct: Double,
    val totalRainfallMm: Double,
    val summary: String,
    val recommended: Boolean
)

data class ActionWindow(
    val status: String, // "available" or "unavailable"
    val isAvailable: Boolean,
    val bestWindow: ActionWindowPeriod?,
    val fallbackWindows: List<ActionWindowPeriod>,
    val score: Double?,
    val constraints: Map<String, String>,
    val confidence: DecisionConfidence,
    val reason: String,
    val hourlyEvaluations: List<CandidateHourEvaluation>?
)

data class LedgerRuleEvaluation(
    val ruleName: String,
    val threshold: String,
    val observedValue: String,
    val unit: String,
    val operator: String,
    val satisfied: Boolean,
    val rationale: String
)

data class EvidenceLedger(
    val decisionId: String,
    val timestamp: String,
    val question: String,
    val rules: List<LedgerRuleEvaluation>,
    val inputs: Map<String, String>,
    val sources: List<String>
)

enum class ExposureState(val raw: String) {
    INSIDE("INSIDE"),
    BUFFER("BUFFER"),
    OUTSIDE("OUTSIDE"),
    UNKNOWN("UNKNOWN");

    companion object {
        fun fromRaw(value: String?): ExposureState =
            entries.firstOrNull { it.raw.equals(value?.trim(), ignoreCase = true) } ?: UNKNOWN
    }
}

data class AlertImpactInfo(
    val alertId: String?,
    val hazard: String?,
    val issuingOffice: String?, // DYNAMIC authority returned by backend (e.g. "NDMA_SACHET", "NDMA")
    val isOfficial: Boolean,
    val alertSeverity: String?, // "Red", "Orange", "Yellow", "Green"
    val affectedAreaStatus: ExposureState, // INSIDE, BUFFER, OUTSIDE, UNKNOWN
    val affectedAreaName: String?,
    val exposureStatus: String, // "AVAILABLE", "PARTIAL", "UNAVAILABLE"
    val exposureSummary: String?,
    val exposedAreaSqkm: Double?,
    val potentialImpact: String?,
    val compositeImpactScore: Double?,
    val riskCategory: String?
)

data class DecisionUncertainty(
    val gfsConfidence: String,
    val wrfStatus: String,
    val uncertaintyNote: String,
    val leadTimeHours: Double?,
    val exposureDataAvailable: Boolean = true
)

data class NirnayCard(
    val question: String,
    val verdict: DecisionVerdict,
    val severity: DecisionSeverity,
    val recommendedAction: String,
    val actionWindow: ActionWindow,
    val confidence: DecisionConfidence,
    val uncertainty: DecisionUncertainty,
    val why: List<String>,
    val primaryRisk: String?,
    val lossPotential: String?,
    val alternatives: List<String>,
    val evidenceMetrics: Map<String, String>,
    val ledger: EvidenceLedger?,
    val alertImpact: AlertImpactInfo? = null,
    val explanation: String? = null,
    val sourceStatus: String = "LIVE", // LIVE, CACHED, FALLBACK, HISTORICAL, UNAVAILABLE
    val lastVerifiedAt: String? = null,
    val dataAge: String? = null
)

