package com.weathergpt.data.remote.dto.sync

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import com.weathergpt.data.remote.dto.decision.NirnayCardDto

/**
 * DTO representing an operational data change event.
 */
@Serializable
data class OperationalEventDto(
    @SerialName("event_id")
    val eventId: String,
    @SerialName("event_type")
    val eventType: String,
    @SerialName("source_id")
    val sourceId: String,
    @SerialName("source_authority")
    val sourceAuthority: String = "E2",
    @SerialName("source_record_id")
    val sourceRecordId: String? = null,
    @SerialName("event_version")
    val eventVersion: Int = 1,
    @SerialName("sequence_number")
    val sequenceNumber: Int? = null,
    @SerialName("correlation_id")
    val correlationId: String,
    @SerialName("payload_hash")
    val payloadHash: String,
    @SerialName("published_at")
    val publishedAt: String? = null,
    @SerialName("observed_at")
    val observedAt: String? = null,
    @SerialName("ingested_at")
    val ingestedAt: String,
    @SerialName("valid_from")
    val validFrom: String? = null,
    @SerialName("valid_until")
    val validUntil: String? = null,
    @SerialName("geography")
    val geography: String = "ALL",
    @SerialName("quality_state")
    val qualityState: String = "VALID",
    @SerialName("freshness_state")
    val freshnessState: String = "FRESH",
    @SerialName("processing_status")
    val processingStatus: String = "RECEIVED"
)

/**
 * Cursor-based incremental synchronization bundle response from server.
 */
@Serializable
data class OperationalSyncResponseDto(
    @SerialName("server_time_iso")
    val serverTimeIso: String,
    @SerialName("cursor_sequence")
    val cursorSequence: Int,
    @SerialName("latest_sequence")
    val latestSequence: Int,
    @SerialName("latest_revision")
    val latestRevision: Int,
    @SerialName("source_status")
    val sourceStatus: String = "LIVE",
    @SerialName("events")
    val events: List<OperationalEventDto> = emptyList(),
    @SerialName("latest_nirnay_card")
    val latestNirnayCard: NirnayCardDto? = null,
    @SerialName("has_more")
    val hasMore: Boolean = false
)
