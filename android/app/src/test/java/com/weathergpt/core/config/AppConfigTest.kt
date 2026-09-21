package com.weathergpt.core.config

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppConfigTest {

    @After
    fun tearDown() {
        AppConfig.setCustomBaseUrl(null)
    }

    @Test
    fun `apiBaseUrl always ends with trailing slash`() {
        AppConfig.setCustomBaseUrl("http://localhost:8000")
        assertEquals("http://localhost:8000/", AppConfig.apiBaseUrl)

        AppConfig.setCustomBaseUrl("https://api.weathergpt.in")
        assertEquals("https://api.weathergpt.in/", AppConfig.apiBaseUrl)
    }

    @Test
    fun `custom base url can be configured dynamically`() {
        val testUrl = "http://192.168.1.50:8000"
        AppConfig.setCustomBaseUrl(testUrl)
        assertEquals("http://192.168.1.50:8000/", AppConfig.apiBaseUrl)
    }

    @Test
    fun `physical device debug url targets localhost adb reverse`() {
        AppConfig.usePhysicalDeviceDebug()
        assertEquals("http://127.0.0.1:8000/", AppConfig.apiBaseUrl)
        assertEquals(Environment.DEVELOPMENT, AppConfig.environment)
    }

    @Test
    fun `emulator debug url targets android emulator loopback`() {
        AppConfig.useEmulatorDebug()
        assertEquals("http://10.0.2.2:8000/", AppConfig.apiBaseUrl)
        assertEquals(Environment.DEVELOPMENT, AppConfig.environment)
    }

    @Test
    fun `staging url targets https staging endpoint`() {
        AppConfig.useStaging()
        assertEquals("https://staging-api.weathergpt.in/", AppConfig.apiBaseUrl)
        assertEquals(Environment.STAGING, AppConfig.environment)
    }

    @Test
    fun `production url targets https production endpoint`() {
        AppConfig.useProduction()
        assertEquals("https://api.weathergpt.in/", AppConfig.apiBaseUrl)
    }

    @Test
    fun `production URL does not contain local or development addresses`() {
        val prodUrl = AppConfig.PRODUCTION_URL
        assertFalse("Production URL must not contain 10.0.2.2", prodUrl.contains("10.0.2.2"))
        assertFalse("Production URL must not contain 127.0.0.1", prodUrl.contains("127.0.0.1"))
        assertFalse("Production URL must not contain localhost", prodUrl.contains("localhost"))
        assertFalse("Production URL must not contain 172.31.245.81", prodUrl.contains("172.31.245.81"))
        assertTrue("Production URL must use HTTPS", prodUrl.startsWith("https://"))
    }

    @Test
    fun `resetToDefault restores default physical debug url`() {
        AppConfig.setCustomBaseUrl("http://192.168.1.100:8000")
        assertEquals("http://192.168.1.100:8000/", AppConfig.apiBaseUrl)

        AppConfig.resetToDefault()
        assertEquals("http://127.0.0.1:8000/", AppConfig.apiBaseUrl)
    }

    @Test
    fun `demo hotspot targets laptop 1 mobile hotspot gateway`() {
        AppConfig.useDemoHotspot()
        assertEquals("http://192.168.137.1:8000/", AppConfig.apiBaseUrl)
        assertEquals("http://192.168.137.1:11434/", AppConfig.ollamaBaseUrl)
        assertEquals("192.168.137.1", AppConfig.DEMO_LAN_GATEWAY)
    }

    @Test
    fun `timeouts are set to sensible production defaults`() {
        assertTrue(AppConfig.REQUEST_TIMEOUT_SECONDS >= 15L)
        assertTrue(AppConfig.CONNECT_TIMEOUT_SECONDS >= 5L)
    }
}
