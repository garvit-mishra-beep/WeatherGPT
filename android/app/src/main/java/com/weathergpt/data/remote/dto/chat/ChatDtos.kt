package com.weathergpt.data.remote.dto.chat

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class GPSLocationDto(
    @SerialName("latitude")
    val latitude: Double,
    @SerialName("longitude")
    val longitude: Double,
    @SerialName("accuracy_m")
    val accuracyM: Double? = null
)

@Serializable
data class DeviceContextDto(
    @SerialName("gps_location")
    val gpsLocation: GPSLocationDto? = null,
    @SerialName("client_timestamp")
    val clientTimestamp: String? = null,
    @SerialName("platform")
    val platform: String = "android",
    @SerialName("app_version")
    val appVersion: String = "1.0.0"
)

@Serializable
data class ChatRequestDto(
    @SerialName("session_id")
    val sessionId: String,
    @SerialName("user_id")
    val userId: String? = null,
    @SerialName("query")
    val query: String,
    @SerialName("language_preference")
    val languagePreference: String? = "hi",
    @SerialName("selected_brain")
    val selectedBrain: String = "auto",
    @SerialName("device_context")
    val deviceContext: DeviceContextDto? = null,
    @SerialName("requested_output_formats")
    val requestedOutputFormats: List<String> = listOf("text", "weather_card")
)

@Serializable
data class RecommendationDto(
    @SerialName("primary_action")
    val primaryAction: String,
    @SerialName("urgency")
    val urgency: String = "medium",
    @SerialName("actions")
    val actions: List<String> = emptyList()
)

@Serializable
data class WeatherAlertDto(
    @SerialName("source")
    val source: String = "IMD",
    @SerialName("level")
    val level: String, // "Green", "Yellow", "Orange", "Red"
    @SerialName("hazard_type")
    val hazardType: String,
    @SerialName("headline")
    val headline: String,
    @SerialName("description")
    val description: String,
    @SerialName("valid_until")
    val validUntil: String
)

@Serializable
data class VisualizationSpecDto(
    @SerialName("type")
    val type: String, // "weather_card", "chart", "map", "table", "dashboard"
    @SerialName("id")
    val id: String,
    @SerialName("title")
    val title: String? = null,
    @SerialName("chart_type")
    val chartType: String? = null,
    @SerialName("spec")
    val spec: JsonObject? = null
)

@Serializable
data class SourceCitationDto(
    @SerialName("authority")
    val authority: String,
    @SerialName("dataset")
    val dataset: String,
    @SerialName("retrieved_at")
    val retrievedAt: String,
    @SerialName("is_official")
    val isOfficial: Boolean = false
)

@Serializable
data class ConfidenceInfoDto(
    @SerialName("evidence_level")
    val evidenceLevel: String = "high",
    @SerialName("model_agreement")
    val modelAgreement: String? = null,
    @SerialName("data_freshness_status")
    val dataFreshnessStatus: String = "fresh",
    @SerialName("notes")
    val notes: String? = null
)

@Serializable
data class ChatResponseDto(
    @SerialName("response_id")
    val responseId: String,
    @SerialName("session_id")
    val sessionId: String,
    @SerialName("brain")
    val brain: String,
    @SerialName("language")
    val language: String = "hi",
    @SerialName("created_at")
    val createdAt: String,
    @SerialName("summary")
    val summary: String,
    @SerialName("answer")
    val answer: String,
    @SerialName("data")
    val data: JsonObject? = null,
    @SerialName("recommendation")
    val recommendation: RecommendationDto? = null,
    @SerialName("alert")
    val alert: WeatherAlertDto? = null,
    @SerialName("visualizations")
    val visualizations: List<VisualizationSpecDto> = emptyList(),
    @SerialName("sources")
    val sources: List<SourceCitationDto> = emptyList(),
    @SerialName("confidence")
    val confidence: ConfidenceInfoDto? = null,
    @SerialName("limitations")
    val limitations: List<String> = emptyList()
)
