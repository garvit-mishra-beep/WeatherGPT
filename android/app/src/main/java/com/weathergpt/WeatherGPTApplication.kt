package com.weathergpt

import android.app.Application
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
    }
}
