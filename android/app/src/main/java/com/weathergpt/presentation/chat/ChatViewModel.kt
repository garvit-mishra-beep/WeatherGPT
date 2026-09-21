package com.weathergpt.presentation.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.audio.AudioPlayerManager
import com.weathergpt.core.audio.AudioRecorderManager
import com.weathergpt.core.audio.SpeechRecognitionManager
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.core.settings.AppLanguage
import com.weathergpt.core.settings.SharedSettingsManager
import com.weathergpt.domain.model.chat.AdvisoryRecommendation
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.ConfidenceAssessment
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.chat.EvidenceCitation
import com.weathergpt.domain.model.decision.NirnayCard
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.presentation.components.IntelligenceBrain
import java.util.Locale
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.UUID

enum class VoiceState {
    IDLE,
    RECORDING,
    UPLOADING,
    TRANSCRIBING,
    THINKING,
    SPEAKING,
    ERROR
}

sealed class ChatMessage {
    data class User(
        val id: String = UUID.randomUUID().toString(),
        val text: String,
        val timestamp: String = "Just now"
    ) : ChatMessage()

    data class Assistant(
        val id: String = UUID.randomUUID().toString(),
        val response: ChatResponse,
        val timestamp: String = "Just now",
        val audioBytes: ByteArray? = null,
        val nirnayCard: NirnayCard? = null
    ) : ChatMessage()
}

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val inputText: String = "",
    val selectedBrain: DomainBrain = DomainBrain.AUTO,
    val language: ChatLanguage = ChatLanguage.HINDI,
    val sessionId: String = UUID.randomUUID().toString(),
    val isSending: Boolean = false,
    val lastFailedQuery: String? = null,
    val voiceState: VoiceState = VoiceState.IDLE,
    val isPlayingAudio: Boolean = false,
    val activeAudioMessageId: String? = null,
    val voiceErrorMessage: String? = null
)

class ChatViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager,
    private val brainManager: SharedBrainManager = SharedBrainManager(),
    private val settingsManager: SharedSettingsManager? = null,
    private val audioRecorder: AudioRecorderManager = AudioRecorderManager(),
    private val audioPlayer: AudioPlayerManager = AudioPlayerManager(),
    private val speechRecognitionManager: SpeechRecognitionManager? = null
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        ChatUiState(
            selectedBrain = brainManager.getDomainBrain(),
            language = settingsManager?.appLanguage?.value?.toChatLanguage() ?: ChatLanguage.ENGLISH
        )
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
        if (settingsManager != null) {
            viewModelScope.launch {
                settingsManager.appLanguage.collectLatest { appLang ->
                    val chatLang = appLang.toChatLanguage()
                    _uiState.value = _uiState.value.copy(language = chatLang)
                }
            }
        }
        viewModelScope.launch {
            audioPlayer.isPlaying.collectLatest { playing ->
                _uiState.value = _uiState.value.copy(
                    isPlayingAudio = playing,
                    voiceState = if (playing) VoiceState.SPEAKING else if (_uiState.value.voiceState == VoiceState.SPEAKING) VoiceState.IDLE else _uiState.value.voiceState,
                    activeAudioMessageId = if (playing) _uiState.value.activeAudioMessageId else null
                )
            }
        }
    }

    fun setInputText(text: String) {
        _uiState.value = _uiState.value.copy(
            inputText = text,
            voiceErrorMessage = if (text.isNotBlank()) null else _uiState.value.voiceErrorMessage,
            voiceState = if (text.isNotBlank() && _uiState.value.voiceState == VoiceState.ERROR) VoiceState.IDLE else _uiState.value.voiceState
        )
    }

    fun clearVoiceError() {
        _uiState.value = _uiState.value.copy(
            voiceErrorMessage = null,
            voiceState = if (_uiState.value.voiceState == VoiceState.ERROR) VoiceState.IDLE else _uiState.value.voiceState
        )
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
        val appLang = AppLanguage.fromCode(lang.code)
        settingsManager?.setLanguage(appLang)
    }

    // ========================================================================
    // Voice Actions: Record -> Transcribe -> Chat Query -> Speak
    // ========================================================================

    fun startVoiceRecording() {
        if (_uiState.value.voiceState in listOf(
                VoiceState.RECORDING,
                VoiceState.UPLOADING,
                VoiceState.TRANSCRIBING,
                VoiceState.THINKING
            )
        ) {
            return
        }
        stopAudioPlayback()

        // 1. Primary path: Native Android on-device SpeechRecognizer
        if (speechRecognitionManager != null && speechRecognitionManager.isRecognitionAvailable()) {
            _uiState.value = _uiState.value.copy(
                voiceState = VoiceState.RECORDING,
                voiceErrorMessage = null
            )
            speechRecognitionManager.startListening(
                languageCode = _uiState.value.language.code,
                onResult = { recognizedText ->
                    if (recognizedText.isNotBlank()) {
                        _uiState.value = _uiState.value.copy(voiceState = VoiceState.THINKING)
                        sendMessage(queryText = recognizedText, autoSpeakResponse = true)
                    } else {
                        _uiState.value = _uiState.value.copy(
                            voiceState = VoiceState.ERROR,
                            voiceErrorMessage = "No speech recognized."
                        )
                    }
                },
                onError = { errorMsg ->
                    _uiState.value = _uiState.value.copy(
                        voiceState = VoiceState.ERROR,
                        voiceErrorMessage = errorMsg
                    )
                }
            )
            return
        }

        // 2. Secondary path: Audio recorder capturing PCM/WAV for backend STT
        viewModelScope.launch {
            val started = audioRecorder.startRecording()
            if (started) {
                _uiState.value = _uiState.value.copy(
                    voiceState = VoiceState.RECORDING,
                    voiceErrorMessage = null
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    voiceState = VoiceState.ERROR,
                    voiceErrorMessage = "Could not access microphone."
                )
            }
        }
    }

    fun stopVoiceRecordingAndSend() {
        if (_uiState.value.voiceState != VoiceState.RECORDING) return

        if (speechRecognitionManager != null && speechRecognitionManager.isRecognitionAvailable()) {
            _uiState.value = _uiState.value.copy(voiceState = VoiceState.TRANSCRIBING)
            speechRecognitionManager.stopListening()
            return
        }

        _uiState.value = _uiState.value.copy(voiceState = VoiceState.UPLOADING)

        viewModelScope.launch {
            val audioBytes = audioRecorder.stopRecording()
            if (audioBytes == null || audioBytes.isEmpty()) {
                _uiState.value = _uiState.value.copy(
                    voiceState = VoiceState.ERROR,
                    voiceErrorMessage = "No audio recorded."
                )
                return@launch
            }

            _uiState.value = _uiState.value.copy(voiceState = VoiceState.TRANSCRIBING)

            val langCode = _uiState.value.language.code
            val sttResult = repository.speechToText(audioBytes, langCode)

            when (sttResult) {
                is ResultState.Success -> {
                    val transcript = sttResult.data.text.trim()
                    if (transcript.isBlank()) {
                        _uiState.value = _uiState.value.copy(
                            voiceState = VoiceState.ERROR,
                            voiceErrorMessage = "Could not understand speech."
                        )
                    } else {
                        _uiState.value = _uiState.value.copy(
                            voiceState = VoiceState.THINKING
                        )
                        sendMessage(queryText = transcript, autoSpeakResponse = true)
                    }
                }
                is ResultState.Error -> {
                    _uiState.value = _uiState.value.copy(
                        voiceState = VoiceState.ERROR,
                        voiceErrorMessage = sttResult.error.message
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(voiceState = VoiceState.IDLE)
                }
            }
        }
    }

    fun cancelVoiceRecording() {
        speechRecognitionManager?.cancel()
        audioRecorder.cancelRecording()
        _uiState.value = _uiState.value.copy(
            voiceState = VoiceState.IDLE,
            voiceErrorMessage = null
        )
    }

    fun playAssistantAudio(messageId: String, text: String) {
        if (_uiState.value.isPlayingAudio && _uiState.value.activeAudioMessageId == messageId) {
            stopAudioPlayback()
            return
        }

        stopAudioPlayback()
        _uiState.value = _uiState.value.copy(
            voiceState = VoiceState.THINKING,
            activeAudioMessageId = messageId
        )

        viewModelScope.launch {
            val langCode = _uiState.value.language.code
            val ttsResult = repository.textToSpeech(text = text, languageCode = langCode)

            when (ttsResult) {
                is ResultState.Success -> {
                    val audioBytes = ttsResult.data
                    _uiState.value = _uiState.value.copy(voiceState = VoiceState.SPEAKING)
                    audioPlayer.playAudio(
                        audioBytes = audioBytes,
                        onCompletion = {
                            _uiState.value = _uiState.value.copy(
                                voiceState = VoiceState.IDLE,
                                activeAudioMessageId = null
                            )
                        },
                        onError = { errMsg ->
                            _uiState.value = _uiState.value.copy(
                                voiceState = VoiceState.ERROR,
                                voiceErrorMessage = errMsg,
                                activeAudioMessageId = null
                            )
                        }
                    )
                }
                is ResultState.Error -> {
                    _uiState.value = _uiState.value.copy(
                        voiceState = VoiceState.ERROR,
                        voiceErrorMessage = ttsResult.error.message,
                        activeAudioMessageId = null
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(
                        voiceState = VoiceState.IDLE,
                        activeAudioMessageId = null
                    )
                }
            }
        }
    }

    fun stopAudioPlayback() {
        audioPlayer.stop()
        _uiState.value = _uiState.value.copy(
            voiceState = if (_uiState.value.voiceState == VoiceState.SPEAKING) VoiceState.IDLE else _uiState.value.voiceState,
            isPlayingAudio = false,
            activeAudioMessageId = null
        )
    }

    private var sendJob: Job? = null

    fun sendMessage(
        queryText: String? = null,
        autoSpeakResponse: Boolean = false,
        isRetry: Boolean = false
    ) {
        if (_uiState.value.isSending || sendJob?.isActive == true) return
        val text = queryText ?: _uiState.value.inputText.trim()
        if (text.isBlank()) return

        val currentMessages = if (isRetry) {
            _uiState.value.messages
        } else {
            _uiState.value.messages + ChatMessage.User(text = text)
        }

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

        sendJob = viewModelScope.launch {
            if (com.weathergpt.core.config.AppConfig.isDemoMode) {
                val result = repository.sendChat(query)
                _chatState.value = result
                when (result) {
                    is ResultState.Success<ChatResponse> -> {
                        val card = com.weathergpt.domain.brain.OfflineDemoIntelligenceEngine.lastEvaluatedNirnayCard
                        val assistantMsg = ChatMessage.Assistant(
                            response = result.data,
                            nirnayCard = card
                        )
                        _uiState.value = _uiState.value.copy(
                            messages = _uiState.value.messages + assistantMsg,
                            isSending = false,
                            lastFailedQuery = null,
                            voiceState = if (autoSpeakResponse) VoiceState.THINKING else VoiceState.IDLE
                        )
                        if (autoSpeakResponse) {
                            val speakText = result.data.summary.ifBlank { result.data.answer }
                            if (speakText.isNotBlank()) {
                                playAssistantAudio(assistantMsg.id, speakText)
                            } else {
                                _uiState.value = _uiState.value.copy(voiceState = VoiceState.IDLE)
                            }
                        }
                    }
                    is ResultState.Error -> {
                        _uiState.value = _uiState.value.copy(
                            isSending = false,
                            lastFailedQuery = text,
                            voiceState = VoiceState.IDLE
                        )
                    }
                    else -> {
                        _uiState.value = _uiState.value.copy(
                            isSending = false,
                            voiceState = VoiceState.IDLE
                        )
                    }
                }
                return@launch
            }

            val lowerText = text.lowercase(Locale.ROOT)
            val isDecisionQuery = lowerText.contains("should i spray") ||
                    lowerText.contains("spray cotton") ||
                    lowerText.contains("cotton spray") ||
                    lowerText.contains("nirnay") ||
                    lowerText.contains("action window") ||
                    lowerText.contains("warning near me") ||
                    lowerText.contains("alert near me") ||
                    lowerText.contains("red rainfall warning") ||
                    lowerText.contains("rainfall warning") ||
                    lowerText.contains("red warning") ||
                    lowerText.contains("orange warning") ||
                    lowerText.contains("yellow warning") ||
                    (lowerText.contains("what should i do") && (lowerText.contains("warning") || lowerText.contains("alert") || lowerText.contains("rain") || lowerText.contains("red")))

            if (isDecisionQuery) {
                val isFarmerQuery = lowerText.contains("spray") ||
                        lowerText.contains("cotton") ||
                        lowerText.contains("crop") ||
                        lowerText.contains("irrigation") ||
                        lowerText.contains("pesticide")

                val queryDomain = if (isFarmerQuery) "farmer" else "general"
                val queryContext = if (isFarmerQuery) mapOf("crop_name" to "Cotton") else emptyMap()

                val decisionResult = repository.evaluateDecision(
                    question = text,
                    locationName = loc.districtName.ifBlank { "Gwalior" },
                    latitude = loc.latitude,
                    longitude = loc.longitude,
                    domain = queryDomain,
                    context = queryContext
                )

                when (decisionResult) {
                    is ResultState.Success<NirnayCard> -> {
                        val card = decisionResult.data
                        val answerText = buildString {
                            appendLine("**${card.verdict.raw}** — ${card.recommendedAction}")
                            appendLine()
                            if (card.alertImpact != null) {
                                val ai = card.alertImpact
                                appendLine("• **Warning Status:** ${ai.affectedAreaStatus.raw} (${ai.exposureSummary ?: ai.affectedAreaStatus.raw})")
                                if (!ai.hazard.isNullOrBlank()) {
                                    appendLine("• **Hazard:** ${ai.hazard}")
                                }
                                if (!ai.issuingOffice.isNullOrBlank()) {
                                    appendLine("• **Source:** ${ai.issuingOffice}${if (ai.isOfficial) " (Official)" else ""}")
                                }
                                if (ai.compositeImpactScore != null) {
                                    appendLine("• **Impact Score:** ${String.format(Locale.ROOT, "%.1f", ai.compositeImpactScore)}/10.0 (${ai.riskCategory?.uppercase(Locale.ROOT) ?: "RISK"})")
                                }
                            } else if (card.actionWindow.isAvailable && card.actionWindow.bestWindow != null) {
                                appendLine("• **Best Action Window:** ${card.actionWindow.bestWindow.summary}")
                            } else {
                                appendLine("• **Action Window:** ${card.actionWindow.reason}")
                            }
                        }

                        val authorityName = card.alertImpact?.issuingOffice ?: "Deterministic Decision Engine"
                        val isOfficialAuth = card.alertImpact?.isOfficial ?: false

                        val synthesizedResponse = ChatResponse(
                            responseId = card.ledger?.decisionId ?: UUID.randomUUID().toString(),
                            sessionId = _uiState.value.sessionId,
                            brain = if (queryDomain == "farmer") DomainBrain.FARMER else DomainBrain.GENERAL,
                            language = _uiState.value.language.code,
                            createdAt = "Just now",
                            summary = card.recommendedAction,
                            answer = answerText,
                            data = null,
                            recommendation = AdvisoryRecommendation(
                                primaryAction = card.recommendedAction,
                                urgency = card.severity.raw,
                                actions = card.alternatives
                            ),
                            alert = null,
                            visualizations = emptyList(),
                            sources = listOf(
                                EvidenceCitation(
                                    authority = authorityName,
                                    dataset = if (card.alertImpact != null) "CAP Severe Weather Bulletin" else "GFS 0.25° NWP / Open-Meteo",
                                    retrievedAt = "Just now",
                                    isOfficial = isOfficialAuth
                                )
                            ),
                            confidence = ConfidenceAssessment(
                                evidenceLevel = card.confidence.raw,
                                modelAgreement = if (card.uncertainty.wrfStatus == "available") "High" else null,
                                dataFreshnessStatus = "Verified",
                                notes = card.uncertainty.uncertaintyNote
                            ),
                            limitations = listOf(card.uncertainty.uncertaintyNote)
                        )

                        val assistantMsg = ChatMessage.Assistant(
                            response = synthesizedResponse,
                            nirnayCard = card
                        )

                        _uiState.value = _uiState.value.copy(
                            messages = _uiState.value.messages + assistantMsg,
                            isSending = false,
                            lastFailedQuery = null,
                            voiceState = if (autoSpeakResponse) VoiceState.THINKING else VoiceState.IDLE
                        )
                        _chatState.value = ResultState.Success(synthesizedResponse)

                        if (autoSpeakResponse) {
                            playAssistantAudio(assistantMsg.id, card.recommendedAction)
                        }
                        return@launch
                    }
                    is ResultState.Error -> {
                        // If decision evaluation fails with an explicit error, record it
                        _uiState.value = _uiState.value.copy(
                            isSending = false,
                            lastFailedQuery = text,
                            voiceState = if (autoSpeakResponse) VoiceState.ERROR else VoiceState.IDLE,
                            voiceErrorMessage = if (autoSpeakResponse) decisionResult.error.message else null
                        )
                        _chatState.value = ResultState.Error(decisionResult.error)
                        return@launch
                    }
                    else -> {}
                }
            }

            val result = repository.sendChat(query)
            _chatState.value = result
            when (result) {
                is ResultState.Success<ChatResponse> -> {
                    val assistantMsg = ChatMessage.Assistant(response = result.data)
                    _uiState.value = _uiState.value.copy(
                        messages = _uiState.value.messages + assistantMsg,
                        isSending = false,
                        lastFailedQuery = null,
                        voiceState = if (autoSpeakResponse) VoiceState.THINKING else VoiceState.IDLE
                    )
                    if (autoSpeakResponse) {
                        val speakText = result.data.summary.ifBlank { result.data.answer }
                        if (speakText.isNotBlank()) {
                            playAssistantAudio(assistantMsg.id, speakText)
                        } else {
                            _uiState.value = _uiState.value.copy(voiceState = VoiceState.IDLE)
                        }
                    }
                }
                is ResultState.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isSending = false,
                        lastFailedQuery = text,
                        voiceState = if (autoSpeakResponse) VoiceState.ERROR else VoiceState.IDLE,
                        voiceErrorMessage = if (autoSpeakResponse) result.error.message else null
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(
                        isSending = false,
                        voiceState = VoiceState.IDLE
                    )
                }
            }
        }
    }

    fun retryLast() {
        val query = _uiState.value.lastFailedQuery
        if (query != null && !_uiState.value.isSending) {
            sendMessage(queryText = query, autoSpeakResponse = false, isRetry = true)
        }
    }

    override fun onCleared() {
        super.onCleared()
        speechRecognitionManager?.cancel()
        audioRecorder.cancelRecording()
        audioPlayer.release()
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                ChatViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager,
                    brainManager = app.container.sharedBrainManager,
                    settingsManager = app.container.sharedSettingsManager,
                    audioRecorder = AudioRecorderManager(app.applicationContext),
                    audioPlayer = AudioPlayerManager(app.applicationContext),
                    speechRecognitionManager = SpeechRecognitionManager(app.applicationContext)
                )
            }
        }
    }
}
