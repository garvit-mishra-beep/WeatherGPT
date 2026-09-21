package com.weathergpt.core.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

private const val TAG = "AudioPlayerManager"

/**
 * Lifecycle-safe Android Audio Player for synthesized speech responses (MP3).
 */
open class AudioPlayerManager(
    private val context: Context? = null
) {
    private var mediaPlayer: MediaPlayer? = null
    private var tempAudioFile: File? = null

    protected val _isPlaying = MutableStateFlow(false)
    open val isPlaying: StateFlow<Boolean> = _isPlaying.asStateFlow()

    open suspend fun playAudio(
        audioBytes: ByteArray,
        onCompletion: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) = withContext(Dispatchers.Main) {
        stop()

        if (audioBytes.isEmpty()) {
            onError?.invoke("Audio payload is empty")
            return@withContext
        }

        try {
            // Write audio bytes to temporary cache file
            val tempDir = context?.cacheDir ?: File(System.getProperty("java.io.tmpdir") ?: ".")
            tempAudioFile = File.createTempFile("weather_voice_", ".mp3", tempDir).apply {
                deleteOnExit()
                FileOutputStream(this).use { it.write(audioBytes) }
            }

            mediaPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_ASSISTANT)
                        .build()
                )
                setDataSource(tempAudioFile!!.absolutePath)
                setOnPreparedListener { mp ->
                    mp.start()
                    _isPlaying.value = true
                    Log.d(TAG, "Audio playback started ( bytes)")
                }
                setOnCompletionListener {
                    _isPlaying.value = false
                    cleanupPlayer()
                    onCompletion?.invoke()
                    Log.d(TAG, "Audio playback completed")
                }
                setOnErrorListener { _, what, extra ->
                    _isPlaying.value = false
                    cleanupPlayer()
                    val msg = "MediaPlayer error (what=, extra=)"
                    Log.e(TAG, msg)
                    onError?.invoke(msg)
                    true
                }
                prepareAsync()
            }
        } catch (e: Exception) {
            _isPlaying.value = false
            cleanupPlayer()
            Log.e(TAG, "Failed to start audio playback: ", e)
            onError?.invoke(e.message ?: "Playback initialization failed")
        }
    }

    open fun stop() {
        if (_isPlaying.value || mediaPlayer != null) {
            try {
                if (mediaPlayer?.isPlaying == true) {
                    mediaPlayer?.stop()
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error stopping mediaPlayer: ")
            } finally {
                _isPlaying.value = false
                cleanupPlayer()
            }
        }
    }

    open fun release() {
        stop()
    }

    private fun cleanupPlayer() {
        try {
            mediaPlayer?.reset()
            mediaPlayer?.release()
        } catch (e: Exception) {
            // Ignored on cleanup
        } finally {
            mediaPlayer = null
        }

        try {
            tempAudioFile?.delete()
        } catch (e: Exception) {
            // Ignored
        } finally {
            tempAudioFile = null
        }
    }
}
