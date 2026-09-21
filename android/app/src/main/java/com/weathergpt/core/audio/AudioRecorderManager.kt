package com.weathergpt.core.audio

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

private const val TAG = "AudioRecorderManager"
private const val SAMPLE_RATE = 16000
private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT

/**
 * Robust Android Audio Recorder capturing 16kHz 16-bit PCM Mono audio and encoding to standard WAV.
 */
open class AudioRecorderManager(
    private val context: Context? = null
) {
    private var audioRecord: AudioRecord? = null
    private var recordingJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO)

    protected val _isRecording = MutableStateFlow(false)
    open val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()

    private var rawAudioStream: ByteArrayOutputStream? = null

    @SuppressLint("MissingPermission")
    open suspend fun startRecording(): Boolean = withContext(Dispatchers.IO) {
        if (_isRecording.value) return@withContext true

        try {
            val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
            if (minBufferSize == AudioRecord.ERROR || minBufferSize == AudioRecord.ERROR_BAD_VALUE) {
                Log.e(TAG, "Invalid buffer size for AudioRecord")
                return@withContext false
            }

            val bufferSize = (minBufferSize * 2).coerceAtLeast(4096)
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord initialization failed")
                audioRecord?.release()
                audioRecord = null
                return@withContext false
            }

            audioRecord?.startRecording()
            _isRecording.value = true
            rawAudioStream = ByteArrayOutputStream()

            recordingJob = scope.launch {
                val buffer = ByteArray(bufferSize)
                while (isActive && _isRecording.value) {
                    val readBytes = audioRecord?.read(buffer, 0, buffer.size) ?: -1
                    if (readBytes > 0) {
                        rawAudioStream?.write(buffer, 0, readBytes)
                    }
                }
            }

            Log.d(TAG, "Started recording audio (16kHz, 16-bit PCM, Mono)")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error starting recording: ", e)
            cleanup()
            false
        }
    }

    open suspend fun stopRecording(): ByteArray? = withContext(Dispatchers.IO) {
        if (!_isRecording.value) return@withContext null

        _isRecording.value = false
        recordingJob?.cancel()
        recordingJob = null

        try {
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping audioRecord: ")
        }

        val rawPcm = rawAudioStream?.toByteArray()
        rawAudioStream = null

        if (rawPcm == null || rawPcm.isEmpty()) {
            Log.w(TAG, "Recorded audio stream is empty")
            return@withContext null
        }

        val wavBytes = addWavHeader(rawPcm, SAMPLE_RATE, 1, 16)
        Log.d(TAG, "Finished recording:  PCM bytes ->  WAV bytes")
        wavBytes
    }

    open fun cancelRecording() {
        _isRecording.value = false
        recordingJob?.cancel()
        recordingJob = null
        cleanup()
    }

    private fun cleanup() {
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (e: Exception) {
            // Ignored on cleanup
        } finally {
            audioRecord = null
            rawAudioStream = null
        }
    }

    /**
     * Builds a 44-byte standard RIFF/WAVE header for raw linear PCM audio bytes.
     */
    private fun addWavHeader(
        pcmData: ByteArray,
        sampleRate: Int,
        channels: Int,
        bitsPerSample: Int
    ): ByteArray {
        val totalAudioLen = pcmData.size
        val totalDataLen = totalAudioLen + 36
        val byteRate = sampleRate * channels * bitsPerSample / 8
        val blockAlign = channels * bitsPerSample / 8

        val header = ByteBuffer.allocate(44).apply {
            order(ByteOrder.LITTLE_ENDIAN)
            put('R'.code.toByte())
            put('I'.code.toByte())
            put('F'.code.toByte())
            put('F'.code.toByte())
            putInt(totalDataLen)
            put('W'.code.toByte())
            put('A'.code.toByte())
            put('V'.code.toByte())
            put('E'.code.toByte())
            put('f'.code.toByte())
            put('m'.code.toByte())
            put('t'.code.toByte())
            put(' '.code.toByte())
            putInt(16) // Subchunk1Size for PCM
            putShort(1.toShort()) // AudioFormat 1 = PCM
            putShort(channels.toShort())
            putInt(sampleRate)
            putInt(byteRate)
            putShort(blockAlign.toShort())
            putShort(bitsPerSample.toShort())
            put('d'.code.toByte())
            put('a'.code.toByte())
            put('t'.code.toByte())
            put('a'.code.toByte())
            putInt(totalAudioLen)
        }.array()

        return header + pcmData
    }
}
