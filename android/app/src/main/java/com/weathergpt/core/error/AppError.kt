package com.weathergpt.core.error

/**
 * Domain-grounded sealed error hierarchy for the WeatherGPT Android application.
 */
sealed class AppError(
    open val message: String,
    open val cause: Throwable? = null
) {
    /**
     * Device has no internet connection or hostname resolution failed.
     */
    data class NetworkUnavailable(
        override val message: String = "Network connection is unavailable. Please check your internet connection.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * Request exceeded connection, read, or write timeout.
     */
    data class Timeout(
        override val message: String = "The network request timed out. Please try again.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * Rate limit exceeded (HTTP 429).
     */
    data class RateLimited(
        val statusCode: Int = 429,
        val retryAfterSeconds: Long? = null,
        val requestId: String? = null,
        override val message: String = if (retryAfterSeconds != null) {
            "Too many requests. Please wait $retryAfterSeconds seconds before retrying."
        } else {
            "Rate limit exceeded. Please try again in a few moments."
        },
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * Structured HTTP error with RFC 7807 problem details from backend (e.g. 400, 404).
     */
    data class HttpError(
        val statusCode: Int,
        val problemDetails: ProblemDetails? = null,
        val requestId: String? = problemDetails?.requestId,
        override val message: String = problemDetails?.detail ?: "Request failed with HTTP status $statusCode.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * Schema validation error (HTTP 422) with detailed field validation messages.
     */
    data class ValidationError(
        val statusCode: Int = 422,
        val problemDetails: ProblemDetails? = null,
        val requestId: String? = problemDetails?.requestId,
        val errors: List<String> = problemDetails?.errors ?: emptyList(),
        override val message: String = problemDetails?.detail ?: "Invalid request parameters.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * JSON payload serialization or deserialization failure.
     */
    data class SerializationError(
        override val message: String = "Unable to process server response.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * 5xx Server Error or server gateway failure (e.g. 500, 502, 503, 504).
     */
    data class ServerUnavailable(
        val statusCode: Int,
        val requestId: String? = null,
        override val message: String = "The WeatherGPT server is currently unavailable (Status $statusCode). Please try again later.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    /**
     * Catch-all unexpected runtime error.
     */
    data class Unknown(
        override val message: String = "An unexpected error occurred. Please try again.",
        override val cause: Throwable? = null
    ) : AppError(message, cause)

    val isRetryable: Boolean
        get() = when (this) {
            is NetworkUnavailable -> true
            is Timeout -> true
            is RateLimited -> true
            is ServerUnavailable -> true
            is HttpError -> statusCode in 500..599
            is ValidationError -> false
            is SerializationError -> false
            is Unknown -> true
        }

    val errorCode: String
        get() = when (this) {
            is NetworkUnavailable -> "ERR_OFFLINE_NO_INTERNET"
            is Timeout -> "ERR_NETWORK_TIMEOUT"
            is RateLimited -> "ERR_RATE_LIMITED_429"
            is ServerUnavailable -> "ERR_SERVER_UNAVAILABLE_$statusCode"
            is HttpError -> problemDetails?.title ?: "ERR_HTTP_$statusCode"
            is ValidationError -> "ERR_VALIDATION_FAILED_422"
            is SerializationError -> "ERR_SERIALIZATION_FAILED"
            is Unknown -> "ERR_UNKNOWN_EXCEPTION"
        }

    val errorRequestId: String?
        get() = when (this) {
            is RateLimited -> requestId
            is HttpError -> requestId
            is ValidationError -> requestId
            is ServerUnavailable -> requestId
            else -> null
        }
}
