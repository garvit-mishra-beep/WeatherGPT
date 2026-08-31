package com.weathergpt.core.network

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import retrofit2.HttpException
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/**
 * Bounded exponential backoff retry policy for idempotent network operations.
 */
object RetryPolicy {

    const val DEFAULT_MAX_RETRIES: Int = 2
    const val DEFAULT_INITIAL_DELAY_MS: Long = 400L
    const val DEFAULT_MAX_DELAY_MS: Long = 2000L
    const val DEFAULT_BACKOFF_FACTOR: Double = 2.0

    /**
     * Executes a suspending [block] with bounded retries for transient failures.
     *
     * IMPORTANT:
     * - Only calls with [isIdempotent] = true (typically GET requests) will be retried.
     * - POST requests or mutating operations MUST NOT be automatically retried.
     * - [CancellationException] is NEVER caught and will rethrow immediately.
     */
    suspend fun <T> executeWithRetry(
        maxRetries: Int = DEFAULT_MAX_RETRIES,
        initialDelayMs: Long = DEFAULT_INITIAL_DELAY_MS,
        maxDelayMs: Long = DEFAULT_MAX_DELAY_MS,
        backoffFactor: Double = DEFAULT_BACKOFF_FACTOR,
        isIdempotent: Boolean = false,
        block: suspend () -> T
    ): T {
        var currentDelay = initialDelayMs
        var attempts = 0

        while (true) {
            try {
                return block()
            } catch (cancellation: CancellationException) {
                // Never swallow cancellation in coroutine scopes
                throw cancellation
            } catch (throwable: Throwable) {
                attempts++
                val isTransient = isTransientFailure(throwable)

                if (!isIdempotent || !isTransient || attempts > maxRetries) {
                    throw throwable
                }

                delay(currentDelay)
                currentDelay = (currentDelay * backoffFactor).toLong().coerceAtMost(maxDelayMs)
            }
        }
    }

    private fun isTransientFailure(throwable: Throwable): Boolean {
        return when (throwable) {
            is SocketTimeoutException, is ConnectException, is UnknownHostException -> true
            is HttpException -> {
                val code = throwable.code()
                code == 502 || code == 503 || code == 504 || code == 408
            }
            is IOException -> true
            else -> false
        }
    }
}
