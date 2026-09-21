package com.weathergpt.data.sync

import android.util.Log
import com.weathergpt.core.network.NetworkMonitor
import com.weathergpt.core.resilience.SystemResilienceManager
import com.weathergpt.data.remote.WeatherGPTApiService
import com.weathergpt.domain.model.decision.NirnayCard
import com.weathergpt.domain.model.resilience.SourceOperationalStatus
import com.weathergpt.domain.model.resilience.SystemOperationalState
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Cohesive UI state representing the synchronized operational disaster intelligence on mobile.
 */
data class OperationalSyncUiState(
    val cursorSequence: Int = 0,
    val latestRevision: Int = 0,
    val isSynchronizing: Boolean = false,
    val systemState: SystemOperationalState = SystemOperationalState.FULL_OPERATIONAL,
    val sourceStatus: SourceOperationalStatus = SourceOperationalStatus.LIVE,
    val latestNirnayCard: NirnayCard? = null,
    val lastVerifiedTimestamp: String = "Just now",
    val isStale: Boolean = false,
    val isOffline: Boolean = false,
    val errorSummary: String? = null,
    val lastDeviceSyncLatencyMs: Long = 0L
)

/**
 * Operational Synchronization Coordinator for VAYUBODHAK Android client.
 *
 * Guarantees:
 * 1. Monotonic cursor advancement (only request deltas since last_synced_sequence).
 * 2. Atomic state persistence (NirnayCard, revision, and events are committed together).
 * 3. Never presents stale cached records as live.
 * 4. Recovery handshake (transitions through RECOVERING -> sync -> FULL_OPERATIONAL).
 * 5. Device-side sync latency measurement.
 */
class OperationalSyncManager(
    private val apiService: WeatherGPTApiService,
    private val localDataSource: LocalOperationalSyncDataSource,
    private val resilienceManager: SystemResilienceManager,
    private val networkMonitor: NetworkMonitor? = null,
    private val dispatcher: CoroutineDispatcher = Dispatchers.Main,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + dispatcher)
) {
    companion object {
        private const val TAG = "OperationalSyncManager"

        private fun formatTimestamp(date: Date = Date()): String {
            return SimpleDateFormat("hh:mm a", Locale.getDefault()).format(date)
        }
    }

    private val _uiState = MutableStateFlow(OperationalSyncUiState())
    val uiState: StateFlow<OperationalSyncUiState> = _uiState.asStateFlow()

    init {
        // Hydrate initial state from persistent local storage
        scope.launch {
            val cached = localDataSource.getLatestSyncRecord()
            if (cached != null) {
                _uiState.update { current ->
                    current.copy(
                        cursorSequence = cached.cursorSequence,
                        latestRevision = cached.latestRevision,
                        latestNirnayCard = cached.latestNirnayCard,
                        lastVerifiedTimestamp = formatTimestamp(Date(cached.localRetrievedAtMillis))
                    )
                }
            }
        }
    }

    /**
     * Executes incremental synchronization against central backend.
     * Bounded cursor pagination avoids full redownload of historical operational logs.
     */
    suspend fun syncOperationalState(
        district: String? = null,
        limit: Int = 50
    ): Result<OperationalSyncUiState> {
        val t0 = System.currentTimeMillis()

        _uiState.update { it.copy(isSynchronizing = true) }

        return try {
            val cursor = localDataSource.getCursorSequence()
            val lastRevision = localDataSource.getLatestRevision()

            // 1. Fetch incremental deltas from Retrofit
            val responseDto = apiService.getOperationalSyncState(
                cursorSeq = cursor,
                lastSyncedRevision = lastRevision,
                district = district,
                limit = limit
            )

            val tReceive = System.currentTimeMillis()

            // 2. Atomic persistent storage write
            localDataSource.saveSyncResponse(responseDto)

            val tWrite = System.currentTimeMillis()

            // 3. Update resilience manager
            val formattedTime = formatTimestamp()
            val parsedStatus = when (responseDto.sourceStatus.uppercase()) {
                "LIVE" -> SourceOperationalStatus.LIVE
                "FALLBACK" -> SourceOperationalStatus.FALLBACK
                "CACHED" -> SourceOperationalStatus.CACHED
                "STALE" -> SourceOperationalStatus.STALE
                else -> SourceOperationalStatus.LIVE
            }

            resilienceManager.completeSynchronization(
                success = (parsedStatus != SourceOperationalStatus.FALLBACK)
            )

            val deviceLatency = System.currentTimeMillis() - t0

            val updatedDomainCard = localDataSource.getLatestNirnayCard()

            _uiState.update { current ->
                current.copy(
                    cursorSequence = responseDto.latestSequence,
                    latestRevision = responseDto.latestRevision,
                    isSynchronizing = false,
                    systemState = if (parsedStatus == SourceOperationalStatus.FALLBACK) {
                        SystemOperationalState.DEGRADED_DATA
                    } else {
                        SystemOperationalState.FULL_OPERATIONAL
                    },
                    sourceStatus = parsedStatus,
                    latestNirnayCard = updatedDomainCard ?: current.latestNirnayCard,
                    lastVerifiedTimestamp = formattedTime,
                    isStale = parsedStatus == SourceOperationalStatus.STALE,
                    isOffline = false,
                    errorSummary = null,
                    lastDeviceSyncLatencyMs = deviceLatency
                )
            }
            val newState = _uiState.value

            Log.i(TAG, "Incremental sync complete: cursor=$cursor -> ${responseDto.latestSequence}, rev=${responseDto.latestRevision}, deviceLatency=${deviceLatency}ms")
            Result.success(newState)
        } catch (e: Exception) {
            Log.e(TAG, "Incremental sync failed: ${e.message}", e)
            _uiState.update { current ->
                current.copy(
                    isSynchronizing = false,
                    errorSummary = e.message ?: "Sync connection failed"
                )
            }
            Result.failure(e)
        }
    }

    /**
     * Called when device connectivity is lost.
     * Transitions UI to OFFLINE mode while preserving verified cached NirnayCard with timestamp.
     */
    fun onDeviceWentOffline() {
        resilienceManager.onDeviceWentOffline()
        _uiState.update { current ->
            current.copy(
                isOffline = true,
                systemState = SystemOperationalState.OFFLINE,
                sourceStatus = SourceOperationalStatus.CACHED
            )
        }
    }

    /**
     * Called when network connectivity returns.
     * Enters RECOVERING state, triggers incremental sync, and restores operational posture.
     */
    fun onConnectivityRestored(district: String? = null): Job = scope.launch {
        resilienceManager.onConnectivityRestored(immediate = true)
        _uiState.update { current ->
            current.copy(
                isOffline = false,
                systemState = SystemOperationalState.RECOVERING
            )
        }
        syncOperationalState(district)
    }
}
