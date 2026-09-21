package com.weathergpt.presentation.status

import com.weathergpt.domain.model.resilience.LlmStatus
import com.weathergpt.domain.model.resilience.OfficialWarningStatus
import com.weathergpt.domain.model.resilience.ResilienceUiState
import com.weathergpt.domain.model.resilience.SourceHealthItem
import com.weathergpt.domain.model.resilience.SourceOperationalStatus
import com.weathergpt.domain.model.resilience.SystemOperationalState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit test verifying ResilienceUiState attributes, multi-attribute accessibility,
 * and fallback disclaimers.
 */
class SystemStatusUiStateTest {

    @Test
    fun test_systemOperationalState_symbolsAndLabels() {
        assertEquals("🟢", SystemOperationalState.FULL_OPERATIONAL.symbol)
        assertEquals("SYSTEM OPERATIONAL", SystemOperationalState.FULL_OPERATIONAL.label)

        assertEquals("🟡", SystemOperationalState.DEGRADED_DATA.symbol)
        assertEquals("DEGRADED MODE", SystemOperationalState.DEGRADED_DATA.label)

        assertEquals("🔴", SystemOperationalState.OFFLINE.symbol)
        assertEquals("OFFLINE MODE", SystemOperationalState.OFFLINE.label)

        assertEquals("🔵", SystemOperationalState.RECOVERING.symbol)
        assertEquals("RECOVERING", SystemOperationalState.RECOVERING.label)

        assertEquals("⚠️", SystemOperationalState.UNAVAILABLE.symbol)
        assertEquals("DATA UNAVAILABLE", SystemOperationalState.UNAVAILABLE.label)
    }

    @Test
    fun test_sourceOperationalStatus_properties() {
        assertTrue(SourceOperationalStatus.LIVE.isLive)
        assertFalse(SourceOperationalStatus.CACHED.isLive)
        assertTrue(SourceOperationalStatus.CACHED.isCachedOrStale)
        assertTrue(SourceOperationalStatus.STALE.isCachedOrStale)
        assertTrue(SourceOperationalStatus.HISTORICAL.isCachedOrStale)
    }

    @Test
    fun test_llmStatus_separationFromDeterministicAssessment() {
        val unavailable = LlmStatus.LLM_UNAVAILABLE
        assertFalse(unavailable.isAvailable)
        assertTrue(unavailable.description.contains("Verified disaster assessment remains available"))

        val available = LlmStatus.LLM_AVAILABLE
        assertTrue(available.isAvailable)
    }

    @Test
    fun test_officialWarningStatus_disclaimerIntegrity() {
        val imdItem = SourceHealthItem(
            sourceId = "IMD",
            sourceName = "India Meteorological Department",
            category = "Official Warning",
            authorityLevel = "E0 Statutory",
            status = SourceOperationalStatus.LIVE,
            lastVerifiedData = "10:30 AM"
        )
        assertEquals("E0 Statutory", imdItem.authorityLevel)
        assertFalse(imdItem.isFallback)

        val fallbackItem = SourceHealthItem(
            sourceId = "OPEN_METEO",
            sourceName = "Supporting NWP",
            category = "Weather",
            authorityLevel = "E2 Supporting",
            status = SourceOperationalStatus.FALLBACK,
            isFallback = true,
            fallbackDisclaimer = "Supporting provider is NOT an official government warning authority."
        )
        assertTrue(fallbackItem.isFallback)
        assertTrue(fallbackItem.fallbackDisclaimer!!.contains("NOT an official government warning authority"))
    }

    @Test
    fun test_resilienceUiState_convenienceFlags() {
        val offlineState = ResilienceUiState(systemState = SystemOperationalState.OFFLINE)
        assertTrue(offlineState.isOffline)
        assertFalse(offlineState.isDegraded)

        val degradedState = ResilienceUiState(systemState = SystemOperationalState.DEGRADED_DATA)
        assertTrue(degradedState.isDegraded)
        assertFalse(degradedState.isOffline)

        val recoveringState = ResilienceUiState(systemState = SystemOperationalState.RECOVERING)
        assertTrue(recoveringState.isRecovering)

        val llmDownState = ResilienceUiState(llmStatus = LlmStatus.LLM_UNAVAILABLE)
        assertTrue(llmDownState.isLlmUnavailable)
    }
}
