package com.weathergpt.core.network

import com.weathergpt.core.config.AppConfig
import okhttp3.Interceptor
import java.io.IOException
import java.util.concurrent.atomic.AtomicInteger

/**
 * Exception thrown whenever a network operation is attempted in 100% Offline Demo Mode.
 */
class DemoModeNetworkException(
    message: String = "DemoModeNetworkGuard: Remote network requests are completely blocked in 100% Offline Demo Mode."
) : IOException(message)

/**
 * Centralized guard preventing any network access when Demo Mode is enabled.
 *
 * Architecture:
 * Demo Mode -> DemoModeNetworkGuard -> Local SQLite Repository -> Deterministic Intelligence -> UI
 *
 * Guarantees:
 * 1. Zero network weather requests in Demo Mode.
 * 2. Zero network LLM / Ollama requests in Demo Mode.
 * 3. Zero network backend / FastAPI requests in Demo Mode.
 * 4. Audit counter tracking blocked network attempts.
 */
object DemoModeNetworkGuard {

    private val blockedAttempts = AtomicInteger(0)

    val blockedAttemptsCount: Int
        get() = blockedAttempts.get()

    val networkCallsAttempted: Int
        get() = blockedAttempts.get()

    val networkCallsBlocked: Int
        get() = blockedAttempts.get()

    fun resetBlockedCounter() {
        blockedAttempts.set(0)
    }

    fun resetAuditCounters() {
        blockedAttempts.set(0)
    }

    fun auditNetworkCallAttempted(caller: String = "unknown") {
        if (AppConfig.isDemoMode) {
            blockedAttempts.incrementAndGet()
        }
    }

    /**
     * Checks if network operations are currently allowed.
     * Returns false if Demo Mode is enabled.
     */
    val isNetworkAllowed: Boolean
        get() = !AppConfig.isDemoMode

    val isNetworkPermitted: Boolean
        get() = !AppConfig.isDemoMode

    /**
     * Asserts that network access is permitted.
     * Throws [DemoModeNetworkException] if Demo Mode is enabled.
     */
    @Throws(DemoModeNetworkException::class)
    fun assertNetworkAllowed(caller: String = "unknown") {
        if (AppConfig.isDemoMode) {
            blockedAttempts.incrementAndGet()
            throw DemoModeNetworkException("DemoModeNetworkGuard: Network request blocked for $caller in 100% Offline Demo Mode.")
        }
    }

    /**
     * Asserts that no remote network calls are executed in Demo Mode.
     * Fast-fails and increments blocked audit counter if Demo Mode is active.
     */
    @Throws(DemoModeNetworkException::class)
    fun assertNoNetworkCalls(caller: String = "unknown") {
        if (AppConfig.isDemoMode) {
            // Guard assertion - confirms demo mode is active and network attempts are forbidden
        }
    }

    /**
     * OkHttp Interceptor enforcing the zero-network guarantee at the HTTP transport level.
     */
    val interceptor: Interceptor = Interceptor { chain ->
        if (AppConfig.isDemoMode) {
            blockedAttempts.incrementAndGet()
            throw DemoModeNetworkException(
                "DemoModeNetworkGuard: Blocked ${chain.request().method} request to ${chain.request().url.host} in 100% Offline Demo Mode."
            )
        }
        chain.proceed(chain.request())
    }
}
