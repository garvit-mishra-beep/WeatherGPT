package com.weathergpt.di

import android.content.Context
import com.weathergpt.core.brain.SharedBrainManager
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.network.ConnectivityNetworkMonitor
import com.weathergpt.core.network.HttpClientFactory
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.RetrofitClientFactory
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.data.repository.WeatherGPTRepositoryImpl
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.domain.usecase.CheckHealthUseCase
import com.weathergpt.domain.usecase.CheckReadinessUseCase
import okhttp3.OkHttpClient
import retrofit2.Retrofit

/**
 * Standard lightweight composition root / Dependency Container for WeatherGPT Android.
 */
interface AppContainer {
    val okHttpClient: OkHttpClient
    val retrofit: Retrofit
    val apiService: WeatherGPTApiService
    val networkMonitor: NetworkMonitor
    val sharedLocationManager: SharedLocationManager
    val sharedBrainManager: SharedBrainManager
    val sharedSettingsManager: com.weathergpt.core.settings.SharedSettingsManager
    val localWeatherDataSource: com.weathergpt.data.local.LocalWeatherDataSource
    val repository: WeatherGPTRepository
    val checkHealthUseCase: CheckHealthUseCase
    val checkReadinessUseCase: CheckReadinessUseCase
}

/**
 * Default production/runtime implementation of [AppContainer].
 */
class DefaultAppContainer(
    context: Context
) : AppContainer {

    private val applicationContext = context.applicationContext

    override val networkMonitor: NetworkMonitor by lazy {
        ConnectivityNetworkMonitor(context = applicationContext)
    }

    override val sharedLocationManager: SharedLocationManager by lazy {
        SharedLocationManager(context = applicationContext)
    }

    override val sharedBrainManager: SharedBrainManager by lazy {
        SharedBrainManager(context = applicationContext)
    }

    override val sharedSettingsManager: com.weathergpt.core.settings.SharedSettingsManager by lazy {
        com.weathergpt.core.settings.SharedSettingsManager(context = applicationContext)
    }

    override val localWeatherDataSource: com.weathergpt.data.local.LocalWeatherDataSource by lazy {
        com.weathergpt.data.local.SQLiteLocalWeatherDataSource(context = applicationContext)
    }

    override val okHttpClient: OkHttpClient by lazy {
        HttpClientFactory.createOkHttpClient()
    }

    override val retrofit: Retrofit by lazy {
        RetrofitClientFactory.createRetrofit(okHttpClient = okHttpClient)
    }

    override val apiService: WeatherGPTApiService by lazy {
        retrofit.create(WeatherGPTApiService::class.java)
    }

    override val repository: WeatherGPTRepository by lazy {
        WeatherGPTRepositoryImpl(
            apiService = apiService,
            networkMonitor = networkMonitor,
            localWeatherDataSource = localWeatherDataSource,
            okHttpClient = okHttpClient
        )
    }

    override val checkHealthUseCase: CheckHealthUseCase by lazy {
        CheckHealthUseCase(repository = repository)
    }

    override val checkReadinessUseCase: CheckReadinessUseCase by lazy {
        CheckReadinessUseCase(repository = repository)
    }
}
