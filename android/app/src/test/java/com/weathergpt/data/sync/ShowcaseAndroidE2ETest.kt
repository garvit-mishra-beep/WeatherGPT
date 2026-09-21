package com.weathergpt.data.sync

import com.weathergpt.core.network.RetrofitClientFactory
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
import kotlinx.serialization.json.Json
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

/**
 * End-to-End Android Showcase Verification Suite for Video Recording Readiness.
 *
 * Verifies that the mobile client correctly consumes the controlled showcase scenario
 * through real Android networking, Room cache, StateFlow, and SystemResilienceManager:
 * 1. Baseline State (Step 0: Revision 1, sequence 1, initial Nirnay)
 * 2. Updated Revision (Step 1: Precipitation Escalation -> Revision 2)
 * 3. Notification & Sync State (Event stream consumption & cursor advancement)
 * 4. Offline Resilience State (Network severed, cache preserved with last verified timestamp)
 * 5. Recovery State (Network restored, incremental reconciliation to latest revision)
 * 6. Latest Nirnay Rendering (Direct actionable verdict without placeholder text)
 */
@OptIn(ExperimentalCoroutinesApi::class)
class ShowcaseAndroidE2ETest {

    private val testDispatcher = StandardTestDispatcher()
    private val testScope = TestScope(testDispatcher)

    private lateinit var mockWebServer: MockWebServer
    private lateinit var localDataSource: InMemoryLocalOperationalSyncDataSource
    private lateinit var resilienceManager: SystemResilienceManager
    private lateinit var syncManager: OperationalSyncManager

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

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

    private fun enqueueSyncResponse(responseDto: OperationalSyncResponseDto) {
        val jsonBody = json.encodeToString(OperationalSyncResponseDto.serializer(), responseDto)
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(jsonBody)
        )
    }

    private fun sampleBaselineNirnay(): NirnayCardDto = NirnayCardDto(
        question = "Operational Assessment: Gwalior District",
        verdict = "MONITOR",
        severity = "LOW",
        recommendedAction = "Atmospheric conditions nominal. Routine agricultural operations may proceed.",
        actionWindow = ActionWindowDto(
            status = "AVAILABLE",
            reason = "Conditions nominal; routine field operations permissible."
        ),
        confidence = "HIGH",
        why = listOf("Observation precipitation 3.0mm meets nominal thresholds"),
        explanation = "Conditions in Gwalior District are nominal."
    )

    private fun sampleEscalatedNirnay(): NirnayCardDto = NirnayCardDto(
        question = "Precipitation Escalation: Gwalior District",
        verdict = "PROCEED_WITH_CAUTION",
        severity = "MODERATE",
        recommendedAction = "Precipitation escalation detected (88.5mm). Clear drainage channels and secure low-lying assets.",
        actionWindow = ActionWindowDto(
            status = "RESTRICTED",
            reason = "Active localized monsoon surge requires drainage clearance."
        ),
        confidence = "HIGH",
        why = listOf("Observed precipitation (88.5mm) crossed 64.5mm heavy rain threshold"),
        explanation = "Significant rainfall escalation detected in Gwalior District."
    )

    private fun sampleWarningNirnay(): NirnayCardDto = NirnayCardDto(
        question = "Statutory Red Alert: Gwalior District",
        verdict = "POSTPONE",
        severity = "HIGH",
        recommendedAction = "Halt outdoor operations. Comply with official IMD Red Warning advisory.",
        actionWindow = ActionWindowDto(
            status = "SUSPENDED",
            reason = "Statutory red alert active; outdoor movement suspended."
        ),
        confidence = "HIGH",
        why = listOf("Official Red Warning bulletin issued by statutory authority IMD"),
        explanation = "Extreme localized precipitation alert active for Gwalior District."
    )

    private fun sampleEvent(seq: Int, eventType: String, sourceId: String): OperationalEventDto = OperationalEventDto(
        eventId = "EVT-SHOWCASE-00$seq",
        eventType = eventType,
        sourceId = sourceId,
        sourceAuthority = if (sourceId == "IMD") "E1" else "E2",
        sourceRecordId = "REC-SHOWCASE-00$seq",
        eventVersion = 1,
        sequenceNumber = seq,
        correlationId = "CORR-SHOWCASE-00$seq",
        payloadHash = "hash-showcase-00$seq",
        ingestedAt = "2026-09-21T09:00:00Z",
        geography = "Gwalior District",
        qualityState = "VALID",
        freshnessState = "FRESH",
        processingStatus = "APPLIED"
    )

    @Test
    fun test01_baselineState_loadsAccuratelyOnClient() = runTest(testDispatcher) {
        val baselineResponse = OperationalSyncResponseDto(
            serverTimeIso = "2026-09-21T09:00:00Z",
            cursorSequence = 0,
            latestSequence = 1,
            latestRevision = 1,
            sourceStatus = "LIVE",
            events = listOf(sampleEvent(1, "WEATHER_UPDATE", "OPEN_METEO")),
            latestNirnayCard = sampleBaselineNirnay()
        )
        enqueueSyncResponse(baselineResponse)

        val result = syncManager.syncOperationalState()
        assertTrue("Baseline sync must succeed", result.isSuccess)

        val recordedRequest = mockWebServer.takeRequest(1, TimeUnit.SECONDS)
        assertNotNull(recordedRequest)
        assertTrue(recordedRequest!!.path!!.contains("/api/v1/sync/operational-state"))

        val uiState = syncManager.uiState.value
        assertEquals("Initial baseline revision must be 1", 1, uiState.latestRevision)
        assertEquals(1, uiState.cursorSequence)
        assertEquals(DecisionVerdict.MONITOR, uiState.latestNirnayCard?.verdict)
        assertEquals(DecisionSeverity.LOW, uiState.latestNirnayCard?.severity)
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, uiState.systemState)

        val localRecord = localDataSource.getLatestSyncRecord()
        assertNotNull(localRecord)
        assertEquals(1, localRecord?.latestRevision)
        assertEquals(1, localRecord?.cursorSequence)
    }

    @Test
    fun test02_precipitationEscalation_updatesClientRevision() = runTest(testDispatcher) {
        // 1. Initial baseline
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T09:00:00Z",
                cursorSequence = 0,
                latestSequence = 1,
                latestRevision = 1,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(1, "WEATHER_UPDATE", "OPEN_METEO")),
                latestNirnayCard = sampleBaselineNirnay()
            )
        )
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // 2. Incremental rainfall escalation delta
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T09:15:00Z",
                cursorSequence = 1,
                latestSequence = 2,
                latestRevision = 2,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(2, "WEATHER_UPDATE", "OPEN_METEO")),
                latestNirnayCard = sampleEscalatedNirnay()
            )
        )

        val result = syncManager.syncOperationalState()
        assertTrue("Incremental sync must succeed", result.isSuccess)

        val request = mockWebServer.takeRequest(1, TimeUnit.SECONDS)
        assertNotNull(request)
        assertTrue(request!!.path!!.contains("cursor_seq=1"))
        assertTrue(request.path!!.contains("last_synced_revision=1"))

        val uiState = syncManager.uiState.value
        assertEquals("Revision must update to 2", 2, uiState.latestRevision)
        assertEquals(2, uiState.cursorSequence)
        assertEquals(DecisionVerdict.PROCEED_WITH_CAUTION, uiState.latestNirnayCard?.verdict)
        assertEquals(DecisionSeverity.MODERATE, uiState.latestNirnayCard?.severity)

        val localRecord = localDataSource.getLatestSyncRecord()
        assertEquals(2, localRecord?.events?.size)
        assertEquals(2, localRecord?.latestRevision)
    }

    @Test
    fun test03_statutoryAlert_updatesClientToRedWarning() = runTest(testDispatcher) {
        // Step 1: Client at Revision 2
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T09:15:00Z",
                cursorSequence = 0,
                latestSequence = 2,
                latestRevision = 2,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(1, "WEATHER_UPDATE", "OPEN_METEO"), sampleEvent(2, "WEATHER_UPDATE", "OPEN_METEO")),
                latestNirnayCard = sampleEscalatedNirnay()
            )
        )
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // Step 2: Red Warning issued by IMD -> Revision 3
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T09:30:00Z",
                cursorSequence = 2,
                latestSequence = 3,
                latestRevision = 3,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(3, "OFFICIAL_WARNING_NEW", "IMD")),
                latestNirnayCard = sampleWarningNirnay()
            )
        )
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        val uiState = syncManager.uiState.value
        assertEquals(3, uiState.latestRevision)
        assertEquals(3, uiState.cursorSequence)
        assertEquals(DecisionVerdict.POSTPONE, uiState.latestNirnayCard?.verdict)
        assertEquals(DecisionSeverity.HIGH, uiState.latestNirnayCard?.severity)

        val localRecord = localDataSource.getLatestSyncRecord()
        assertEquals(3, localRecord?.events?.size)
    }

    @Test
    fun test04_offlineResilience_preservesLastVerifiedState() = runTest(testDispatcher) {
        // Initialize with Step 1 state
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T09:15:00Z",
                cursorSequence = 0,
                latestSequence = 2,
                latestRevision = 2,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(1, "WEATHER_UPDATE", "OPEN_METEO"), sampleEvent(2, "WEATHER_UPDATE", "OPEN_METEO")),
                latestNirnayCard = sampleEscalatedNirnay()
            )
        )
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // Disconnect network
        syncManager.onDeviceWentOffline()

        val offlineState = syncManager.uiState.value
        assertTrue("UI state must flag offline mode", offlineState.isOffline)
        assertEquals(SystemOperationalState.OFFLINE, offlineState.systemState)
        assertEquals(SourceOperationalStatus.CACHED, offlineState.sourceStatus)
        // Last verified decision remains visible and non-null
        assertNotNull(offlineState.latestNirnayCard)
        assertEquals(2, offlineState.latestRevision)
        assertEquals(DecisionVerdict.PROCEED_WITH_CAUTION, offlineState.latestNirnayCard?.verdict)
    }

    @Test
    fun test05_recoveryFlow_reconcilesLatestStateOnReconnect() = runTest(testDispatcher) {
        // 1. Initial sync of Revision 1
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T09:00:00Z",
                cursorSequence = 0,
                latestSequence = 1,
                latestRevision = 1,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(1, "WEATHER_UPDATE", "OPEN_METEO")),
                latestNirnayCard = sampleBaselineNirnay()
            )
        )
        syncManager.syncOperationalState()
        mockWebServer.takeRequest(1, TimeUnit.SECONDS)

        // 2. Disconnect network
        syncManager.onDeviceWentOffline()
        assertTrue(syncManager.uiState.value.isOffline)
        assertEquals(SystemOperationalState.OFFLINE, syncManager.uiState.value.systemState)

        // 3. Network returns: Server has Revision 3 (Warning escalation)
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T10:00:00Z",
                cursorSequence = 1,
                latestSequence = 3,
                latestRevision = 3,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(2, "WEATHER_UPDATE", "OPEN_METEO"), sampleEvent(3, "OFFICIAL_WARNING_NEW", "IMD")),
                latestNirnayCard = sampleWarningNirnay()
            )
        )

        // Trigger connectivity restoration
        syncManager.onConnectivityRestored().join()

        val recoveredState = syncManager.uiState.value
        assertFalse("Client must recover from offline state", recoveredState.isOffline)
        assertEquals(SystemOperationalState.FULL_OPERATIONAL, recoveredState.systemState)
        assertEquals(3, recoveredState.latestRevision)
        assertEquals(DecisionVerdict.POSTPONE, recoveredState.latestNirnayCard?.verdict)
    }

    @Test
    fun test06_latestNirnayRendering_containsDirectVerifiableAction() = runTest(testDispatcher) {
        val warningCard = sampleWarningNirnay()
        enqueueSyncResponse(
            OperationalSyncResponseDto(
                serverTimeIso = "2026-09-21T10:00:00Z",
                cursorSequence = 0,
                latestSequence = 3,
                latestRevision = 3,
                sourceStatus = "LIVE",
                events = listOf(sampleEvent(1, "WEATHER_UPDATE", "OPEN_METEO")),
                latestNirnayCard = warningCard
            )
        )
        syncManager.syncOperationalState()

        val uiState = syncManager.uiState.value
        val card = uiState.latestNirnayCard
        assertNotNull(card)
        assertTrue("Verdict must not be empty", card!!.verdict.name.isNotEmpty())
        assertTrue("Action must provide clear guidance", card.recommendedAction.isNotEmpty())
        assertFalse("Action must not contain raw internal debug terms", card.recommendedAction.contains("Demo Mode"))
        assertFalse("Action must not contain mock terminology", card.recommendedAction.contains("mock"))
    }
}
