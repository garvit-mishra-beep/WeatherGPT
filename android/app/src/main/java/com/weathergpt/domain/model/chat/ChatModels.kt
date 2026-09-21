package com.weathergpt.domain.model.chat

import kotlinx.serialization.json.JsonObject

enum class DomainBrain(val value: String) {
    AUTO("auto"),
    GENERAL("general"),
    FARMER("farmer"),
    RESEARCHER("researcher"),
    ANALYST("analyst");

    companion object {
        fun fromValue(value: String): DomainBrain =
            entries.firstOrNull { it.value.equals(value, ignoreCase = true) } ?: AUTO
    }
}

enum class ChatLanguage(val code: String) {
    ENGLISH("en"),
    HINDI("hi"),
    MARATHI("mr"),
    BENGALI("bn"),
    TAMIL("ta"),
    TELUGU("te"),
    GUJARATI("gu"),
    KANNADA("kn"),
    MALAYALAM("ml"),
    PUNJABI("pa");

    companion object {
        fun fromCode(code: String): ChatLanguage =
            entries.firstOrNull { it.code.equals(code, ignoreCase = true) } ?: ENGLISH
    }
}

data class ChatQuery(
    val sessionId: String,
    val query: String,
    val languagePreference: ChatLanguage = ChatLanguage.HINDI,
    val selectedBrain: DomainBrain = DomainBrain.AUTO,
    val userId: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null
)

data class AdvisoryRecommendation(
    val primaryAction: String,
    val urgency: String,
    val actions: List<String>
)

data class OfficialWarningCard(
    val source: String,
    val level: String, // Green, Yellow, Orange, Red (Immutable)
    val hazardType: String,
    val headline: String,
    val description: String,
    val validUntil: String
)

data class VisualizationCard(
    val type: String,
    val id: String,
    val title: String?,
    val chartType: String?,
    val spec: JsonObject?
)

data class EvidenceCitation(
    val authority: String,
    val dataset: String,
    val retrievedAt: String,
    val isOfficial: Boolean
)

data class ConfidenceAssessment(
    val evidenceLevel: String,
    val modelAgreement: String?,
    val dataFreshnessStatus: String,
    val notes: String?
)

data class ChatResponse(
    val responseId: String,
    val sessionId: String,
    val brain: DomainBrain,
    val language: String,
    val createdAt: String,
    val summary: String,
    val answer: String,
    val data: JsonObject?,
    val recommendation: AdvisoryRecommendation?,
    val alert: OfficialWarningCard?,
    val visualizations: List<VisualizationCard>,
    val sources: List<EvidenceCitation>,
    val confidence: ConfidenceAssessment?,
    val limitations: List<String>
)
