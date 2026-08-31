package com.weathergpt.core.network

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.conflate
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * Authoritative typed network connectivity state.
 */
sealed interface NetworkState {
    data object Available : NetworkState
    data object Unavailable : NetworkState

    val isOnline: Boolean
        get() = this is Available
}

/**
 * Clean abstraction for monitoring network connectivity across the application.
 */
interface NetworkMonitor {
    val networkState: Flow<NetworkState>
    val isOnline: Boolean
}

/**
 * Android platform implementation of [NetworkMonitor] using [ConnectivityManager.NetworkCallback].
 */
class ConnectivityNetworkMonitor(
    context: Context
) : NetworkMonitor {

    private val connectivityManager =
        context.applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager

    override val isOnline: Boolean
        get() {
            val cm = connectivityManager ?: return false
            val activeNetwork = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(activeNetwork) ?: return false
            return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
        }

    override val networkState: Flow<NetworkState> = callbackFlow {
        val cm = connectivityManager
        if (cm == null) {
            trySend(NetworkState.Unavailable)
            close()
            return@callbackFlow
        }

        val callback = object : ConnectivityManager.NetworkCallback() {
            private val networks = mutableSetOf<Network>()

            override fun onAvailable(network: Network) {
                networks += network
                trySend(NetworkState.Available)
            }

            override fun onLost(network: Network) {
                networks -= network
                trySend(if (networks.isNotEmpty()) NetworkState.Available else NetworkState.Unavailable)
            }

            override fun onCapabilitiesChanged(
                network: Network,
                networkCapabilities: NetworkCapabilities
            ) {
                val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                if (hasInternet) {
                    networks += network
                    trySend(NetworkState.Available)
                } else {
                    networks -= network
                    trySend(if (networks.isNotEmpty()) NetworkState.Available else NetworkState.Unavailable)
                }
            }
        }

        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        cm.registerNetworkCallback(request, callback)

        // Send initial state immediately
        trySend(if (isOnline) NetworkState.Available else NetworkState.Unavailable)

        awaitClose {
            try {
                cm.unregisterNetworkCallback(callback)
            } catch (_: Exception) {
                // Ignore if already unregistered on shutdown
            }
        }
    }.distinctUntilChanged().conflate()
}
