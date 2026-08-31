package com.weathergpt.core.config
 
import com.weathergpt.BuildConfig
 
/**
 * Supported execution environments for the Android client.
 */
enum class Environment {
    DEVELOPMENT,
    STAGING,
    PRODUCTION
}

/**
 * Target device/network profile for development debug builds.
 */
enum class DebugTarget {
    PHYSICAL_DEVICE,
    EMULATOR,
    CUSTOM
}

/**
 * Centralized application configuration.
 *
 * Distinct backend targets:
 * 1. Physical Android DEBUG (via ADB reverse): http://127.0.0.1:8000/
 * 2. Android Emulator DEBUG: http://10.0.2.2:8000/
 * 3. Staging HTTPS: https://staging-api.weathergpt.in/
 * 4. Production HTTPS: https://api.weathergpt.in/
 */
object AppConfig {

    const val PHYSICAL_DEBUG_URL: String = BuildConfig.DEBUG_PHYSICAL_URL
    const val EMULATOR_DEBUG_URL: String = BuildConfig.DEBUG_EMULATOR_URL
    const val STAGING_URL: String = BuildConfig.STAGING_URL
    const val PRODUCTION_URL: String = BuildConfig.PRODUCTION_URL

    private const val PREFS_NAME = "weathergpt_debug_config"
    private const val KEY_CUSTOM_URL = "custom_backend_url"

    private var runtimeBaseUrl: String? = null

    val isCustomBaseUrl: Boolean
        get() = runtimeBaseUrl != null

    val environment: Environment
        get() = when {
            !BuildConfig.DEBUG -> Environment.PRODUCTION
            runtimeBaseUrl == STAGING_URL -> Environment.STAGING
            else -> Environment.DEVELOPMENT
        }

    /**
     * Initialize AppConfig and load persisted debug URL if running in DEBUG mode.
     */
    fun init(context: android.content.Context?) {
        if (!BuildConfig.DEBUG || context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
            val savedUrl = prefs.getString(KEY_CUSTOM_URL, null)
            if (!savedUrl.isNullOrBlank()) {
                val validation = BackendUrlValidator.validateBackendUrl(savedUrl, isDebug = true)
                if (validation is ValidationResult.Success) {
                    runtimeBaseUrl = validation.normalizedUrl
                }
            }
        } catch (_: Throwable) {
            // Ignore SharedPreferences failure in unit test environments
        }
    }

    /**
     * Effective API Base URL ending with a trailing slash.
     */
    val apiBaseUrl: String
        get() {
            if (!BuildConfig.DEBUG) {
                return PRODUCTION_URL
            }
            val url = runtimeBaseUrl ?: BuildConfig.DEFAULT_API_BASE_URL
            return if (url.endsWith("/")) url else "$url/"
        }

    /**
     * Set target to Physical Device with ADB reverse (http://127.0.0.1:8000/).
     */
    fun usePhysicalDeviceDebug(context: android.content.Context? = null): ValidationResult {
        return setCustomBaseUrl(PHYSICAL_DEBUG_URL, context)
    }

    /**
     * Set target to Android Emulator (http://10.0.2.2:8000/).
     */
    fun useEmulatorDebug(context: android.content.Context? = null): ValidationResult {
        return setCustomBaseUrl(EMULATOR_DEBUG_URL, context)
    }

    /**
     * Set target to Staging HTTPS environment.
     */
    fun useStaging(context: android.content.Context? = null): ValidationResult {
        return setCustomBaseUrl(STAGING_URL, context)
    }

    /**
     * Set target to Production HTTPS environment.
     */
    fun useProduction(context: android.content.Context? = null): ValidationResult {
        return setCustomBaseUrl(PRODUCTION_URL, context)
    }

    /**
     * Override base URL at runtime (DEBUG only) with validation and local persistence.
     */
    fun setCustomBaseUrl(url: String?, context: android.content.Context? = null): ValidationResult {
        if (!BuildConfig.DEBUG) {
            runtimeBaseUrl = null
            return ValidationResult.Error("Runtime backend URL mutation is strictly forbidden in release builds")
        }

        if (url.isNullOrBlank()) {
            runtimeBaseUrl = null
            persistUrl(context, null)
            return ValidationResult.Success(apiBaseUrl)
        }

        return when (val result = BackendUrlValidator.validateBackendUrl(url, isDebug = true)) {
            is ValidationResult.Success -> {
                runtimeBaseUrl = result.normalizedUrl
                persistUrl(context, result.normalizedUrl)
                result
            }
            is ValidationResult.Error -> result
        }
    }

    /**
     * Reset configuration back to default debug endpoint (http://127.0.0.1:8000/).
     */
    fun resetToDefault(context: android.content.Context? = null) {
        if (!BuildConfig.DEBUG) return
        runtimeBaseUrl = null
        persistUrl(context, null)
    }

    private fun persistUrl(context: android.content.Context?, url: String?) {
        if (context == null || !BuildConfig.DEBUG) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_CUSTOM_URL, url).apply()
        } catch (_: Throwable) {
            // Non-fatal if SharedPreferences is unavailable
        }
    }

    /**
     * Network request timeouts in seconds.
     */
    const val REQUEST_TIMEOUT_SECONDS: Long = 30L
    const val CONNECT_TIMEOUT_SECONDS: Long = 15L

    /**
     * Whether verbose HTTP request/response logging is enabled.
     */
    val isLoggingEnabled: Boolean = BuildConfig.ENABLE_NETWORK_LOGGING
}
