package com.weathergpt.domain.model

/**
 * Domain model representing backend system health status.
 */
data class HealthStatus(
    val status: String,
    val appName: String = "WeatherGPT",
    val environment: String,
    val version: String = "v1",
    val apiVersion: String = "v1",
    val timestamp: String,
    val isHealthy: Boolean = status.equals("healthy", ignoreCase = true) || status.equals("ok", ignoreCase = true)
)

/**
 * Domain model representing backend system readiness status.
 */
data class ReadinessStatus(
    val status: String,
    val isReady: Boolean,
    val environment: String,
    val apiVersion: String,
    val dependencies: Map<String, String> = emptyMap(),
    val probes: Map<String, Boolean> = emptyMap(),
    val timestamp: String
)
