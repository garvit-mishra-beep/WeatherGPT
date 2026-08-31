package com.weathergpt.core.error

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Standard RFC 7807 Problem Details representation emitted by the WeatherGPT backend.
 */
@Serializable
data class ProblemDetails(
    val type: String? = null,
    val title: String? = null,
    val status: Int? = null,
    val detail: String? = null,
    val instance: String? = null,
    @SerialName("request_id")
    val requestId: String? = null,
    val errors: List<String>? = null
)
