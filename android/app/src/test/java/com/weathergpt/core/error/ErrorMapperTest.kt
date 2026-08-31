package com.weathergpt.core.error

import com.weathergpt.core.network.ErrorMapper
import kotlinx.coroutines.CancellationException
import okhttp3.Headers
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

class ErrorMapperTest {

    @Test
    fun `maps UnknownHostException to NetworkUnavailable`() {
        val exception = UnknownHostException("Unable to resolve host")
        val error = ErrorMapper.mapThrowable(exception)

        assertTrue(error is AppError.NetworkUnavailable)
    }

    @Test
    fun `maps ConnectException to NetworkUnavailable`() {
        val exception = ConnectException("Connection refused")
        val error = ErrorMapper.mapThrowable(exception)

        assertTrue(error is AppError.NetworkUnavailable)
    }

    @Test
    fun `maps SocketTimeoutException to Timeout`() {
        val exception = SocketTimeoutException("Read timed out")
        val error = ErrorMapper.mapThrowable(exception)

        assertTrue(error is AppError.Timeout)
    }

    @Test
    fun `maps 422 HttpException with RFC 7807 problem details to ValidationError`() {
        val problemJson = """
            {
                "type": "https://weathergpt.in/errors/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": "Latitude must be between 6.0 and 38.0",
                "instance": "/api/v1/weather/current",
                "request_id": "req-test-12345",
                "errors": ["lat: Value 45.0 is outside valid range"]
            }
        """.trimIndent()

        val responseBody = problemJson.toResponseBody("application/json".toMediaType())
        val response = Response.error<String>(422, responseBody)
        val exception = HttpException(response)

        val error = ErrorMapper.mapThrowable(exception)

        assertTrue(error is AppError.ValidationError)
        val validationError = error as AppError.ValidationError
        assertEquals(422, validationError.statusCode)
        assertEquals("req-test-12345", validationError.requestId)
        assertEquals("Latitude must be between 6.0 and 38.0", validationError.message)
        assertEquals(1, validationError.errors.size)
    }

    @Test
    fun `maps 429 HttpException with Retry-After header to RateLimited`() {
        val responseBody = "Too Many Requests".toResponseBody("text/plain".toMediaType())
        val headers = Headers.Builder()
            .add("Retry-After", "30")
            .add("x-request-id", "req-rate-limit-01")
            .build()
        val response = Response.error<String>(
            responseBody,
            okhttp3.Response.Builder()
                .code(429)
                .message("Too Many Requests")
                .protocol(okhttp3.Protocol.HTTP_1_1)
                .request(okhttp3.Request.Builder().url("https://api.weathergpt.in/api/v1/chat").build())
                .headers(headers)
                .build()
        )
        val exception = HttpException(response)

        val error = ErrorMapper.mapThrowable(exception)

        assertTrue(error is AppError.RateLimited)
        val rateLimitError = error as AppError.RateLimited
        assertEquals(429, rateLimitError.statusCode)
        assertEquals(30L, rateLimitError.retryAfterSeconds)
        assertEquals("req-rate-limit-01", rateLimitError.requestId)
        assertTrue(rateLimitError.message.contains("30 seconds"))
    }

    @Test
    fun `maps 503 HttpException to ServerUnavailable`() {
        val responseBody = "Service Unavailable".toResponseBody("text/plain".toMediaType())
        val response = Response.error<String>(503, responseBody)
        val exception = HttpException(response)

        val error = ErrorMapper.mapThrowable(exception)

        assertTrue(error is AppError.ServerUnavailable)
        val serverError = error as AppError.ServerUnavailable
        assertEquals(503, serverError.statusCode)
    }

    @Test
    fun `cancellation exception is rethrown directly by ErrorMapper`() {
        val cancellation = CancellationException("Coroutine was cancelled")
        try {
            ErrorMapper.mapThrowable(cancellation)
            fail("Expected CancellationException to be re-thrown")
        } catch (e: CancellationException) {
            assertEquals("Coroutine was cancelled", e.message)
        }
    }
}
