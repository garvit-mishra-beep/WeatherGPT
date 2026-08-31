package com.weathergpt.core.config

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BackendUrlValidatorTest {

    @Test
    fun `debug - localhost and loopback are valid`() {
        val res1 = BackendUrlValidator.validateBackendUrl("http://127.0.0.1:8000", isDebug = true)
        assertTrue(res1 is ValidationResult.Success)
        assertEquals("http://127.0.0.1:8000/", (res1 as ValidationResult.Success).normalizedUrl)

        val res2 = BackendUrlValidator.validateBackendUrl("http://localhost:8000/", isDebug = true)
        assertTrue(res2 is ValidationResult.Success)
        assertEquals("http://localhost:8000/", (res2 as ValidationResult.Success).normalizedUrl)

        val res3 = BackendUrlValidator.validateBackendUrl("http://10.0.2.2:8000", isDebug = true)
        assertTrue(res3 is ValidationResult.Success)
        assertEquals("http://10.0.2.2:8000/", (res3 as ValidationResult.Success).normalizedUrl)
    }

    @Test
    fun `debug - private LAN IP endpoints are valid`() {
        val res1 = BackendUrlValidator.validateBackendUrl("http://192.168.1.105:8000", isDebug = true)
        assertTrue(res1 is ValidationResult.Success)
        assertEquals("http://192.168.1.105:8000/", (res1 as ValidationResult.Success).normalizedUrl)

        val res2 = BackendUrlValidator.validateBackendUrl("http://172.31.10.5:8000/", isDebug = true)
        assertTrue(res2 is ValidationResult.Success)
        assertEquals("http://172.31.10.5:8000/", (res2 as ValidationResult.Success).normalizedUrl)

        val res3 = BackendUrlValidator.validateBackendUrl("http://10.1.2.3:8000", isDebug = true)
        assertTrue(res3 is ValidationResult.Success)
        assertEquals("http://10.1.2.3:8000/", (res3 as ValidationResult.Success).normalizedUrl)
    }

    @Test
    fun `debug - missing scheme returns error`() {
        val res = BackendUrlValidator.validateBackendUrl("192.168.1.50:8000", isDebug = true)
        assertTrue(res is ValidationResult.Error)
        assertTrue((res as ValidationResult.Error).message.contains("Missing scheme"))
    }

    @Test
    fun `debug - invalid scheme returns error`() {
        val res = BackendUrlValidator.validateBackendUrl("ftp://192.168.1.50:8000", isDebug = true)
        assertTrue(res is ValidationResult.Error)
        assertTrue((res as ValidationResult.Error).message.contains("must start with http:// or https://"))
    }

    @Test
    fun `debug - invalid port returns error`() {
        val res1 = BackendUrlValidator.validateBackendUrl("http://192.168.1.50:70000", isDebug = true)
        assertTrue(res1 is ValidationResult.Error)

        val res2 = BackendUrlValidator.validateBackendUrl("http://192.168.1.50:0", isDebug = true)
        assertTrue(res2 is ValidationResult.Error)
    }

    @Test
    fun `debug - empty or blank URL returns error`() {
        val res1 = BackendUrlValidator.validateBackendUrl("", isDebug = true)
        assertTrue(res1 is ValidationResult.Error)

        val res2 = BackendUrlValidator.validateBackendUrl("   ", isDebug = true)
        assertTrue(res2 is ValidationResult.Error)
    }

    @Test
    fun `release - strictly forbids local HTTP and private LAN IPs`() {
        val res1 = BackendUrlValidator.validateBackendUrl("http://127.0.0.1:8000/", isDebug = false)
        assertTrue(res1 is ValidationResult.Error)
        assertEquals("Release builds strictly require HTTPS", (res1 as ValidationResult.Error).message)

        val res2 = BackendUrlValidator.validateBackendUrl("http://192.168.1.50:8000/", isDebug = false)
        assertTrue(res2 is ValidationResult.Error)

        val res3 = BackendUrlValidator.validateBackendUrl("https://192.168.1.50:8000/", isDebug = false)
        assertTrue(res3 is ValidationResult.Error)
        assertTrue((res3 as ValidationResult.Error).message.contains("Local/private IP addresses are forbidden"))

        val res4 = BackendUrlValidator.validateBackendUrl("https://127.0.0.1:8000/", isDebug = false)
        assertTrue(res4 is ValidationResult.Error)

        val res5 = BackendUrlValidator.validateBackendUrl("https://localhost:8000/", isDebug = false)
        assertTrue(res5 is ValidationResult.Error)
    }

    @Test
    fun `release - permits strictly configured production HTTPS endpoint`() {
        val res = BackendUrlValidator.validateBackendUrl("https://api.weathergpt.in/", isDebug = false)
        assertTrue(res is ValidationResult.Success)
        assertEquals("https://api.weathergpt.in/", (res as ValidationResult.Success).normalizedUrl)
    }

    @Test
    fun `qr code payload parsing validates correctly`() {
        val valid = BackendUrlValidator.parseQrCodePayload("http://192.168.1.200:8000/", isDebug = true)
        assertTrue(valid is ValidationResult.Success)
        assertEquals("http://192.168.1.200:8000/", (valid as ValidationResult.Success).normalizedUrl)

        val empty = BackendUrlValidator.parseQrCodePayload("", isDebug = true)
        assertTrue(empty is ValidationResult.Error)
    }
}
