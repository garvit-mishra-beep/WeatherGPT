package com.weathergpt.data.remote.dto.system

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class HealthResponseDto(
    @SerialName("status")
    val status: String,
    @SerialName("app_name")
    val appName: String? = "WeatherGPT",
    @SerialName("environment")
    val environment: String,
    @SerialName("version")
    val version: String? = null,
    @SerialName("api_version")
    val apiVersion: String? = null,
    @SerialName("timestamp")
    val timestamp: String
)

@Serializable
data class DependencyStatusDto(
    @SerialName("status")
    val status: String,
    @SerialName("latency_ms")
    val latencyMs: Double = 0.0,
    @SerialName("detail")
    val detail: String = "",
    @SerialName("postgis")
    val postgis: String? = null
)

@Serializable
data class ReadyResponseDto(
    @SerialName("status")
    val status: String,
    @SerialName("ready")
    val ready: Boolean,
    @SerialName("dependencies")
    val dependencies: Map<String, DependencyStatusDto>? = null,
    @SerialName("probes")
    val probes: Map<String, Boolean>? = null,
    @SerialName("environment")
    val environment: String? = null,
    @SerialName("api_version")
    val apiVersion: String? = null,
    @SerialName("timestamp")
    val timestamp: String? = null
)

@Serializable
data class RootMetadataDto(
    @SerialName("title")
    val title: String? = null,
    @SerialName("api_version")
    val apiVersion: String? = null,
    @SerialName("environment")
    val environment: String? = null,
    @SerialName("timestamp")
    val timestamp: String? = null
)
