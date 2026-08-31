package com.weathergpt.core.network

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NetworkMonitorTest {

    private class FakeNetworkMonitor(
        initialState: NetworkState = NetworkState.Available
    ) : NetworkMonitor {
        private val _state = MutableStateFlow(initialState)
        override val networkState: Flow<NetworkState> = _state.asStateFlow()

        override val isOnline: Boolean
            get() = _state.value is NetworkState.Available

        fun setState(newState: NetworkState) {
            _state.value = newState
        }
    }

    @Test
    fun `initial available network state reflects isOnline true`() = runTest {
        val monitor = FakeNetworkMonitor(NetworkState.Available)
        assertTrue(monitor.isOnline)
    }

    @Test
    fun `unavailable network state reflects isOnline false`() = runTest {
        val monitor = FakeNetworkMonitor(NetworkState.Unavailable)
        assertFalse(monitor.isOnline)
    }

    @Test
    fun `network state transition updates online status correctly`() = runTest {
        val monitor = FakeNetworkMonitor(NetworkState.Available)
        assertTrue(monitor.isOnline)

        monitor.setState(NetworkState.Unavailable)
        assertFalse(monitor.isOnline)

        monitor.setState(NetworkState.Available)
        assertTrue(monitor.isOnline)
    }
}
