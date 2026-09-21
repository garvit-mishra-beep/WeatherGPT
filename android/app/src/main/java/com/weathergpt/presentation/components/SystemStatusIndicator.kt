package com.weathergpt.presentation.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.weathergpt.domain.model.resilience.LlmStatus
import com.weathergpt.domain.model.resilience.ResilienceUiState
import com.weathergpt.domain.model.resilience.SystemOperationalState

/**
 * Compact, accessible System Resilience & Data Status indicator banner.
 *
 * Guarantees:
 * 1. Accessible multi-attribute encoding: Icon + Label + Subtitle + Semantic description (never color alone).
 * 2. Clickable: Navigates to the detailed System Status screen.
 * 3. Never hides stale/cached/fallback states.
 */
@Composable
fun SystemStatusIndicator(
    state: ResilienceUiState,
    onStatusClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val (bgColor, borderColor, dotColor, textColor) = when (state.systemState) {
        SystemOperationalState.FULL_OPERATIONAL -> QuadColor(
            bg = Color(0xFFF0FDF4),
            border = Color(0xFFBBF7D0),
            dot = Color(0xFF16A34A),
            text = Color(0xFF15803D)
        )
        SystemOperationalState.DEGRADED_DATA -> QuadColor(
            bg = Color(0xFFFFFBEB),
            border = Color(0xFFFDE68A),
            dot = Color(0xFFD97706),
            text = Color(0xFFB45309)
        )
        SystemOperationalState.OFFLINE -> QuadColor(
            bg = Color(0xFFFEF2F2),
            border = Color(0xFFFECACA),
            dot = Color(0xFFDC2626),
            text = Color(0xFFB91C1C)
        )
        SystemOperationalState.RECOVERING -> QuadColor(
            bg = Color(0xFFEFF6FF),
            border = Color(0xFFBFDBFE),
            dot = Color(0xFF2563EB),
            text = Color(0xFF1D4ED8)
        )
        SystemOperationalState.UNAVAILABLE -> QuadColor(
            bg = Color(0xFFFFF7ED),
            border = Color(0xFFFED7AA),
            dot = Color(0xFFEA580C),
            text = Color(0xFFC2410C)
        )
    }

    val semanticAccessibilityDescription = "${state.systemState.label}: ${state.systemState.subtitle}. Tap to open system status."

    Column(modifier = modifier.fillMaxWidth()) {
        Surface(
            shape = RoundedCornerShape(12.dp),
            color = bgColor,
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, borderColor, RoundedCornerShape(12.dp))
                .clickable(onClick = onStatusClick)
                .semantics { contentDescription = semanticAccessibilityDescription }
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    // Symbol + Accessible colored indicator dot
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(dotColor)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = state.systemState.label,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = textColor
                            )
                            if (state.lastVerifiedTimestamp != null && state.systemState != SystemOperationalState.FULL_OPERATIONAL) {
                                Text(
                                    text = " • ${state.lastVerifiedTimestamp}",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = textColor.copy(alpha = 0.85f)
                                )
                            }
                        }
                        Text(
                            text = if (state.isSyncing && state.syncMessage != null) state.syncMessage else state.systemState.subtitle,
                            fontSize = 11.sp,
                            color = textColor.copy(alpha = 0.9f),
                            fontWeight = FontWeight.Normal
                        )
                    }
                }

                // Status chip arrow
                Text(
                    text = "Details ›",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = textColor
                )
            }
        }

        // Optional independent LLM degradation alert banner
        if (state.llmStatus == LlmStatus.LLM_UNAVAILABLE) {
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = Color(0xFFF8FAFC),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp)
                    .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(8.dp))
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = "ℹ️", fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "AI explanation temporarily unavailable. Verified disaster assessment remains available.",
                        fontSize = 10.sp,
                        color = Color(0xFF475569),
                        fontWeight = FontWeight.Medium,
                        lineHeight = 14.sp
                    )
                }
            }
        }
    }
}

private data class QuadColor(
    val bg: Color,
    val border: Color,
    val dot: Color,
    val text: Color
)
