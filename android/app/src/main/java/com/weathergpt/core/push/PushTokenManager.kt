package com.weathergpt.core.push

import android.content.Context
import android.os.Build
import android.provider.Settings
import android.util.Log
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.data.remote.dto.proactive.RegisterDeviceRequestDto
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Manages Firebase Cloud Messaging (FCM) registration tokens and backend synchronization.
 *
 * Adheres to Vayubodhak security and diagnostic guidelines:
 * - Never logs full tokens in plaintext (uses masking).
 * - Gracefully handles unconfigured Firebase runtime when google-services.json is absent.
 * - Dispatches token registration to backend /api/v1/proactive/devices.
 */
object PushTokenManager {

    private const val TAG = "PushTokenManager"
    private const val PREFS_NAME = "weathergpt_push_prefs"
    private const val KEY_DEVICE_ID = "cached_device_id"
    private const val KEY_LAST_TOKEN = "cached_fcm_token"

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    @Volatile
    private var apiService: WeatherGPTApiService? = null

    @Volatile
    private var currentUserId: String = "guest_farmer"

    @Volatile
    private var cachedDeviceId: String? = null

    /**
     * Initializes the token manager with API dependencies and user context.
     */
    fun init(context: Context, api: WeatherGPTApiService, userId: String = "guest_farmer") {
        apiService = api
        currentUserId = userId
        cachedDeviceId = getOrCreateDeviceId(context)

        checkAndSyncToken(context)
    }

    /**
     * Updates the active user context (e.g. after profile switch or authentication).
     */
    fun updateUserId(context: Context, userId: String) {
        if (currentUserId != userId) {
            currentUserId = userId
            checkAndSyncToken(context)
        }
    }

    /**
     * Masks an FCM token for safe logging (e.g. 'eK9j...3x9z').
     */
    fun maskToken(token: String): String {
        return if (token.length <= 8) {
            "***"
        } else {
            "${token.take(4)}...${token.takeLast(4)}"
        }
    }

    /**
     * Called when a new FCM token is emitted by FirebaseMessagingService.
     */
    fun onNewToken(context: Context, token: String) {
        Log.i(TAG, "New FCM token received: ${maskToken(token)}")
        saveCachedToken(context, token)
        dispatchRegistration(context, token)
    }

    /**
     * Checks if Firebase is initialized and requests the current token if needed.
     */
    fun checkAndSyncToken(context: Context) {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            Log.d(TAG, "Demo Mode active: skipping FCM token backend sync")
            return
        }
        if (FirebaseApp.getApps(context).isEmpty()) {
            Log.w(TAG, "FirebaseApp is not initialized (google-services.json not configured). Push sync skipped.")
            return
        }

        try {
            FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
                if (!task.isSuccessful) {
                    Log.w(TAG, "Fetching FCM registration token failed: ${task.exception?.message}")
                    return@addOnCompleteListener
                }

                val token = task.result
                if (!token.isNullOrBlank()) {
                    Log.d(TAG, "Active FCM token retrieved: ${maskToken(token)}")
                    saveCachedToken(context, token)
                    dispatchRegistration(context, token)
                }
            }
        } catch (exc: Exception) {
            Log.w(TAG, "Could not acquire FCM token: ${exc.message}")
        }
    }

    private fun dispatchRegistration(context: Context, token: String) {
        val api = apiService ?: return
        val deviceId = cachedDeviceId ?: getOrCreateDeviceId(context)
        val userId = currentUserId

        scope.launch {
            try {
                val req = RegisterDeviceRequestDto(
                    userId = userId,
                    deviceId = deviceId,
                    fcmToken = token,
                    platform = "android"
                )
                val response = api.registerDeviceToken(req)
                if (response.registered) {
                    Log.i(TAG, "FCM token registered successfully with backend for user $userId (device $deviceId)")
                } else {
                    Log.w(TAG, "Backend reported token registration incomplete: ${response.message}")
                }
            } catch (exc: Exception) {
                Log.e(TAG, "Failed to register FCM token with backend: ${exc.message}")
            }
        }
    }

    private fun getOrCreateDeviceId(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        var deviceId = prefs.getString(KEY_DEVICE_ID, null)
        if (deviceId.isNullOrBlank()) {
            val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            deviceId = if (!androidId.isNullOrBlank()) {
                "android_$androidId"
            } else {
                "android_${UUID.randomUUID().toString().take(12)}"
            }
            prefs.edit().putString(KEY_DEVICE_ID, deviceId).apply()
        }
        return deviceId
    }

    private fun saveCachedToken(context: Context, token: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_LAST_TOKEN, token).apply()
    }
}
