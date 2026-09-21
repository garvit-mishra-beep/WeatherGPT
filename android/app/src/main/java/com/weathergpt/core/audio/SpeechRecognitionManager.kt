package com.weathergpt.core.audio

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

private const val TAG = "SpeechRecognitionMgr"

sealed class SpeechRecognitionState {
    object Idle : SpeechRecognitionState()
    object Listening : SpeechRecognitionState()
    data class Success(val text: String) : SpeechRecognitionState()
    data class Error(val message: String, val errorCode: Int? = null) : SpeechRecognitionState()
    object NotAvailable : SpeechRecognitionState()
}

/**
 * Native Android SpeechRecognizer wrapper providing on-device speech-to-text.
 *
 * Adheres to Vayubodhak Phase 1 Voice architecture:
 * Microphone -> Android SpeechRecognizer -> Recognized Text -> Chat / Brain Routing.
 */
open class SpeechRecognitionManager(
    private val context: Context?
) {
    private var speechRecognizer: SpeechRecognizer? = null

    private val _state = MutableStateFlow<SpeechRecognitionState>(SpeechRecognitionState.Idle)
    val state: StateFlow<SpeechRecognitionState> = _state.asStateFlow()

    open fun isRecognitionAvailable(): Boolean {
        val ctx = context ?: return false
        return SpeechRecognizer.isRecognitionAvailable(ctx)
    }

    open fun startListening(
        languageCode: String = "hi",
        onResult: (String) -> Unit = {},
        onError: (String) -> Unit = {}
    ) {
        val ctx = context
        if (ctx == null || !isRecognitionAvailable()) {
            _state.value = SpeechRecognitionState.NotAvailable
            onError("Speech recognition is not available on this device")
            return
        }

        stopListening()

        try {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(ctx).apply {
                setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {
                        Log.d(TAG, "Speech recognizer ready for speech")
                        _state.value = SpeechRecognitionState.Listening
                    }

                    override fun onBeginningOfSpeech() {
                        Log.d(TAG, "Beginning of speech detected")
                    }

                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {
                        Log.d(TAG, "End of speech detected")
                    }

                    override fun onError(error: Int) {
                        val errorMsg = when (error) {
                            SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                            SpeechRecognizer.ERROR_CLIENT -> "Client error"
                            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission required"
                            SpeechRecognizer.ERROR_NETWORK -> "Network error during speech recognition"
                            SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                            SpeechRecognizer.ERROR_NO_MATCH -> "No speech recognized"
                            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognition service busy"
                            SpeechRecognizer.ERROR_SERVER -> "Server error"
                            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech input detected"
                            else -> "Recognition failed (code $error)"
                        }
                        Log.w(TAG, "SpeechRecognizer error: $errorMsg (code $error)")
                        _state.value = SpeechRecognitionState.Error(errorMsg, error)
                        onError(errorMsg)
                    }

                    override fun onResults(results: Bundle?) {
                        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        val recognizedText = matches?.firstOrNull()?.trim().orEmpty()
                        Log.d(TAG, "Speech recognition results received: '$recognizedText'")
                        if (recognizedText.isNotEmpty()) {
                            _state.value = SpeechRecognitionState.Success(recognizedText)
                            onResult(recognizedText)
                        } else {
                            _state.value = SpeechRecognitionState.Error("No speech recognized")
                            onError("No speech recognized")
                        }
                    }

                    override fun onPartialResults(partialResults: Bundle?) {}
                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
            }

            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, languageCode)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, languageCode)
                putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, languageCode)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }

            speechRecognizer?.startListening(intent)
            _state.value = SpeechRecognitionState.Listening
            Log.d(TAG, "Started speech recognition listener with lang: $languageCode")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start speech recognition: ${e.message}", e)
            val err = "Failed to start speech recognition: ${e.message}"
            _state.value = SpeechRecognitionState.Error(err)
            onError(err)
        }
    }

    open fun stopListening() {
        try {
            speechRecognizer?.stopListening()
            speechRecognizer?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "Error cleaning up SpeechRecognizer: ${e.message}")
        } finally {
            speechRecognizer = null
            if (_state.value is SpeechRecognitionState.Listening) {
                _state.value = SpeechRecognitionState.Idle
            }
        }
    }

    open fun cancel() {
        try {
            speechRecognizer?.cancel()
            speechRecognizer?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "Error cancelling SpeechRecognizer: ${e.message}")
        } finally {
            speechRecognizer = null
            _state.value = SpeechRecognitionState.Idle
        }
    }
}
