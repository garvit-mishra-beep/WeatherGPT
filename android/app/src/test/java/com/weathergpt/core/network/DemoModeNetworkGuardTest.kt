package com.weathergpt.core.network

import com.weathergpt.core.config.AppConfig
import okhttp3.OkHttpClient
import okhttp3.Request
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class DemoModeNetworkGuardTest {

    private val originalDemoMode = AppConfig.isDemoMode

    @Before
    fun setup() {
        DemoModeNetworkGuard.resetAuditCounters()
    }

    @After
    fun tearDown() {
        AppConfig.isDemoMode = originalDemoMode
        DemoModeNetworkGuard.resetAuditCounters()
    }

    @Test
    fun `when demo mode enabled, network is not permitted`() {
        AppConfig.isDemoMode = true
        assertFalse(DemoModeNetworkGuard.isNetworkPermitted)
    }

    @Test
    fun `when demo mode disabled, network is permitted`() {
        AppConfig.isDemoMode = false
        assertTrue(DemoModeNetworkGuard.isNetworkPermitted)
    }

    @Test
    fun `assertNetworkAllowed throws DemoModeNetworkException when demo mode is active`() {
        AppConfig.isDemoMode = true
        assertThrows(DemoModeNetworkException::class.java) {
            DemoModeNetworkGuard.assertNetworkAllowed("Unit test call")
        }
        assertEquals(1, DemoModeNetworkGuard.networkCallsAttempted)
        assertEquals(1, DemoModeNetworkGuard.networkCallsBlocked)
    }

    @Test
    fun `assertNetworkAllowed succeeds when demo mode is inactive`() {
        AppConfig.isDemoMode = false
        DemoModeNetworkGuard.assertNetworkAllowed("Unit test call")
        assertEquals(0, DemoModeNetworkGuard.networkCallsBlocked)
    }

    @Test
    fun `assertNoNetworkCalls verifies zero attempted calls`() {
        AppConfig.isDemoMode = true
        DemoModeNetworkGuard.assertNoNetworkCalls("Pre-check")
        assertEquals(0, DemoModeNetworkGuard.networkCallsAttempted)
    }

    @Test
    fun `auditNetworkCallAttempted records attempts and blocks in demo mode`() {
        AppConfig.isDemoMode = true
        DemoModeNetworkGuard.auditNetworkCallAttempted("Test Tag 1")
        DemoModeNetworkGuard.auditNetworkCallAttempted("Test Tag 2")

        assertEquals(2, DemoModeNetworkGuard.networkCallsAttempted)
        assertEquals(2, DemoModeNetworkGuard.networkCallsBlocked)
    }

    @Test
    fun `okhttp interceptor throws DemoModeNetworkException during demo mode`() {
        AppConfig.isDemoMode = true
        val client = OkHttpClient.Builder()
            .addInterceptor(DemoModeNetworkGuard.interceptor)
            .build()

        val request = Request.Builder()
            .url("https://api.open-meteo.com/v1/forecast?latitude=26.22&longitude=78.18")
            .build()

        assertThrows(DemoModeNetworkException::class.java) {
            client.newCall(request).execute()
        }

        assertTrue(DemoModeNetworkGuard.networkCallsBlocked > 0)
    }
}
