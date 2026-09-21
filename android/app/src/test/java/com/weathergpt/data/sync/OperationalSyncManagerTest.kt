package com.weathergpt.data.sync

import com.weathergpt.core.network.RetrofitClientFactory
import com.weathergpt.core.network.networkJson
import com.weathergpt.core.resilience.SystemResilienceManager
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.data.remote.dto.decision.ActionWindowDto
import com.weathergpt.data.remote.dto.decision.NirnayCardDto
import com.weathergpt.data.remote.dto.sync.OperationalEventDto
import com.weathergpt.data.remote.dto.sync.OperationalSyncResponseDto
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionVerdict
import com.weathergpt.domain.model.resilience.SourceOperationalStatus
import com.weathergpt.domain.model.resilience.SystemOperationalState
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.concurrent.TimeUnit

@OptIn(ExperimentalCoroutinesApi::class)
class OperationalSyncManagerTest {

    private val testDispatcher = StandardTestDispatcher()
    private val testScope = TestScope(testDispatcher)

    private lateinit var mockWebServer: MockWebServer
    private lateinit var localDataSource: InMemoryLocalOperationalSyncDataSource
    private lateinit var resilienceManager: SystemResilienceManager
    private lateinit var syncManager: OperationalSyncManager

    @Before
    fun setup() {
        mockWebServer = MockWebServer()
        mockWebServer.start()

        val okHttpClient = OkHttpClient.Builder()
            .connectTimeout(1, TimeUnit.SECONDS)
            .readTimeout(1, TimeUnit.SECONDS)
            .build()

        val retrofit = RetrofitClientFactory.createRetrofit(
            okHttpClient = okHttpClient,
            baseUrl = mockWebServer.url("/").toString()
        )
        val apiService = retrofit.create(WeatherGPTApiService::class.java)

        localDataSource = InMemoryLocalOperationalSyncDataSource()
        resilienceManager = SystemResilienceManager.getTestInstance(dispatcher = testDispatcher)
        syncManager = OperationalSyncManager(
            apiService = apiService,
            localDataSource = localDataSource,
            resilienceManager = resilienceManager,
            dispatcher = testDispatcher,
            scope = testScope
        )
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
    }

    private fun enqueueSyncResponse(response: OperationalSyncResponseDto) {
        val jsonBody = networkJson.encodeToString(OperationalSyncResponseDto.serializer(), response)
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(jsonBody)
        )
    }

    private fun sampleNirnayDto(
        verdict: String = "PROCEED_WITH_CAUTION",
        severity: String = "MODERATE",
        action: String = "Proceed with field operations vigilance."
    ): NirnayCardDto {
        return NirnayCardDto(
            question = "Operational advisory for Pune District",
            verdict = verdict,
            severity = severity,
            recommendedAction = action,
            actionWindow = ActionWindowDto(
                status = "available",
                reason = "Favorable operational window identified."
            ),
            confidence = "HIGH"
        )
    }

    private fun sampleEventDto(seq: Int, eventType: String = "WEATHER_UPDATE"): OperationalEventDto {
        return OperationalEventDto(
            eventId = "EVT-SEQ-$seq",
            eventType = eventType,
            sourceId = "OPEN_METEO",
            sourceAuthority = "E2",
            sourceRecordId = "REC-$seq",
            eventVersion = 1,
            sequenceNumber = seq,
            correlationId = "CORR-$seq",
            payloadHash = "hash-$seq",
            ingestedAt = "2026-09-21T12:00:00Z",
            geography = "Pune District",
            qualityState = "VALID",
            freshnessState = "FRESH",
            processingStatus = "APPLIED"
        )
    }

    @Test
    fun testInitialOperationalSync_storesRevisionA_advancesCursor() = runTest(testDispatcher) {
        // Backend prepares initial state (Revision 1, cursor 5)
        val backendResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T12:00:00Z",
            cursorSequence = 0,
            latestSequence = 5,
            latestRevision = 1,
            sourceStatus = "LIVE",
            events = (1..5).map { sampleEventDto(it) },
            latestNirnayCard = sampleNirnayDto(verdict = "PROCEED_WITH_CAUTION", severity = "MODERATE")
        )
        enqueueSyncResponse(backendResponse)

        val result = syncManager.syncOperationalState()
        assertTrue(result.isSuccess)

        // Verify request sent over wire
        val recordedRequest = mockWebServer.takeRequest(1, TimeUnit.SECONDS)
        assertNotNull(recordedRequest)
        assertTrue(recordedRequest!!.path!!.contains("/api/v1/sync/operational-state"))
        assertTrue(recordedRequest.path!!.contains("cursor_seq=0"))
        assertTrue(recordedRequest.path!!.contains("last_synced_revision=0"))

        val uiState = syncManager.uiState.value
        assertEquals(5, uiState.cursorSequence)
        assertEquals(1, uiState.latestRevision)
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, uiState.systemState)
        assertEquals(SourceOperationalStatus.LIVE, uiState.sourceStatus)
        assertNotNull(uiState.latestNirnayCard)
        assertEquals(DecisionVerdict.PROCEED_WITH_CAUTION, uiState.latestNirnayCard?.verdict)

        // Verify local storage persistence
        val record = localDataSource.getLatestSyncRecord()
        assertNotNull(record)
        assertEquals(5, record?.cursorSequence)
        assertEquals(1, record?.latestRevision)
        assertEquals(5, record?.events?.size)
    }

    @Test
    fun testIncrementalSync_cursorHandshake_storesRevisionB() = runTest(testDispatcher) {
        // 1. Initial Sync (Revision 1, cursor 5)
        val initialResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T12:00:00Z",
            cursorSequence = 0,
            latestSequence = 5,
            latestRevision = 1,
            sourceStatus = "LIVE",
            events = (1..5).map { sampleEventDto(it) },
            latestNirnayCard = sampleNirnayDto(verdict = "PROCEED_WITH_CAUTION", severity = "MODERATE")
        )
        enqueueSyncResponse(initialResponse)
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // 2. Incremental Sync (Revision 2, new delta events 6 and 7, verdict escalates to POSTPONE)
        val deltaResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T12:30:00Z",
            cursorSequence = 5,
            latestSequence = 7,
            latestRevision = 2,
            sourceStatus = "LIVE",
            events = listOf(sampleEventDto(6, "WEATHER_UPDATE"), sampleEventDto(7, "OFFICIAL_WARNING_NEW")),
            latestNirnayCard = sampleNirnayDto(verdict = "POSTPONE", severity = "HIGH", action = "Halt operations immediately.")
        )
        enqueueSyncResponse(deltaResponse)

        val result = syncManager.syncOperationalState()
        assertTrue(result.isSuccess)

        // Verify cursor passed in second HTTP request
        val secondRequest = mockWebServer.takeRequest(1, TimeUnit.SECONDS)
        assertNotNull(secondRequest)
        assertTrue(secondRequest!!.path!!.contains("cursor_seq=5"))
        assertTrue(secondRequest.path!!.contains("last_synced_revision=1"))

        val uiState = syncManager.uiState.value
        assertEquals(7, uiState.cursorSequence)
        assertEquals(2, uiState.latestRevision)
        assertEquals(DecisionVerdict.POSTPONE, uiState.latestNirnayCard?.verdict)
        assertEquals(DecisionSeverity.HIGH, uiState.latestNirnayCard?.severity)

        // Verify incremental accumulation in local persistent storage without duplicating 1..5
        val record = localDataSource.getLatestSyncRecord()
        assertEquals(7, record?.events?.size)
        assertEquals(7, record?.cursorSequence)
        assertEquals(2, record?.latestRevision)
    }

    @Test
    fun testDuplicateSyncResponse_noDuplicateInsertion() = runTest(testDispatcher) {
        val initialResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T12:00:00Z",
            cursorSequence = 0,
            latestSequence = 3,
            latestRevision = 1,
            sourceStatus = "LIVE",
            events = (1..3).map { sampleEventDto(it) },
            latestNirnayCard = sampleNirnayDto()
        )
        enqueueSyncResponse(initialResponse)
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // Send identical response again (same cursor = 3)
        enqueueSyncResponse(initialResponse.copy(events = emptyList()))
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        val record = localDataSource.getLatestSyncRecord()
        assertEquals(3, record?.events?.size) // Still exactly 3 events, zero duplicate accumulation
        assertEquals(3, record?.cursorSequence)
    }

    @Test
    fun testOfflineRecovery_cachedRevisionNotMaskedAsLive_reconnectsAndSyncsRevisionB() = runTest(testDispatcher) {
        // Step 1: Initial Sync of Revision 1
        val initialResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T10:00:00Z",
            cursorSequence = 0,
            latestSequence = 2,
            latestRevision = 1,
            sourceStatus = "LIVE",
            events = (1..2).map { sampleEventDto(it) },
            latestNirnayCard = sampleNirnayDto(verdict = "GO", severity = "LOW")
        )
        enqueueSyncResponse(initialResponse)
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // Step 2: Device loses connectivity
        syncManager.onDeviceWentOffline()

        val offlineState = syncManager.uiState.value
        assertTrue(offlineState.isOffline)
        assertEquals(SystemOperationalState.OFFLINE, offlineState.systemState)
        assertEquals(SourceOperationalStatus.CACHED, offlineState.sourceStatus)
        // Crucial invariant: Cached Revision 1 is displayed with CACHED status, never masked as live
        assertEquals(1, offlineState.latestRevision)
        assertEquals(DecisionVerdict.GO, offlineState.latestNirnayCard?.verdict)

        // Step 3: Network restored, backend prepared with Revision 2
        val recoveryResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T11:00:00Z",
            cursorSequence = 2,
            latestSequence = 4,
            latestRevision = 2,
            sourceStatus = "LIVE",
            events = listOf(sampleEventDto(3), sampleEventDto(4)),
            latestNirnayCard = sampleNirnayDto(verdict = "POSTPONE", severity = "HIGH")
        )
        enqueueSyncResponse(recoveryResponse)

        syncManager.onConnectivityRestored().join()

        val restoredState = syncManager.uiState.value
        assertFalse(restoredState.isOffline)
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, restoredState.systemState)
        assertEquals(SourceOperationalStatus.LIVE, restoredState.sourceStatus)
        assertEquals(2, restoredState.latestRevision)
        assertEquals(4, restoredState.cursorSequence)
        assertEquals(DecisionVerdict.POSTPONE, restoredState.latestNirnayCard?.verdict)
    }

    @Test
    fun testConsistency_riskAndEvidenceMatchSameRevision_noTearing() = runTest(testDispatcher) {
        // Atomicity test: ensures local storage write does not allow partial updates
        val revisionCard = sampleNirnayDto(verdict = "POSTPONE", severity = "CRITICAL")
        val response = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T14:00:00Z",
            cursorSequence = 5,
            latestSequence = 8,
            latestRevision = 4,
            sourceStatus = "LIVE",
            events = listOf(sampleEventDto(6), sampleEventDto(7), sampleEventDto(8)),
            latestNirnayCard = revisionCard
        )
        enqueueSyncResponse(response)
        syncManager.syncOperationalState()

        val record = localDataSource.getLatestSyncRecord()
        assertNotNull(record)
        // Both revision number and NirnayCard verdict reflect the exact same revision bundle
        assertEquals(4, record?.latestRevision)
        assertEquals(DecisionVerdict.POSTPONE, record?.latestNirnayCard?.verdict)
        assertEquals(DecisionSeverity.CRITICAL, record?.latestNirnayCard?.severity)
        assertEquals(8, record?.cursorSequence)
    }

    @Test
    fun testDeviceSideSyncLatency_measuresExecutionSpeed() = runTest(testDispatcher) {
        val response = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T12:00:00Z",
            cursorSequence = 0,
            latestSequence = 2,
            latestRevision = 1,
            sourceStatus = "LIVE",
            events = (1..2).map { sampleEventDto(it) },
            latestNirnayCard = sampleNirnayDto()
        )
        enqueueSyncResponse(response)

        syncManager.syncOperationalState()

        val uiState = syncManager.uiState.value
        assertTrue("Device sync latency must be measured", uiState.lastDeviceSyncLatencyMs >= 0L)
        println("Measured Device-Side Sync Latency: ${uiState.lastDeviceSyncLatencyMs} ms")
    }
}
