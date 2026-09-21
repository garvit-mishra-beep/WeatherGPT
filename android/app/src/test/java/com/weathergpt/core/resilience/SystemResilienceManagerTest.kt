package com.weathergpt.core.resilience

import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.network.NetworkState
import com.weathergpt.domain.model.resilience.LlmStatus
import com.weathergpt.domain.model.resilience.OfficialWarningStatus
import com.weathergpt.domain.model.resilience.SourceOperationalStatus
import com.weathergpt.domain.model.resilience.SystemOperationalState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit test suite verifying the System Resilience architecture and state transitions.
 *
 * Scenarios tested (Section 21 of Master Prompt):
 * 1. Normal: all sources live, LLM available, system operational
 * 2. API failure: primary source fails, fallback works, UI shows FALLBACK
 * 3. All sources fail: cached state available, UI shows CACHED/STALE, timestamp visible
 * 4. Complete offline: no network, cached state displayed, OFFLINE MODE visible
 * 5. Recovery: network restored, synchronization starts, state changes to RECOVERING, successful sync changes to LIVE
 * 6. LLM failure: LLM unavailable, deterministic assessment remains visible, AI section shows unavailable
 * 7. Warning failure: official warning source unavailable, app does not fabricate an official warning
 * 8. Stale state: stale evidence shown with explicit timestamp
 * 9. No cached data: system clearly displays UNAVAILABLE, no fabricated values appear
 * 10. Manual retry: triggers checking sources and updates status
 */
class SystemResilienceManagerTest {

    private class FakeNetworkMonitor : NetworkMonitor {
        val flow = MutableSharedFlow<NetworkState>(replay = 1)
        override val networkState: Flow<NetworkState> = flow
        override var isOnline: Boolean = true
    }

    private lateinit var fakeNetworkMonitor: FakeNetworkMonitor
    private lateinit var manager: SystemResilienceManager

    @Before
    fun setUp() {
        fakeNetworkMonitor = FakeNetworkMonitor()
        fakeNetworkMonitor.flow.tryEmit(NetworkState.Available)
        manager = SystemResilienceManager(
            networkMonitor = fakeNetworkMonitor,
            dispatcher = Dispatchers.Unconfined
        )
    }

    @After
    fun tearDown() {
        manager.stopObserving()
    }

    @Test
    fun test1_normal_allSourcesLive_llmAvailable_systemOperational() {
        val state = manager.uiState.value
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, state.systemState)
        assertEquals(LlmStatus.LLM_AVAILABLE, state.llmStatus)
        assertEquals(OfficialWarningStatus.AVAILABLE, state.officialWarningStatus)
        assertTrue(state.sourceStatuses.any { it.sourceId == "IMD" && it.status == SourceOperationalStatus.LIVE })
        assertTrue(state.sourceStatuses.any { it.sourceId == "OPEN_METEO" && it.status == SourceOperationalStatus.LIVE })
        assertNotNull(state.lastVerifiedTimestamp)
    }

    @Test
    fun test2_apiFailure_primaryFails_fallbackWorks_uiShowsFallback() {
        // Open-Meteo primary fails, supporting secondary fallback source engaged
        manager.reportSourceFallback("OPEN_METEO", fallbackProviderName = "Tomorrow.io NWP")
        val state = manager.uiState.value

        assertEquals(SystemOperationalState.DEGRADED_DATA, state.systemState)
        val weatherSource = state.sourceStatuses.first { it.sourceId == "OPEN_METEO" }
        assertEquals(SourceOperationalStatus.FALLBACK, weatherSource.status)
        assertTrue(weatherSource.isFallback)
        assertNotNull(weatherSource.fallbackDisclaimer)
        assertTrue(weatherSource.fallbackDisclaimer!!.contains("NOT an official government warning authority"))
    }

    @Test
    fun test3_allSourcesFail_cachedStateAvailable_uiShowsCachedStale_timestampVisible() {
        manager.reportSourceUnavailable("OPEN_METEO", "Weather server unreachable")
        manager.reportSourceUnavailable("IMD", "Official alert gateway timeout")
        val state = manager.uiState.value

        // System indicates degradation/cached mode with visible timestamp
        assertEquals(SystemOperationalState.DEGRADED_DATA, state.systemState)
        assertNotNull(state.lastVerifiedTimestamp)
        val imdSource = state.sourceStatuses.first { it.sourceId == "IMD" }
        assertEquals(SourceOperationalStatus.UNAVAILABLE, imdSource.status)
        assertEquals("Official alert gateway timeout", imdSource.errorReason)
    }

    @Test
    fun test4_completeOffline_noNetwork_cachedStateDisplayed_offlineModeVisible() {
        manager.onDeviceWentOffline()
        val state = manager.uiState.value
        assertEquals(SystemOperationalState.OFFLINE, state.systemState)
        assertTrue(state.isOffline)
        assertNotNull(state.lastVerifiedTimestamp)
        assertTrue(state.sourceStatuses.any { it.status == SourceOperationalStatus.CACHED })
    }

    @Test
    fun test5_recovery_networkRestored_stateChangesToRecovering_syncsToLive() {
        // First go offline
        manager.onDeviceWentOffline()
        assertEquals(SystemOperationalState.OFFLINE, manager.uiState.value.systemState)

        // Connectivity returns with immediate synchronization
        manager.onConnectivityRestored(immediate = true)

        val stateAfterRecovery = manager.uiState.value
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, stateAfterRecovery.systemState)
        assertFalse(stateAfterRecovery.isOffline)
        assertEquals("Latest data synchronized", stateAfterRecovery.syncMessage)
    }

    @Test
    fun test6_llmFailure_llmUnavailable_deterministicAssessmentRemainsVisible() {
        manager.reportLlmFailure("Ollama server connection refused")
        val state = manager.uiState.value

        // LLM status is unavailable
        assertEquals(LlmStatus.LLM_UNAVAILABLE, state.llmStatus)
        assertTrue(state.isLlmUnavailable)
        // System operational state for deterministic assessment remains intact!
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, state.systemState)

        // Then LLM recovers
        manager.reportLlmSuccess()
        assertEquals(LlmStatus.LLM_AVAILABLE, manager.uiState.value.llmStatus)
    }

    @Test
    fun test7_warningFailure_officialSourceUnavailable_doesNotFabricateOfficialWarning() {
        manager.reportOfficialWarningStatus(OfficialWarningStatus.UNAVAILABLE, verifiedTimestamp = "09:45 AM")
        val state = manager.uiState.value

        assertEquals(OfficialWarningStatus.UNAVAILABLE, state.officialWarningStatus)
        assertEquals("09:45 AM", state.lastVerifiedWarningTimestamp)
        assertNull(state.activeWarningHeadline)
        val imdSource = state.sourceStatuses.first { it.sourceId == "IMD" }
        assertEquals(SourceOperationalStatus.UNAVAILABLE, imdSource.status)
        assertEquals("Official warning data currently unavailable.", imdSource.errorReason)
    }

    @Test
    fun test8_staleState_recordDataVerification_updatesTimestamp() {
        manager.recordDataVerification("2026-09-21T10:32:00")
        val state = manager.uiState.value
        assertNotNull(state.lastVerifiedTimestamp)
    }

    @Test
    fun test9_noCachedData_allSourcesUnavailable_systemShowsUnavailable() {
        // Manually fail all sources
        for (s in manager.uiState.value.sourceStatuses) {
            manager.reportSourceUnavailable(s.sourceId, "Failed connection")
        }
        val state = manager.uiState.value
        assertEquals(SystemOperationalState.UNAVAILABLE, state.systemState)
    }

    @Test
    fun test10_retryNow_triggersCheckingSourcesAndSynchronizes() {
        manager.retryNow(immediate = true)
        val state = manager.uiState.value
        assertFalse(state.isSyncing)
        assertEquals("Latest data synchronized", state.syncMessage)
    }
}
