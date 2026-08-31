package com.weathergpt.core.network

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.IOException
import java.net.SocketTimeoutException

class RetryPolicyTest {

    @Test
    fun `idempotent call retries on transient network error and returns success`() = runTest {
        var attempts = 0

        val result = RetryPolicy.executeWithRetry(
            maxRetries = 2,
            initialDelayMs = 10L,
            maxDelayMs = 50L,
            isIdempotent = true
        ) {
            attempts++
            if (attempts == 1) {
                throw SocketTimeoutException("Read timeout on attempt 1")
            }
            "recovered_value"
        }

        assertEquals("recovered_value", result)
        assertEquals(2, attempts)
    }

    @Test
    fun `idempotent call exhausts max retries and throws last exception`() = runTest {
        var attempts = 0

        try {
            RetryPolicy.executeWithRetry(
                maxRetries = 2,
                initialDelayMs = 10L,
                maxDelayMs = 50L,
                isIdempotent = true
            ) {
                attempts++
                throw IOException("Persistent network outage")
            }
            fail("Expected IOException to be thrown")
        } catch (e: IOException) {
            assertEquals("Persistent network outage", e.message)
            assertEquals(3, attempts) // Initial attempt + 2 retries = 3
        }
    }

    @Test
    fun `non-idempotent call fails immediately on first error without retrying`() = runTest {
        var attempts = 0

        try {
            RetryPolicy.executeWithRetry(
                maxRetries = 3,
                initialDelayMs = 10L,
                maxDelayMs = 50L,
                isIdempotent = false // Non-idempotent (e.g. POST chat request)
            ) {
                attempts++
                throw IOException("Network error on POST")
            }
            fail("Expected IOException on non-idempotent call")
        } catch (e: IOException) {
            assertEquals(1, attempts) // Executed exactly once
        }
    }

    @Test
    fun `cancellation exception is rethrown immediately and never retried`() = runTest {
        var attempts = 0

        try {
            RetryPolicy.executeWithRetry(
                maxRetries = 3,
                initialDelayMs = 10L,
                isIdempotent = true
            ) {
                attempts++
                throw CancellationException("Job was cancelled")
            }
            fail("Expected CancellationException to rethrow")
        } catch (e: CancellationException) {
            assertEquals(1, attempts) // Stopped immediately without retries
        }
    }
}
