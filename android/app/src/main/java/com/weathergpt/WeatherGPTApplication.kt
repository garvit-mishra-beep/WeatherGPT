package com.weathergpt

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.weathergpt.core.push.PushTokenManager
import com.weathergpt.core.push.WeatherGPTFirebaseMessagingService
import com.weathergpt.di.AppContainer
import com.weathergpt.di.DefaultAppContainer

/**
 * Android Application entrypoint holding the singleton dependency container.
 */
class WeatherGPTApplication : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        com.weathergpt.core.config.AppConfig.init(this)
        container = DefaultAppContainer(context = this)

        createNotificationChannels()
        PushTokenManager.init(context = this, api = container.apiService)
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                WeatherGPTFirebaseMessagingService.CHANNEL_ID,
                "Weather Decisions & Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Proactive agronomic and severe weather hazard decisions"
                enableLights(true)
                enableVibration(true)
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager?.createNotificationChannel(channel)
        }
    }
}
