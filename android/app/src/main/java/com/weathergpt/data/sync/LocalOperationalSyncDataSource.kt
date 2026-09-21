package com.weathergpt.data.sync

import com.weathergpt.data.mapper.Mappers.toDomain
import com.weathergpt.data.remote.dto.sync.OperationalEventDto
import com.weathergpt.data.remote.dto.sync.OperationalSyncResponseDto
import com.weathergpt.domain.model.decision.NirnayCard
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.concurrent.ConcurrentHashMap

/**
 * Domain representation of locally cached operational synchronization state.
 */
data class OperationalSyncRecord(
    val cursorSequence: Int,
    val latestRevision: Int,
    val sourceStatus: String,
    val serverTimeIso: String,
    val localRetrievedAtMillis: Long,
    val events: List<OperationalEventDto>,
    val latestNirnayCard: NirnayCard?
)

/**
 * Interface contract for persistent storage of operational synchronization state.
 * Guarantees atomic transaction boundaries to prevent "new risk + old evidence" state tearing.
 */
interface LocalOperationalSyncDataSource {
    suspend fun saveSyncResponse(response: OperationalSyncResponseDto)
    suspend fun getLatestSyncRecord(): OperationalSyncRecord?
    suspend fun getCursorSequence(): Int
    suspend fun getLatestRevision(): Int
    suspend fun getLatestNirnayCard(): NirnayCard?
    suspend fun clear()
}

/**
 * In-memory thread-safe implementation of [LocalOperationalSyncDataSource]
 * providing atomic transaction semantics for unit and integration tests.
 */
class InMemoryLocalOperationalSyncDataSource(
    private val timeProvider: () -> Long = { System.currentTimeMillis() }
) : LocalOperationalSyncDataSource {

    private val mutex = Mutex()
    private var currentRecord: OperationalSyncRecord? = null
    private val eventStore = ConcurrentHashMap<String, OperationalEventDto>()

    override suspend fun saveSyncResponse(response: OperationalSyncResponseDto) {
        mutex.withLock {
            // Atomic transaction: store events, update cursor, update revision, update NirnayCard simultaneously
            for (evt in response.events) {
                eventStore[evt.eventId] = evt
            }

            val domainCard = response.latestNirnayCard?.toDomain()

            currentRecord = OperationalSyncRecord(
                cursorSequence = response.latestSequence,
                latestRevision = response.latestRevision,
                sourceStatus = response.sourceStatus,
                serverTimeIso = response.serverTimeIso,
                localRetrievedAtMillis = timeProvider(),
                events = eventStore.values.sortedBy { it.sequenceNumber ?: 0 },
                latestNirnayCard = domainCard ?: currentRecord?.latestNirnayCard
            )
        }
    }

    override suspend fun getLatestSyncRecord(): OperationalSyncRecord? {
        return mutex.withLock { currentRecord }
    }

    override suspend fun getCursorSequence(): Int {
        return mutex.withLock { currentRecord?.cursorSequence ?: 0 }
    }

    override suspend fun getLatestRevision(): Int {
        return mutex.withLock { currentRecord?.latestRevision ?: 0 }
    }

    override suspend fun getLatestNirnayCard(): NirnayCard? {
        return mutex.withLock { currentRecord?.latestNirnayCard }
    }

    override suspend fun clear() {
        mutex.withLock {
            currentRecord = null
            eventStore.clear()
        }
    }
}
