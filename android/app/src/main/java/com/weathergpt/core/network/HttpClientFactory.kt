package com.weathergpt.core.network

import com.weathergpt.core.config.AppConfig
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

/**
 * Factory constructing configured and hardened [OkHttpClient] instances.
 */
object HttpClientFactory {

    private val SENSITIVE_HEADERS = setOf(
        "authorization",
        "api-key",
        "cookie",
        "set-cookie",
        "x-api-key",
        "token"
    )

    /**
     * Interceptor that strips sensitive credentials from log outputs.
     */
    private val safeLoggingInterceptor = HttpLoggingInterceptor { message ->
        try {
            android.util.Log.d("WeatherGPT-Network", message)
        } catch (_: Throwable) {
            // JVM test environment fallback where android.util.Log is unmocked
        }
    }.apply {
        level = if (AppConfig.isLoggingEnabled) {
            HttpLoggingInterceptor.Level.HEADERS
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
        for (header in SENSITIVE_HEADERS) {
            redactHeader(header)
        }
    }

    /**
     * Interceptor ensuring standard HTTP headers are attached.
     */
    private val headersInterceptor = Interceptor { chain ->
        val original = chain.request()
        val request = original.newBuilder()
            .header("Accept", "application/json")
            .header("User-Agent", "WeatherGPT-Android/1.0.0")
            .build()
        chain.proceed(request)
    }

    /**
     * Interceptor rewriting host/port/scheme dynamically if AppConfig.apiBaseUrl is updated at runtime (Debug only).
     * Bypasses Ollama and explicit external requests so LAN LLM calls are never diverted to the local backend.
     */
    private val dynamicBaseUrlInterceptor = Interceptor { chain ->
        var request = chain.request()
        val originalUrl = request.url

        // Never rewrite Ollama requests (port 11434, /api/chat, /api/tags, or bypass header)
        if (originalUrl.port == 11434 ||
            originalUrl.encodedPath.startsWith("/api/chat") ||
            originalUrl.encodedPath.startsWith("/api/tags") ||
            request.header("X-Bypass-Dynamic-Base-Url") != null
        ) {
            return@Interceptor chain.proceed(request)
        }

        val currentBaseUrlStr = AppConfig.apiBaseUrl
        val currentBaseUrl = currentBaseUrlStr.toHttpUrlOrNull()
        if (currentBaseUrl != null) {
            val newUrl = request.url.newBuilder()
                .scheme(currentBaseUrl.scheme)
                .host(currentBaseUrl.host)
                .port(currentBaseUrl.port)
                .build()
            request = request.newBuilder().url(newUrl).build()
        }
        chain.proceed(request)
    }

    fun createOkHttpClient(): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .addInterceptor(DemoModeNetworkGuard.interceptor)
            .connectTimeout(AppConfig.CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .readTimeout(AppConfig.REQUEST_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .writeTimeout(AppConfig.REQUEST_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .callTimeout(45L, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .addInterceptor(dynamicBaseUrlInterceptor)
            .addInterceptor(headersInterceptor)

        if (AppConfig.isLoggingEnabled) {
            builder.addInterceptor(safeLoggingInterceptor)
        }

        return builder.build()
    }
}
