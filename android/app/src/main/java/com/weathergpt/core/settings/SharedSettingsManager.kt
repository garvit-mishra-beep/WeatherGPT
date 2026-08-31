package com.weathergpt.core.settings

import android.content.Context
import com.weathergpt.domain.model.chat.ChatLanguage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class AppLanguage(val code: String, val englishName: String, val nativeName: String) {
    ENGLISH("en", "English", "English"),
    HINDI("hi", "Hindi", "हिन्दी");

    fun toChatLanguage(): ChatLanguage = when (this) {
        ENGLISH -> ChatLanguage.ENGLISH
        HINDI -> ChatLanguage.HINDI
    }

    companion object {
        fun fromCode(code: String): AppLanguage = entries.find { it.code.equals(code, ignoreCase = true) } ?: ENGLISH
    }
}

enum class UnitSystem(val code: String, val displayNameEn: String, val displayNameHi: String) {
    METRIC("metric", "Metric (°C, km/h)", "मीट्रिक (°C, किमी/घंटा)"),
    IMPERIAL("imperial", "Imperial (°F, mph)", "इंपीरियल (°F, मील/घंटा)");

    companion object {
        fun fromCode(code: String): UnitSystem = entries.find { it.code.equals(code, ignoreCase = true) } ?: METRIC
    }
}

/**
 * Centralized Settings and Preferences Manager with SharedPreferences persistence.
 */
class SharedSettingsManager(
    private val context: Context? = null
) {
    private val _appLanguage = MutableStateFlow(AppLanguage.HINDI)
    val appLanguage: StateFlow<AppLanguage> = _appLanguage.asStateFlow()

    private val _unitSystem = MutableStateFlow(UnitSystem.METRIC)
    val unitSystem: StateFlow<UnitSystem> = _unitSystem.asStateFlow()

    private val _notificationsEnabled = MutableStateFlow(true)
    val notificationsEnabled: StateFlow<Boolean> = _notificationsEnabled.asStateFlow()

    init {
        loadSettings()
    }

    fun setLanguage(language: AppLanguage) {
        _appLanguage.value = language
        persistLanguage(language)
    }

    fun setUnitSystem(units: UnitSystem) {
        _unitSystem.value = units
        persistUnits(units)
    }

    fun setNotificationsEnabled(enabled: Boolean) {
        _notificationsEnabled.value = enabled
        persistNotifications(enabled)
    }

    private fun loadSettings() {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val langCode = prefs.getString(KEY_LANGUAGE, AppLanguage.HINDI.code) ?: AppLanguage.HINDI.code
            _appLanguage.value = AppLanguage.fromCode(langCode)

            val unitCode = prefs.getString(KEY_UNITS, UnitSystem.METRIC.code) ?: UnitSystem.METRIC.code
            _unitSystem.value = UnitSystem.fromCode(unitCode)

            _notificationsEnabled.value = prefs.getBoolean(KEY_NOTIFICATIONS, true)
        } catch (_: Throwable) {
            // Safe fallback
        }
    }

    private fun persistLanguage(language: AppLanguage) {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_LANGUAGE, language.code).apply()
        } catch (_: Throwable) {}
    }

    private fun persistUnits(units: UnitSystem) {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_UNITS, units.code).apply()
        } catch (_: Throwable) {}
    }

    private fun persistNotifications(enabled: Boolean) {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putBoolean(KEY_NOTIFICATIONS, enabled).apply()
        } catch (_: Throwable) {}
    }

    companion object {
        private const val PREFS_NAME = "weathergpt_settings_prefs"
        private const val KEY_LANGUAGE = "setting_app_language"
        private const val KEY_UNITS = "setting_unit_system"
        private const val KEY_NOTIFICATIONS = "setting_notifications_enabled"
    }
}
