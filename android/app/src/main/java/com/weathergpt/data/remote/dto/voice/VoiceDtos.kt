package com.weathergpt.data.remote.dto.voice

import com.weathergpt.data.remote.dto.chat.ChatResponseDto
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class VoiceSttResponseDto(
    @SerialName("text") val text: String,
    @SerialName("language_code") val languageCode: String,
    @SerialName("provider") val provider: String,
    @SerialName("confidence") val confidence: Double? = null,
    @SerialName("detected_language") val detectedLanguage: String? = null
)

@Serializable
data class VoiceTtsRequestDto(
    @SerialName("text") val text: String,
    @SerialName("language_code") val languageCode: String = "hi",
    @SerialName("voice") val voice: String? = null,
    @SerialName("speaking_rate") val speakingRate: Double = 1.0
)

@Serializable
data class VoiceQueryResponseDto(
    @SerialName("transcript") val transcript: String,
    @SerialName("detected_language") val detectedLanguage: String,
    @SerialName("confidence") val confidence: Double? = null,
    @SerialName("final_response") val finalResponse: ChatResponseDto,
    @SerialName("audio_base64") val audioBase64: String? = null,
    @SerialName("audio_content_type") val audioContentType: String = "audio/mpeg"
)
