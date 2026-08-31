package com.weathergpt.presentation.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.presentation.components.IntelligenceBrain
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.util.UUID

sealed class ChatMessage {
    data class User(
        val id: String = UUID.randomUUID().toString(),
        val text: String,
        val timestamp: String = "Just now"
    ) : ChatMessage()

    data class Assistant(
        val id: String = UUID.randomUUID().toString(),
        val response: ChatResponse,
        val timestamp: String = "Just now"
    ) : ChatMessage()
}

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val inputText: String = "",
    val selectedBrain: DomainBrain = DomainBrain.AUTO,
    val language: ChatLanguage = ChatLanguage.ENGLISH,
    val sessionId: String = UUID.randomUUID().toString(),
    val isSending: Boolean = false,
    val lastFailedQuery: String? = null
)

class ChatViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager,
    private val brainManager: SharedBrainManager = SharedBrainManager()
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        ChatUiState(selectedBrain = brainManager.getDomainBrain())
    )
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private val _chatState = MutableStateFlow<ResultState<ChatResponse>>(ResultState.Idle)
    val chatState: StateFlow<ResultState<ChatResponse>> = _chatState.asStateFlow()

    init {
        viewModelScope.launch {
            brainManager.selectedBrain.collectLatest {
                _uiState.value = _uiState.value.copy(selectedBrain = brainManager.getDomainBrain())
            }
        }
    }

    fun setInputText(text: String) {
        _uiState.value = _uiState.value.copy(inputText = text)
    }

    fun selectBrain(brain: DomainBrain) {
        _uiState.value = _uiState.value.copy(selectedBrain = brain)
        val intelligenceBrain = when (brain) {
            DomainBrain.AUTO -> IntelligenceBrain.AUTO
            DomainBrain.GENERAL -> IntelligenceBrain.GENERAL
            DomainBrain.FARMER -> IntelligenceBrain.FARMER
            DomainBrain.RESEARCHER -> IntelligenceBrain.RESEARCHER
            DomainBrain.ANALYST -> IntelligenceBrain.ANALYST
        }
        brainManager.selectBrain(intelligenceBrain)
    }

    fun setLanguage(lang: ChatLanguage) {
        _uiState.value = _uiState.value.copy(language = lang)
    }

    fun sendMessage(queryText: String? = null) {
        val text = queryText ?: _uiState.value.inputText.trim()
        if (text.isBlank()) return

        val userMessage = ChatMessage.User(text = text)
        val currentMessages = _uiState.value.messages + userMessage
        _uiState.value = _uiState.value.copy(
            messages = currentMessages,
            inputText = "",
            isSending = true,
            lastFailedQuery = null
        )
        _chatState.value = ResultState.Loading

        val loc = locationManager.locationState.value
        val query = ChatQuery(
            sessionId = _uiState.value.sessionId,
            query = text,
            languagePreference = _uiState.value.language,
            selectedBrain = _uiState.value.selectedBrain,
            latitude = loc.latitude,
            longitude = loc.longitude
        )

        viewModelScope.launch {
            val result = repository.sendChat(query)
            _chatState.value = result
            when (result) {
                is ResultState.Success<ChatResponse> -> {
                    val assistantMsg = ChatMessage.Assistant(response = result.data)
                    _uiState.value = _uiState.value.copy(
                        messages = _uiState.value.messages + assistantMsg,
                        isSending = false
                    )
                }
                is ResultState.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isSending = false,
                        lastFailedQuery = text
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(isSending = false)
                }
            }
        }
    }

    fun retryLast() {
        val query = _uiState.value.lastFailedQuery
        if (query != null) {
            sendMessage(query)
        }
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                ChatViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager,
                    brainManager = app.container.sharedBrainManager
                )
            }
        }
    }
}
