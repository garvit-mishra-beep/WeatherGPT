package com.weathergpt.core.brain

import android.content.Context
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.presentation.components.IntelligenceBrain
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Centralized Shared Brain State Manager for WeatherGPT.
 *
 * Responsibilities:
 * 1. Maintains single source of truth for the active [IntelligenceBrain] across the app.
 * 2. Persists selected Brain in [SharedPreferences] across app restarts.
 * 3. Bridges presentation [IntelligenceBrain] to domain [DomainBrain].
 * 4. Safely falls back to [IntelligenceBrain.AUTO] on invalid or missing state.
 */
class SharedBrainManager(
    private val context: Context? = null
) {
    private val _selectedBrain = MutableStateFlow(IntelligenceBrain.AUTO)
    val selectedBrain: StateFlow<IntelligenceBrain> = _selectedBrain.asStateFlow()

    init {
        loadPersistedBrain()
    }

    fun selectBrain(brain: IntelligenceBrain) {
        _selectedBrain.value = brain
        persistBrain(brain)
    }

    fun getDomainBrain(): DomainBrain {
        return when (_selectedBrain.value) {
            IntelligenceBrain.AUTO -> DomainBrain.AUTO
            IntelligenceBrain.GENERAL -> DomainBrain.GENERAL
            IntelligenceBrain.FARMER -> DomainBrain.FARMER
            IntelligenceBrain.RESEARCHER -> DomainBrain.RESEARCHER
            IntelligenceBrain.ANALYST -> DomainBrain.ANALYST
        }
    }

    private fun loadPersistedBrain() {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val savedBrainId = prefs.getString(KEY_SELECTED_BRAIN, null)
            if (!savedBrainId.isNullOrBlank()) {
                val matchedBrain = IntelligenceBrain.entries.find { it.id.equals(savedBrainId, ignoreCase = true) }
                _selectedBrain.value = matchedBrain ?: IntelligenceBrain.AUTO
            }
        } catch (_: Throwable) {
            // Non-fatal in test or isolated environments
        }
    }

    private fun persistBrain(brain: IntelligenceBrain) {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_SELECTED_BRAIN, brain.id).apply()
        } catch (_: Throwable) {
            // Non-fatal if SharedPreferences is unavailable
        }
    }

    companion object {
        private const val PREFS_NAME = "weathergpt_brain_prefs"
        private const val KEY_SELECTED_BRAIN = "selected_intelligence_brain"
    }
}
