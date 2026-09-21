package com.weathergpt.presentation.chat

import com.weathergpt.core.audio.AudioPlayerManager
import com.weathergpt.core.audio.AudioRecorderManager
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.core.error.AppError
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.remote.dto.voice.VoiceSttResponseDto
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatQuery
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.lang.reflect.Proxy

@OptIn(ExperimentalCoroutinesApi::class)
class ChatViewModelVoiceTest {

    private val testDispatcher = StandardTestDispatcher()

    private class FakeAudioRecorderManager : AudioRecorderManager(null) {
        var startResult: Boolean = true
        var stopResultBytes: ByteArray? = byteArrayOf(82, 73, 70, 70, 0, 0, 0, 0)
        var isCancelled: Boolean = false

        override suspend fun startRecording(): Boolean {
            _isRecording.value = startResult
            return startResult
        }

        override suspend fun stopRecording(): ByteArray? {
            _isRecording.value = false
            return stopResultBytes
        }

        override fun cancelRecording() {
            _isRecording.value = false
            isCancelled = true
        }
    }

    private class FakeAudioPlayerManager : AudioPlayerManager(null) {
        var playedAudioBytes: ByteArray? = null
        var shouldSucceed: Boolean = true
        var errorMessage: String = "Playback failure"

        override suspend fun playAudio(
            audioBytes: ByteArray,
            onCompletion: (() -> Unit)?,
            onError: ((String) -> Unit)?
        ) {
            playedAudioBytes = audioBytes
            if (shouldSucceed) {
                _isPlaying.value = true
                onCompletion?.invoke()
                _isPlaying.value = false
            } else {
                _isPlaying.value = false
                onError?.invoke(errorMessage)
            }
        }

        override fun stop() {
            _isPlaying.value = false
        }
    }

    private fun createProxyRepository(
        sttText: String = "इंदौर में आज मौसम कैसा है",
        sttConfidence: Double = 0.96,
        sttError: AppError? = null,
        ttsBytes: ByteArray = byteArrayOf(1, 2, 3, 4),
        ttsError: AppError? = null
    ): WeatherGPTRepository {
        val handler = java.lang.reflect.InvocationHandler { _, method, args ->
            when (method.name) {
                "speechToText" -> {
                    if (sttError != null) {
                        ResultState.Error(sttError)
                    } else {
                        ResultState.Success(
                            VoiceSttResponseDto(
                                text = sttText,
                                languageCode = "hi",
                                provider = "google_speech_to_text_v2",
                                confidence = sttConfidence,
                                detectedLanguage = "hi-IN"
                            )
                        )
                    }
                }
                "textToSpeech" -> {
                    if (ttsError != null) {
                        ResultState.Error(ttsError)
                    } else {
                        ResultState.Success(ttsBytes)
                    }
                }
                "sendChat" -> {
                    val q = args?.get(0) as? ChatQuery
                    ResultState.Success(
                        ChatResponse(
                            responseId = "resp_test_001",
                            sessionId = q?.sessionId ?: "test_session",
                            brain = q?.selectedBrain ?: DomainBrain.AUTO,
                            language = q?.languagePreference?.code ?: "hi",
                            createdAt = "2026-08-30T10:00:00Z",
                            summary = "इंदौर में आज मौसम साफ रहेगा।",
                            answer = "इंदौर में आज अधिकतम तापमान 32 डिग्री सेल्सियस रहने का अनुमान है।",
                            data = null,
                            recommendation = null,
                            alert = null,
                            visualizations = emptyList(),
                            sources = emptyList(),
                            confidence = null,
                            limitations = emptyList()
                        )
                    )
                }
                else -> ResultState.Success(Unit)
            }
        }
        return Proxy.newProxyInstance(
            WeatherGPTRepository::class.java.classLoader,
            arrayOf(WeatherGPTRepository::class.java),
            handler
        ) as WeatherGPTRepository
    }

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialVoiceStateIsIdle() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
        assertFalse(viewModel.uiState.value.isPlayingAudio)
    }

    @Test
    fun testVoiceLanguageMapping() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.setLanguage(ChatLanguage.MARATHI)
        assertEquals(ChatLanguage.MARATHI, viewModel.uiState.value.language)
        assertEquals("mr", viewModel.uiState.value.language.code)

        viewModel.setLanguage(ChatLanguage.TAMIL)
        assertEquals(ChatLanguage.TAMIL, viewModel.uiState.value.language)
        assertEquals("ta", viewModel.uiState.value.language.code)

        viewModel.setLanguage(ChatLanguage.ENGLISH)
        assertEquals(ChatLanguage.ENGLISH, viewModel.uiState.value.language)
        assertEquals("en", viewModel.uiState.value.language.code)
    }

    @Test
    fun testNormalTypedChatStillWorks() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.setInputText("What is the temperature in Surat?")
        viewModel.sendMessage()
        advanceUntilIdle()

        assertEquals(2, viewModel.uiState.value.messages.size)
        val userMsg = viewModel.uiState.value.messages[0] as ChatMessage.User
        val assistantMsg = viewModel.uiState.value.messages[1] as ChatMessage.Assistant

        assertEquals("What is the temperature in Surat?", userMsg.text)
        assertNotNull(assistantMsg.response)
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
    }

    @Test
    fun testVoiceRecordingWorkflowTransitions() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        // 1. Start recording
        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.RECORDING, viewModel.uiState.value.voiceState)

        // 2. Cancel recording
        viewModel.cancelVoiceRecording()
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
        assertTrue(fakeRecorder.isCancelled)
    }

    @Test
    fun testVoiceRecordStopAndQuerySuccessFlow() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val repo = createProxyRepository(sttText = "पुणे का मौसम बताओ")
        val viewModel = ChatViewModel(
            repository = repo,
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        // Start recording
        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.RECORDING, viewModel.uiState.value.voiceState)

        // Stop recording and send -> auto triggers STT, sendChat, and TTS
        viewModel.stopVoiceRecordingAndSend()
        advanceUntilIdle()

        // Verify messages were created from transcribed text
        assertEquals(2, viewModel.uiState.value.messages.size)
        val userMsg = viewModel.uiState.value.messages[0] as ChatMessage.User
        assertEquals("पुणे का मौसम बताओ", userMsg.text)

        val assistantMsg = viewModel.uiState.value.messages[1] as ChatMessage.Assistant
        assertNotNull(assistantMsg.response)
        assertNotNull(fakePlayer.playedAudioBytes)
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
    }

    @Test
    fun testVoiceRecordSttErrorTransitionsToErrorState() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val repo = createProxyRepository(sttError = AppError.NetworkUnavailable("STT Network timeout"))
        val viewModel = ChatViewModel(
            repository = repo,
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.RECORDING, viewModel.uiState.value.voiceState)

        viewModel.stopVoiceRecordingAndSend()
        advanceUntilIdle()

        assertEquals(VoiceState.ERROR, viewModel.uiState.value.voiceState)
        assertNotNull(viewModel.uiState.value.voiceErrorMessage)
    }

    @Test
    fun testStopAudioPlaybackResetsState() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.stopAudioPlayback()
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
        assertFalse(viewModel.uiState.value.isPlayingAudio)
    }

    @Test
    fun testDuplicateVoiceSubmissionPrevented() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        // 1. Start recording
        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.RECORDING, viewModel.uiState.value.voiceState)

        // 2. Attempt duplicate start while already RECORDING
        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.RECORDING, viewModel.uiState.value.voiceState)
    }

    @Test
    fun testClearVoiceErrorRestoresIdle() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        fakeRecorder.startResult = false
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.ERROR, viewModel.uiState.value.voiceState)
        assertEquals("Could not access microphone.", viewModel.uiState.value.voiceErrorMessage)

        viewModel.clearVoiceError()
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
        assertEquals(null, viewModel.uiState.value.voiceErrorMessage)
    }

    @Test
    fun testTypingTextClearsVoiceError() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        fakeRecorder.startResult = false
        val fakePlayer = FakeAudioPlayerManager()
        val viewModel = ChatViewModel(
            repository = createProxyRepository(),
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.startVoiceRecording()
        advanceUntilIdle()
        assertEquals(VoiceState.ERROR, viewModel.uiState.value.voiceState)

        viewModel.setInputText("Mumbai weather")
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
        assertEquals(null, viewModel.uiState.value.voiceErrorMessage)
        assertEquals("Mumbai weather", viewModel.uiState.value.inputText)
    }

    @Test
    fun testTtsFailurePreservesTranscribedChatMessages() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val repo = createProxyRepository(
            sttText = "दिल्ली का तापमान",
            ttsError = AppError.NetworkUnavailable("TTS timeout")
        )
        val viewModel = ChatViewModel(
            repository = repo,
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.startVoiceRecording()
        advanceUntilIdle()
        viewModel.stopVoiceRecordingAndSend()
        advanceUntilIdle()

        // Verify conversation history is intact despite TTS failure
        assertEquals(2, viewModel.uiState.value.messages.size)
        val userMsg = viewModel.uiState.value.messages[0] as ChatMessage.User
        val assistantMsg = viewModel.uiState.value.messages[1] as ChatMessage.Assistant
        assertEquals("दिल्ली का तापमान", userMsg.text)
        assertNotNull(assistantMsg.response)
        assertEquals(VoiceState.ERROR, viewModel.uiState.value.voiceState)

        // User can still continue typing and send next message
        viewModel.setInputText("Thanks")
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
        viewModel.sendMessage()
        advanceUntilIdle()
        assertEquals(4, viewModel.uiState.value.messages.size)
    }

    @Test
    fun testBlankTtsResponseSafelyTransitionsToIdle() = runTest {
        val fakeRecorder = FakeAudioRecorderManager()
        val fakePlayer = FakeAudioPlayerManager()
        val handler = java.lang.reflect.InvocationHandler { _, method, args ->
            when (method.name) {
                "speechToText" -> ResultState.Success(
                    VoiceSttResponseDto(
                        text = "Hello",
                        languageCode = "en",
                        provider = "google_speech_to_text_v2",
                        confidence = 0.99,
                        detectedLanguage = "en-IN"
                    )
                )
                "sendChat" -> ResultState.Success(
                    ChatResponse(
                        responseId = "resp_blank_test",
                        sessionId = "sess_blank",
                        brain = DomainBrain.GENERAL,
                        language = "en",
                        createdAt = "2026-08-30T10:00:00Z",
                        summary = "",
                        answer = "",
                        data = null,
                        recommendation = null,
                        alert = null,
                        visualizations = emptyList(),
                        sources = emptyList(),
                        confidence = null,
                        limitations = emptyList()
                    )
                )
                else -> ResultState.Success(Unit)
            }
        }
        val blankRepo = Proxy.newProxyInstance(
            WeatherGPTRepository::class.java.classLoader,
            arrayOf(WeatherGPTRepository::class.java),
            handler
        ) as WeatherGPTRepository

        val viewModel = ChatViewModel(
            repository = blankRepo,
            locationManager = SharedLocationManager(null),
            brainManager = SharedBrainManager(),
            audioRecorder = fakeRecorder,
            audioPlayer = fakePlayer
        )
        advanceUntilIdle()

        viewModel.startVoiceRecording()
        advanceUntilIdle()
        viewModel.stopVoiceRecordingAndSend()
        advanceUntilIdle()

        // Should return to IDLE without hanging in THINKING
        assertEquals(VoiceState.IDLE, viewModel.uiState.value.voiceState)
    }
}
