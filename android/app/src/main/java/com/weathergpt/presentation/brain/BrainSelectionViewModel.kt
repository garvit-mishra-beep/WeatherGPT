package com.weathergpt.presentation.brain

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.presentation.components.IntelligenceBrain
import kotlinx.coroutines.flow.StateFlow

class BrainSelectionViewModel(
    private val brainManager: SharedBrainManager
) : ViewModel() {

    val selectedBrain: StateFlow<IntelligenceBrain> = brainManager.selectedBrain

    fun selectBrain(brain: IntelligenceBrain) {
        brainManager.selectBrain(brain)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                BrainSelectionViewModel(
                    brainManager = app.container.sharedBrainManager
                )
            }
        }
    }
}
