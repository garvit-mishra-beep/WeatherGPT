package com.weathergpt.presentation.status

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.core.resilience.SystemResilienceManager
import com.weathergpt.domain.model.resilience.LlmStatus
import com.weathergpt.domain.model.resilience.OfficialWarningStatus
import com.weathergpt.domain.model.resilience.ResilienceUiState
import com.weathergpt.domain.model.resilience.SourceHealthItem
import com.weathergpt.domain.model.resilience.SourceOperationalStatus
import com.weathergpt.domain.model.resilience.SystemOperationalState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SystemStatusScreen(
    resilienceManager: SystemResilienceManager = SystemResilienceManager.getInstance(),
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val state by resilienceManager.uiState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "System & Data Status",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color(0xFF0F172A)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        modifier = modifier.fillMaxSize()
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFFF8FAF8))
                .padding(innerPadding)
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. Overall Status Card
            OverallStatusCard(state = state)

            // 2. Offline / Freshness Safety Notice (Sections 6 & 7)
            if (state.systemState != SystemOperationalState.FULL_OPERATIONAL) {
                FreshnessSafetyCard(state = state)
            }

            // 3. Official Warning Dedicated Section (Section 9)
            OfficialWarningStatusCard(state = state)

            // 4. Independent AI Assistant / LLM Status Section (Section 10)
            LlmStatusCard(state = state)

            // 5. Source Health & Data Feeds (Sections 5, 8, 14)
            SourceHealthListSection(sources = state.sourceStatuses)

            // 6. Manual Retry Action (Section 16)
            RetryActionCard(
                isSyncing = state.isSyncing,
                syncMessage = state.syncMessage,
                onRetryClick = { resilienceManager.retryNow() }
            )

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun OverallStatusCard(state: ResilienceUiState) {
    val (bgColor, borderColor, textColor) = when (state.systemState) {
        SystemOperationalState.FULL_OPERATIONAL -> Triple(Color(0xFFF0FDF4), Color(0xFFBBF7D0), Color(0xFF15803D))
        SystemOperationalState.DEGRADED_DATA -> Triple(Color(0xFFFFFBEB), Color(0xFFFDE68A), Color(0xFFB45309))
        SystemOperationalState.OFFLINE -> Triple(Color(0xFFFEF2F2), Color(0xFFFECACA), Color(0xFFB91C1C))
        SystemOperationalState.RECOVERING -> Triple(Color(0xFFEFF6FF), Color(0xFFBFDBFE), Color(0xFF1D4ED8))
        SystemOperationalState.UNAVAILABLE -> Triple(Color(0xFFFFF7ED), Color(0xFFFED7AA), Color(0xFFC2410C))
    }

    Surface(
        shape = RoundedCornerShape(16.dp),
        color = bgColor,
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, borderColor, RoundedCornerShape(16.dp))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = state.systemState.symbol, fontSize = 20.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = state.systemState.label,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = textColor
                    )
                }
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = textColor.copy(alpha = 0.12f)
                ) {
                    Text(
                        text = if (state.isOffline) "OFFLINE" else "ONLINE",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = textColor,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = state.systemState.subtitle,
                fontSize = 13.sp,
                color = textColor.copy(alpha = 0.9f)
            )

            state.lastVerifiedTimestamp?.let { ts ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Latest verified information: $ts",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF64748B)
                )
            }
        }
    }
}

@Composable
private fun FreshnessSafetyCard(state: ResilienceUiState) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color.White,
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.Top
        ) {
            Text(text = "🛡️", fontSize = 16.sp)
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text(
                    text = "Operational Safety Notice",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF0F172A)
                )
                Spacer(modifier = Modifier.height(4.dp))
                val noticeText = when (state.systemState) {
                    SystemOperationalState.OFFLINE ->
                        "This device is currently offline. All displayed disaster intelligence is based on information verified at ${state.lastVerifiedTimestamp ?: "the last connection"}. Live real-time updates are temporarily unavailable."
                    SystemOperationalState.DEGRADED_DATA ->
                        "Some external data feeds are currently degraded or using secondary fallback sources. The system continues to evaluate deterministic risk using verified historical baselines and available telemetry."
                    SystemOperationalState.RECOVERING ->
                        "Connectivity has returned. The system is synchronizing latest official bulletins and observation streams."
                    else ->
                        "Live telemetry is temporarily unavailable. Displaying last verified records."
                }
                Text(
                    text = noticeText,
                    fontSize = 12.sp,
                    color = Color(0xFF475569),
                    lineHeight = 16.sp
                )
            }
        }
    }
}

@Composable
private fun OfficialWarningStatusCard(state: ResilienceUiState) {
    val (statusText, statusBg, statusColor) = when (state.officialWarningStatus) {
        OfficialWarningStatus.AVAILABLE, OfficialWarningStatus.UPDATED ->
            Triple("ACTIVE OFFICIAL ALERT", Color(0xFFDCFCE7), Color(0xFF15803D))
        OfficialWarningStatus.EXPIRED ->
            Triple("WARNING EXPIRED", Color(0xFFF1F5F9), Color(0xFF475569))
        OfficialWarningStatus.CANCELLED ->
            Triple("WARNING CANCELLED", Color(0xFFF1F5F9), Color(0xFF475569))
        OfficialWarningStatus.UNAVAILABLE ->
            Triple("FEED UNAVAILABLE", Color(0xFFFEE2E2), Color(0xFFB91C1C))
    }

    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color.White,
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "📢", fontSize = 16.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Official Statutory Warnings",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                }
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = statusBg
                ) {
                    Text(
                        text = statusText,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = statusColor,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Authority: India Meteorological Department (IMD / NDMA SACHET) • Tier E0",
                fontSize = 11.sp,
                color = Color(0xFF64748B)
            )

            if (state.officialWarningStatus == OfficialWarningStatus.UNAVAILABLE) {
                Spacer(modifier = Modifier.height(6.dp))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFFFF7ED),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "Official warning feed currently unavailable. Last verified warning: ${state.lastVerifiedWarningTimestamp ?: "None recorded"}. Third-party providers are NEVER substituted as official government warnings.",
                        fontSize = 11.sp,
                        color = Color(0xFFC2410C),
                        modifier = Modifier.padding(8.dp),
                        lineHeight = 15.sp
                    )
                }
            } else if (!state.activeWarningHeadline.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = state.activeWarningHeadline,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF0F172A)
                )
            }
        }
    }
}

@Composable
private fun LlmStatusCard(state: ResilienceUiState) {
    val isAvailable = state.llmStatus == LlmStatus.LLM_AVAILABLE || state.llmStatus == LlmStatus.LLM_LOCAL_AVAILABLE
    val (statusLabel, statusBg, statusColor) = if (isAvailable) {
        Triple("AVAILABLE", Color(0xFFDCFCE7), Color(0xFF15803D))
    } else {
        Triple("UNAVAILABLE", Color(0xFFFEF3C7), Color(0xFFB45309))
    }

    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color.White,
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🤖", fontSize = 16.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "AI Assistant (Ollama / Local LLM)",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                }
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = statusBg
                ) {
                    Text(
                        text = statusLabel,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = statusColor,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = state.llmStatus.description,
                fontSize = 12.sp,
                color = Color(0xFF475569),
                lineHeight = 16.sp
            )

            if (!isAvailable) {
                Spacer(modifier = Modifier.height(6.dp))
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = Color(0xFFF1F5F9),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "Safety Guarantee: LLM outage does NOT affect deterministic hazard, vulnerability, risk, or NirnayCard evaluation.",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF334155),
                        modifier = Modifier.padding(6.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun SourceHealthListSection(sources: List<SourceHealthItem>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "OPERATIONAL DATA SOURCES (${sources.size})",
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF64748B),
            letterSpacing = 0.5.sp
        )

        sources.forEach { source ->
            SourceHealthRowCard(source = source)
        }
    }
}

@Composable
private fun SourceHealthRowCard(source: SourceHealthItem) {
    val (statusBg, statusText, statusColor) = when (source.status) {
        SourceOperationalStatus.LIVE -> Triple(Color(0xFFDCFCE7), "LIVE", Color(0xFF15803D))
        SourceOperationalStatus.CACHED -> Triple(Color(0xFFE0F2FE), "CACHED", Color(0xFF0369A1))
        SourceOperationalStatus.FALLBACK -> Triple(Color(0xFFFEF3C7), "FALLBACK", Color(0xFFB45309))
        SourceOperationalStatus.STALE -> Triple(Color(0xFFFFEDD5), "STALE", Color(0xFFC2410C))
        SourceOperationalStatus.HISTORICAL -> Triple(Color(0xFFF1F5F9), "HISTORICAL", Color(0xFF475569))
        SourceOperationalStatus.UNAVAILABLE -> Triple(Color(0xFFFEE2E2), "UNAVAILABLE", Color(0xFFB91C1C))
    }

    Surface(
        shape = RoundedCornerShape(10.dp),
        color = Color.White,
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(10.dp))
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = source.sourceName,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = "${source.category} • ${source.authorityLevel}",
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }

                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = statusBg
                ) {
                    Text(
                        text = statusText,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = statusColor,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }

            source.lastVerifiedData?.let { verified ->
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Last verified data: $verified",
                    fontSize = 10.sp,
                    color = Color(0xFF64748B)
                )
            }

            if (source.isFallback && source.fallbackDisclaimer != null) {
                Spacer(modifier = Modifier.height(6.dp))
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = Color(0xFFFFFBEB),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFDE68A)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = source.fallbackDisclaimer,
                        fontSize = 10.sp,
                        color = Color(0xFF92400E),
                        modifier = Modifier.padding(6.dp),
                        lineHeight = 14.sp
                    )
                }
            }

            if (!source.errorReason.isNullOrBlank() && !source.isFallback) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = source.errorReason,
                    fontSize = 10.sp,
                    color = Color(0xFFB91C1C)
                )
            }
        }
    }
}

@Composable
private fun RetryActionCard(
    isSyncing: Boolean,
    syncMessage: String?,
    onRetryClick: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color.White,
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Synchronization & Recovery",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF0F172A)
                )
                Text(
                    text = syncMessage ?: "Verify all remote statutory feeds and observation channels.",
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            Button(
                onClick = onRetryClick,
                enabled = !isSyncing,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20)),
                shape = RoundedCornerShape(8.dp)
            ) {
                if (isSyncing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(14.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Retry now",
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = "Retry now", fontSize = 12.sp)
                }
            }
        }
    }
}
