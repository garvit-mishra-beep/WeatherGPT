package com.weathergpt.data.remote.dto.proactive

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Request payload for registering or refreshing a client push device token with the backend.
 *
 * Matches backend `RegisterDeviceRequest` in `app/proactive/models.py`.
 */
@Serializable
data class RegisterDeviceRequestDto(
    @SerialName("user_id")
    val userId: String,
    @SerialName("device_id")
    val deviceId: String,
    @SerialName("fcm_token")
    val fcmToken: String,
    @SerialName("platform")
    val platform: String = "android"
)

/**
 * Response payload confirming device token registration.
 *
 * Matches backend `RegisterDeviceResponse` in `app/proactive/models.py`.
 */
@Serializable
data class RegisterDeviceResponseDto(
    @SerialName("device_id")
    val deviceId: String,
    @SerialName("user_id")
    val userId: String,
    @SerialName("registered")
    val registered: Boolean,
    @SerialName("message")
    val message: String = ""
)
