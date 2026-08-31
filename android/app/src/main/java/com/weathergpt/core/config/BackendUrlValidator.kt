package com.weathergpt.core.config

import com.weathergpt.BuildConfig
import java.net.URI

/**
 * Result of URL validation.
 */
sealed interface ValidationResult {
    data class Success(val normalizedUrl: String) : ValidationResult
    data class Error(val message: String) : ValidationResult
}

/**
 * Validator and normalizer for WeatherGPT backend endpoints.
 *
 * Enforces strict environment boundaries:
 * 1. DEBUG mode allows local HTTP (localhost, 127.0.0.1, 10.0.2.2, LAN IPs) and HTTPS.
 * 2. RELEASE mode strictly forbids local HTTP, private LAN IPs, and arbitrary endpoint mutation.
 */
object BackendUrlValidator {

    private val PRIVATE_IP_PATTERN = Regex(
        "^((10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})|" +
        "(172\\.(1[6-9]|2[0-9]|3[0-1])\\.\\d{1,3}\\.\\d{1,3})|" +
        "(192\\.168\\.\\d{1,3}\\.\\d{1,3})|" +
        "(127\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})|" +
        "(localhost)|(10\\.0\\.2\\.2))$"
    )

    /**
     * Validates and normalizes raw URL string.
     */
    fun validateBackendUrl(rawUrl: String?, isDebug: Boolean = BuildConfig.DEBUG): ValidationResult {
        if (rawUrl.isNullOrBlank()) {
            return ValidationResult.Error("Backend URL cannot be empty")
        }

        val trimmed = rawUrl.trim()
        if (!trimmed.startsWith("http://", ignoreCase = true) && !trimmed.startsWith("https://", ignoreCase = true)) {
            return ValidationResult.Error("Missing scheme: must start with http:// or https://")
        }

        val uri = try {
            URI(trimmed)
        } catch (e: Exception) {
            return ValidationResult.Error("Malformed URL syntax: ${e.message}")
        }

        val scheme = uri.scheme?.lowercase()
        if (scheme == null || (scheme != "http" && scheme != "https")) {
            return ValidationResult.Error("URL scheme must be http:// or https://")
        }

        val host = uri.host
        if (host.isNullOrBlank()) {
            return ValidationResult.Error("URL host cannot be empty")
        }

        val port = uri.port
        if (port != -1 && (port < 1 || port > 65535)) {
            return ValidationResult.Error("Port must be between 1 and 65535")
        }

        // Release security validation: Release MUST NOT use local HTTP, localhost, 127.0.0.1, or LAN IPs
        if (!isDebug) {
            if (scheme != "https") {
                return ValidationResult.Error("Release builds strictly require HTTPS")
            }
            if (PRIVATE_IP_PATTERN.matches(host.lowercase())) {
                return ValidationResult.Error("Local/private IP addresses are forbidden in release builds")
            }
            val expectedProd = AppConfig.PRODUCTION_URL.removeSuffix("/")
            val candidateNoSlash = trimmed.removeSuffix("/")
            if (candidateNoSlash != expectedProd) {
                return ValidationResult.Error("Arbitrary backend endpoints are forbidden in release builds")
            }
        }

        val normalized = if (trimmed.endsWith("/")) trimmed else "$trimmed/"
        return ValidationResult.Success(normalized)
    }

    /**
     * Parses QR code payload string into a validated backend URL.
     */
    fun parseQrCodePayload(payload: String?, isDebug: Boolean = BuildConfig.DEBUG): ValidationResult {
        if (payload.isNullOrBlank()) {
            return ValidationResult.Error("QR code payload is empty")
        }
        return validateBackendUrl(payload, isDebug)
    }
}
