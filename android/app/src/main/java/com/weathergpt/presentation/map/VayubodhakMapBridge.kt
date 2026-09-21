package com.weathergpt.presentation.map

import android.webkit.JavascriptInterface

/**
 * Android-JS Bridge interface facilitating bidirectional communication between the
 * Leaflet web map canvas and Vayubodhak's native Jetpack Compose architecture and SharedLocationManager.
 */
class VayubodhakMapBridge(
    private val onLocationSelectedCallback: (lat: Double, lon: Double, label: String) -> Unit,
    private val onHistoryRequestedCallback: ((lat: Double, lon: Double, dateStr: String) -> Unit)? = null,
    private val onErrorCallback: ((errorType: String, message: String) -> Unit)? = null
) {

    @JavascriptInterface
    fun onLocationSelected(lat: Double, lon: Double, label: String) {
        onLocationSelectedCallback(lat, lon, label)
    }

    @JavascriptInterface
    fun onHistoryRequested(lat: Double, lon: Double, dateStr: String) {
        onHistoryRequestedCallback?.invoke(lat, lon, dateStr)
    }

    @JavascriptInterface
    fun onMapError(errorType: String, message: String) {
        onErrorCallback?.invoke(errorType, message)
    }
}
