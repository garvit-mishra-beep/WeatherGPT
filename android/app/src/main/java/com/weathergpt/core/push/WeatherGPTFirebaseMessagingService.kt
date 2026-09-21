package com.weathergpt.core.push

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.weathergpt.R
import com.weathergpt.presentation.MainActivity

/**
 * Firebase Cloud Messaging receiver service for Vayubodhak proactive notifications.
 *
 * Adheres to Phase 9/11 push delivery architecture:
 * - Emits notifications to 'weathergpt_proactive_decisions' channel.
 * - Extracts event_id and decision metadata from data payload.
 * - Creates deep-link PendingIntent to MainActivity preserving event context.
 * - Never calculates or alters decision logic on the client.
 */
class WeatherGPTFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "WeatherGPTFCM"
        const val CHANNEL_ID = "weathergpt_proactive_decisions"
        const val EXTRA_EVENT_ID = "extra_event_id"
        const val EXTRA_SEVERITY = "extra_severity"
        const val EXTRA_EVENT_TYPE = "extra_event_type"
        const val EXTRA_ACTION = "extra_action"
        const val EXTRA_TARGET_SCREEN = "extra_target_screen"
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.i(TAG, "onNewToken: Token refreshed")
        PushTokenManager.onNewToken(applicationContext, token)
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        Log.d(TAG, "onMessageReceived from: ${remoteMessage.from}")

        val data = remoteMessage.data
        val eventId = data["event_id"] ?: ""
        val severity = data["severity"] ?: "MEDIUM"
        val eventType = data["event_type"] ?: "weather_hazard"
        val action = data["action"] ?: ""

        val title = remoteMessage.notification?.title
            ?: data["title"]
            ?: "WeatherGPT Decision Alert"

        val body = remoteMessage.notification?.body
            ?: data["body"]
            ?: "New proactive weather advisory available."

        showNotification(
            title = title,
            body = body,
            eventId = eventId,
            severity = severity,
            eventType = eventType,
            action = action
        )
    }

    private fun showNotification(
        title: String,
        body: String,
        eventId: String,
        severity: String,
        eventType: String,
        action: String
    ) {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(EXTRA_EVENT_ID, eventId)
            putExtra(EXTRA_SEVERITY, severity)
            putExtra(EXTRA_EVENT_TYPE, eventType)
            putExtra(EXTRA_ACTION, action)
            putExtra(EXTRA_TARGET_SCREEN, if (severity.equals("CRITICAL", ignoreCase = true)) "alerts" else "farmer")
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            eventId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notificationBuilder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(
                if (severity.equals("CRITICAL", ignoreCase = true) || severity.equals("HIGH", ignoreCase = true)) {
                    NotificationCompat.PRIORITY_HIGH
                } else {
                    NotificationCompat.PRIORITY_DEFAULT
                }
            )
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)

        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
        val notificationId = if (eventId.isNotBlank()) eventId.hashCode() else System.currentTimeMillis().toInt()
        notificationManager?.notify(notificationId, notificationBuilder.build())
    }
}
