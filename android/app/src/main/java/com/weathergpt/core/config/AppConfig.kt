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

    const val DEMO_LAN_GATEWAY: String = "192.168.137.1"
    const val DEMO_HOTSPOT_BACKEND_URL: String = "http://$DEMO_LAN_GATEWAY:8000/"
    const val DEMO_HOTSPOT_OLLAMA_URL: String = "http://$DEMO_LAN_GATEWAY:11434/"

    private const val PREFS_NAME = "weathergpt_debug_config"
    private const val KEY_CUSTOM_URL = "custom_backend_url"
    private const val KEY_DEMO_MODE = "showcase_demo_mode"
    private const val KEY_OLLAMA_URL = "custom_ollama_url"
    private const val KEY_OLLAMA_MODEL = "custom_ollama_model"

    private var runtimeBaseUrl: String? = null
    private var runtimeDemoMode: Boolean? = null
    private var runtimeOllamaUrl: String? = null
    private var runtimeOllamaModel: String? = null

    /**
     * Single source of truth for full offline Showcase Demo Mode.
     */
    var isDemoMode: Boolean
        get() = runtimeDemoMode ?: BuildConfig.DEMO_MODE
        set(value) {
            runtimeDemoMode = value
        }

    val ollamaBaseUrl: String
        get() {
            val url = runtimeOllamaUrl ?: if (isDemoMode) DEMO_HOTSPOT_OLLAMA_URL else BuildConfig.DEFAULT_OLLAMA_URL
            return if (url.endsWith("/")) url else "$url/"
        }

    val ollamaModel: String
        get() = runtimeOllamaModel ?: BuildConfig.DEFAULT_OLLAMA_MODEL

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
            } else if (isDemoMode) {
                runtimeBaseUrl = DEMO_HOTSPOT_BACKEND_URL
            }
            if (prefs.contains(KEY_DEMO_MODE)) {
                runtimeDemoMode = prefs.getBoolean(KEY_DEMO_MODE, BuildConfig.DEMO_MODE)
            }
            val savedOllamaUrl = prefs.getString(KEY_OLLAMA_URL, null)
            if (!savedOllamaUrl.isNullOrBlank()) {
                runtimeOllamaUrl = savedOllamaUrl
            }
            val savedOllamaModel = prefs.getString(KEY_OLLAMA_MODEL, null)
            if (!savedOllamaModel.isNullOrBlank()) {
                runtimeOllamaModel = savedOllamaModel
            }
        } catch (_: Throwable) {
            // Ignore SharedPreferences failure in unit test environments
        }
    }

    fun setDemoMode(enabled: Boolean, context: android.content.Context? = null) {
        runtimeDemoMode = enabled
        if (context != null) {
            try {
                val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
                prefs.edit().putBoolean(KEY_DEMO_MODE, enabled).apply()
            } catch (_: Throwable) {
                // Non-fatal
            }
        }
    }

    fun setCustomOllamaUrl(url: String?, context: android.content.Context? = null) {
        runtimeOllamaUrl = url?.takeIf { it.isNotBlank() }
        if (context != null) {
            try {
                val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
                prefs.edit().putString(KEY_OLLAMA_URL, runtimeOllamaUrl).apply()
            } catch (_: Throwable) {
                // Non-fatal
            }
        }
    }

    fun setCustomOllamaModel(model: String?, context: android.content.Context? = null) {
        runtimeOllamaModel = model?.takeIf { it.isNotBlank() }
        if (context != null) {
            try {
                val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
                prefs.edit().putString(KEY_OLLAMA_MODEL, runtimeOllamaModel).apply()
            } catch (_: Throwable) {
                // Non-fatal
            }
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
     * Set target to Laptop 1 Hotspot Gateway for offline demo (http://192.168.137.1:8000/).
     */
    fun useDemoHotspot(context: android.content.Context? = null): ValidationResult {
        setCustomOllamaUrl(DEMO_HOTSPOT_OLLAMA_URL, context)
        return setCustomBaseUrl(DEMO_HOTSPOT_BACKEND_URL, context)
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
        runtimeDemoMode = null
        runtimeOllamaUrl = null
        runtimeOllamaModel = null
        persistUrl(context, null)
        if (context != null) {
            try {
                val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
                prefs.edit().remove(KEY_DEMO_MODE).remove(KEY_OLLAMA_URL).remove(KEY_OLLAMA_MODEL).apply()
            } catch (_: Throwable) {
                // Non-fatal
            }
        }
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
