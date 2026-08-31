package com.weathergpt.core.network

import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.error.AppError
import com.weathergpt.core.error.ProblemDetails
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.ResponseBody
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/**
 * Standard configured Kotlinx Serialization [Json] parser.
 */
val networkJson: Json = Json {
    ignoreUnknownKeys = true
    isLenient = true
    coerceInputValues = true
    encodeDefaults = true
}

/**
 * Factory creating configured Retrofit instances.
 */
object RetrofitClientFactory {

    fun createRetrofit(
        okHttpClient: OkHttpClient = HttpClientFactory.createOkHttpClient(),
        baseUrl: String = AppConfig.apiBaseUrl,
        json: Json = networkJson
    ): Retrofit {
        val contentType = "application/json".toMediaType()
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
    }
}

/**
 * Utility mapping network and HTTP exceptions to domain [AppError]s.
 */
object ErrorMapper {

    /**
     * Maps any throwable to an [AppError].
     *
     * IMPORTANT: If [throwable] is a [CancellationException], it MUST NOT be caught or converted.
     * It is re-thrown immediately to preserve structured concurrency in Coroutine scopes.
     */
    fun mapThrowable(throwable: Throwable, json: Json = networkJson): AppError {
        if (throwable is CancellationException) {
            throw throwable
        }

        return when (throwable) {
            is UnknownHostException, is ConnectException -> {
                AppError.NetworkUnavailable(cause = throwable)
            }
            is SocketTimeoutException -> {
                AppError.Timeout(cause = throwable)
            }
            is HttpException -> {
                val statusCode = throwable.code()
                val response = throwable.response()
                val errorBody = response?.errorBody()
                val problemDetails = parseProblemDetails(errorBody, json)
                val requestId = problemDetails?.requestId ?: response?.headers()?.get("x-request-id")

                when {
                    statusCode == 429 -> {
                        val retryAfterHeader = response?.headers()?.get("Retry-After")?.toLongOrNull()
                        AppError.RateLimited(
                            statusCode = statusCode,
                            retryAfterSeconds = retryAfterHeader,
                            requestId = requestId,
                            cause = throwable
                        )
                    }
                    statusCode == 422 -> {
                        AppError.ValidationError(
                            statusCode = statusCode,
                            problemDetails = problemDetails,
                            requestId = requestId,
                            errors = problemDetails?.errors ?: emptyList(),
                            message = problemDetails?.detail ?: "Invalid request parameters.",
                            cause = throwable
                        )
                    }
                    statusCode >= 500 -> {
                        AppError.ServerUnavailable(
                            statusCode = statusCode,
                            requestId = requestId,
                            message = problemDetails?.detail ?: "The WeatherGPT server is currently unavailable (Status $statusCode).",
                            cause = throwable
                        )
                    }
                    else -> {
                        AppError.HttpError(
                            statusCode = statusCode,
                            problemDetails = problemDetails,
                            requestId = requestId,
                            message = problemDetails?.detail ?: "Request failed with HTTP status $statusCode.",
                            cause = throwable
                        )
                    }
                }
            }
            is kotlinx.serialization.SerializationException -> {
                AppError.SerializationError(
                    message = "Failed to process server response.",
                    cause = throwable
                )
            }
            is IOException -> {
                AppError.NetworkUnavailable(message = throwable.message ?: "Network error", cause = throwable)
            }
            else -> {
                AppError.Unknown(message = throwable.message ?: "An unexpected error occurred.", cause = throwable)
            }
        }
    }

    private fun parseProblemDetails(errorBody: ResponseBody?, json: Json): ProblemDetails? {
        if (errorBody == null) return null
        return try {
            val content = errorBody.string()
            if (content.isBlank()) return null
            json.decodeFromString<ProblemDetails>(content)
        } catch (_: Exception) {
            null
        }
    }
}
