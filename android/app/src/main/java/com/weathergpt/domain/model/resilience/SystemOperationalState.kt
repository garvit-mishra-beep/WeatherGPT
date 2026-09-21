package com.weathergpt.domain.model.resilience

/**
 * High-level operational state of the entire VAYUBODHAK application.
 *
 * Guaranteed Invariants:
 * 1. Data availability can degrade without pretending the system has fresh data.
 * 2. LLM availability is strictly independent from deterministic disaster intelligence.
 * 3. Never hide data freshness or source failure.
 * 4. Never make cached information appear live.
 */
enum class SystemOperationalState(
    val label: String,
    val subtitle: String,
    val symbol: String
) {
    FULL_OPERATIONAL(
        label = "SYSTEM OPERATIONAL",
        subtitle = "Live data available",
        symbol = "🟢"
    ),
    DEGRADED_DATA(
        label = "DEGRADED MODE",
        subtitle = "Some live data unavailable",
        symbol = "🟡"
    ),
    OFFLINE(
        label = "OFFLINE MODE",
        subtitle = "Showing last verified information",
        symbol = "🔴"
    ),
    RECOVERING(
        label = "RECOVERING",
        subtitle = "Synchronizing latest information",
        symbol = "🔵"
    ),
    UNAVAILABLE(
        label = "DATA UNAVAILABLE",
        subtitle = "No verified current information available",
        symbol = "⚠️"
    );

    val isOnline: Boolean
        get() = this != OFFLINE

    val isFullyLive: Boolean
        get() = this == FULL_OPERATIONAL
}

/**
 * Operational status of an individual data provider or statutory feed.
 */
enum class SourceOperationalStatus(val label: String) {
    LIVE("LIVE"),
    CACHED("CACHED"),
    FALLBACK("FALLBACK"),
    STALE("STALE"),
    UNAVAILABLE("UNAVAILABLE"),
    HISTORICAL("HISTORICAL");

    val isLive: Boolean
        get() = this == LIVE

    val isCachedOrStale: Boolean
        get() = this == CACHED || this == STALE || this == HISTORICAL
}

/**
 * Independent operational status of the conversational AI / LLM assistant.
 *
 * Invariant: LLM failure NEVER invalidates or obscures deterministic hazard,
 * risk, impact, or NirnayCard assessments.
 */
enum class LlmStatus(val label: String, val description: String) {
    LLM_AVAILABLE(
        label = "AVAILABLE",
        description = "AI explanation available"
    ),
    LLM_UNAVAILABLE(
        label = "UNAVAILABLE",
        description = "AI explanation temporarily unavailable. Verified disaster assessment remains available."
    ),
    LLM_LOCAL_AVAILABLE(
        label = "LOCAL AVAILABLE",
        description = "On-device local assistant available"
    ),
    LLM_RECOVERING(
        label = "RECOVERING",
        description = "AI assistant reconnecting..."
    );

    val isAvailable: Boolean
        get() = this == LLM_AVAILABLE || this == LLM_LOCAL_AVAILABLE
}

/**
 * Authoritative statutory alert state (IMD CAP feed).
 */
enum class OfficialWarningStatus(val label: String) {
    AVAILABLE("AVAILABLE"),
    UPDATED("UPDATED"),
    EXPIRED("EXPIRED"),
    CANCELLED("CANCELLED"),
    UNAVAILABLE("UNAVAILABLE");

    val hasActiveAlert: Boolean
        get() = this == AVAILABLE || this == UPDATED
}

/**
 * Detailed health telemetry item for a registered operational source.
 */
data class SourceHealthItem(
    val sourceId: String,
    val sourceName: String,
    val category: String, // e.g., "Weather", "Official Warning", "GIS", "Hydrology", "Demographics"
    val authorityLevel: String, // "E0 Statutory", "E1 Standard", "E2 Supporting"
    val status: SourceOperationalStatus,
    val lastSuccess: String? = null,
    val lastFailure: String? = null,
    val lastVerifiedData: String? = null,
    val errorReason: String? = null,
    val isFallback: Boolean = false,
    val fallbackDisclaimer: String? = null
)

/**
 * Single coherent UI state for the System Resilience and Data Status feature.
 */
data class ResilienceUiState(
    val systemState: SystemOperationalState = SystemOperationalState.FULL_OPERATIONAL,
    val sourceStatuses: List<SourceHealthItem> = emptyList(),
    val llmStatus: LlmStatus = LlmStatus.LLM_AVAILABLE,
    val officialWarningStatus: OfficialWarningStatus = OfficialWarningStatus.AVAILABLE,
    val lastVerifiedTimestamp: String? = null,
    val lastVerifiedWarningTimestamp: String? = null,
    val isSyncing: Boolean = false,
    val syncMessage: String? = null,
    val activeWarningHeadline: String? = null
) {
    val isOffline: Boolean
        get() = systemState == SystemOperationalState.OFFLINE

    val isDegraded: Boolean
        get() = systemState == SystemOperationalState.DEGRADED_DATA

    val isRecovering: Boolean
        get() = systemState == SystemOperationalState.RECOVERING

    val isLlmUnavailable: Boolean
        get() = llmStatus == LlmStatus.LLM_UNAVAILABLE
}
