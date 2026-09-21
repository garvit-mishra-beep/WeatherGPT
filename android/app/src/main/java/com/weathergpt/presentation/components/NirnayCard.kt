package com.weathergpt.presentation.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.weathergpt.domain.model.decision.ActionWindow
import com.weathergpt.domain.model.decision.ActionWindowPeriod
import com.weathergpt.domain.model.decision.CandidateHourEvaluation
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionVerdict
import com.weathergpt.domain.model.decision.LedgerRuleEvaluation
import com.weathergpt.domain.model.decision.NirnayCard
import com.weathergpt.presentation.theme.SeverityGreen
import com.weathergpt.presentation.theme.SeverityOrange
import com.weathergpt.presentation.theme.SeverityRed
import com.weathergpt.presentation.theme.SeverityYellow
import com.weathergpt.presentation.theme.WeatherPrimary
import java.util.Locale

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun NirnayCardComposable(
    card: NirnayCard,
    modifier: Modifier = Modifier,
    initiallyExpanded: Boolean = false
) {
    var isExpanded by remember { mutableStateOf(initiallyExpanded) }

    val verdictBgColor = when (card.verdict) {
        DecisionVerdict.GO -> Color(0xFFDCFCE7)
        DecisionVerdict.PROCEED_WITH_CAUTION -> Color(0xFFFEF9C3)
        DecisionVerdict.POSTPONE -> Color(0xFFFFEDD5)
        DecisionVerdict.NO_GO -> Color(0xFFFEE2E2)
        DecisionVerdict.MONITOR, DecisionVerdict.INSUFFICIENT_DATA -> Color(0xFFF1F5F9)
    }

    val verdictTextColor = when (card.verdict) {
        DecisionVerdict.GO -> SeverityGreen
        DecisionVerdict.PROCEED_WITH_CAUTION -> SeverityYellow
        DecisionVerdict.POSTPONE -> SeverityOrange
        DecisionVerdict.NO_GO -> SeverityRed
        DecisionVerdict.MONITOR, DecisionVerdict.INSUFFICIENT_DATA -> Color(0xFF475569)
    }

    val severityColor = when (card.severity) {
        DecisionSeverity.LOW -> SeverityGreen
        DecisionSeverity.MODERATE -> SeverityYellow
        DecisionSeverity.HIGH -> SeverityOrange
        DecisionSeverity.CRITICAL -> SeverityRed
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // 1. Header: Domain Badge + Severity Tier
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(24.dp)
                            .clip(CircleShape)
                            .background(Color(0xFFE8F5E9)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(text = "⚡", fontSize = 12.sp)
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "NIRNAY DECISION",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = WeatherPrimary,
                        letterSpacing = 0.5.sp
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Phase 9B Data Source Status Badge (LIVE, CACHED, FALLBACK, HISTORICAL, UNAVAILABLE)
                    val statusBgColor = when (card.sourceStatus.uppercase(Locale.ROOT)) {
                        "LIVE" -> Color(0xFFDCFCE7)
                        "CACHED" -> Color(0xFFE0F2FE)
                        "FALLBACK" -> Color(0xFFFEF3C7)
                        "HISTORICAL" -> Color(0xFFF1F5F9)
                        else -> Color(0xFFFEE2E2)
                    }
                    val statusTextColor = when (card.sourceStatus.uppercase(Locale.ROOT)) {
                        "LIVE" -> Color(0xFF15803D)
                        "CACHED" -> Color(0xFF0369A1)
                        "FALLBACK" -> Color(0xFFB45309)
                        "HISTORICAL" -> Color(0xFF475569)
                        else -> Color(0xFFB91C1C)
                    }
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = statusBgColor,
                        modifier = Modifier.padding(end = 4.dp)
                    ) {
                        Text(
                            text = card.sourceStatus.uppercase(Locale.ROOT),
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                            color = statusTextColor,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }

                    // Severity Pill
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = severityColor.copy(alpha = 0.12f),
                        modifier = Modifier.padding(2.dp)
                    ) {
                        Text(
                            text = "${card.severity.raw.uppercase(Locale.ROOT)} RISK",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = severityColor,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                        )
                    }
                }
            }

            // Evidence Freshness & System Resilience Status (Section 17 & Section 7)
            val isLiveEvidence = card.sourceStatus.equals("LIVE", ignoreCase = true)
            val evidenceStatusText = if (isLiveEvidence) "VERIFIED" else card.sourceStatus.uppercase(Locale.ROOT)
            val evidenceStatusBg = if (isLiveEvidence) Color(0xFFDCFCE7) else Color(0xFFFEF3C7)
            val evidenceStatusColor = if (isLiveEvidence) Color(0xFF15803D) else Color(0xFFB45309)

            Spacer(modifier = Modifier.height(6.dp))
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = if (isLiveEvidence) Color(0xFFF8FAFC) else Color(0xFFFFFBEB),
                border = androidx.compose.foundation.BorderStroke(1.dp, if (isLiveEvidence) Color(0xFFE2E8F0) else Color(0xFFFDE68A)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "Evidence Status: ",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF475569)
                            )
                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = evidenceStatusBg
                            ) {
                                Text(
                                    text = evidenceStatusText,
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = evidenceStatusColor,
                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                )
                            }
                        }

                        val timeLabel = if (isLiveEvidence) {
                            "Assessment updated: ${card.lastVerifiedAt ?: "Live"}"
                        } else {
                            "Based on verified info: ${card.lastVerifiedAt ?: "Cached"}"
                        }
                        Text(
                            text = timeLabel,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF64748B)
                        )
                    }

                    if (!isLiveEvidence) {
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "This information was last verified at ${card.lastVerifiedAt ?: "earlier"}. Live data is currently unavailable.",
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Normal,
                            color = Color(0xFF92400E)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 2. User Question
            Text(
                text = card.question,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF0F172A),
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(10.dp))

            // 3. Verdict Banner (Large Prominent Action Status)
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = verdictBgColor,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "DECISION VERDICT",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = verdictTextColor.copy(alpha = 0.85f),
                            letterSpacing = 0.5.sp
                        )
                        Text(
                            text = card.verdict.raw.replace("_", " "),
                            fontSize = 20.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = verdictTextColor
                        )
                    }

                    // Icon / Confidence indicator
                    Surface(
                        shape = RoundedCornerShape(20.dp),
                        color = Color.White.copy(alpha = 0.8f),
                        modifier = Modifier.padding(start = 8.dp)
                    ) {
                        Text(
                            text = "${card.confidence.raw.uppercase(Locale.ROOT)} CONFIDENCE",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF334155),
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 4. Recommended Action Command
            Text(
                text = card.recommendedAction,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color(0xFF1E293B),
                lineHeight = 19.sp
            )

            // 4.5 Alert Impact & Exposure Intelligence (USP Phase 3)
            if (card.alertImpact != null) {
                Spacer(modifier = Modifier.height(10.dp))
                AlertImpactSection(alert = card.alertImpact, uncertainty = card.uncertainty)
            }

            // 4.6 Natural-Language Evidence-Grounded Explanation (Phase 4A)
            if (!card.explanation.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color(0xFFF8FAFC),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE2E8F0)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Filled.Info,
                                contentDescription = null,
                                tint = WeatherPrimary,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "EXPLANATION & INSIGHT",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = WeatherPrimary,
                                letterSpacing = 0.5.sp
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = card.explanation,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Normal,
                            color = Color(0xFF334155),
                            lineHeight = 18.sp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // 5. Action Window Section (USP Core)
            ActionWindowSection(actionWindow = card.actionWindow)

            Spacer(modifier = Modifier.height(12.dp))

            // 6. Honest Uncertainty / Trust Callout
            UncertaintyTrustCallout(uncertainty = card.uncertainty)

            Spacer(modifier = Modifier.height(12.dp))

            // 7. Expandable "Why this decision?" Accordion
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { isExpanded = !isExpanded }
                    .background(Color(0xFFF8FAFC))
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = WeatherPrimary,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isExpanded) "Hide Decision Evidence" else "Why this decision? (View Evidence)",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = WeatherPrimary
                    )
                }

                Icon(
                    imageVector = if (isExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = if (isExpanded) "Collapse" else "Expand",
                    tint = WeatherPrimary,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Expanded Evidence Details
            AnimatedVisibility(
                visible = isExpanded,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp)
                ) {
                    // A. Physical Reasons List
                    if (card.why.isNotEmpty()) {
                        Text(
                            text = "EVALUATED REASONS & THRESHOLDS",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF475569),
                            letterSpacing = 0.5.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        card.why.forEach { reason ->
                            Row(
                                modifier = Modifier.padding(vertical = 3.dp),
                                verticalAlignment = Alignment.Top
                            ) {
                                Text(
                                    text = "•",
                                    fontSize = 13.sp,
                                    color = SeverityOrange,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(end = 6.dp)
                                )
                                Text(
                                    text = reason,
                                    fontSize = 12.sp,
                                    color = Color(0xFF334155),
                                    lineHeight = 17.sp
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // B. Evaluated Rule Ledger (Audit Proof)
                    if (card.ledger != null && card.ledger.rules.isNotEmpty()) {
                        Text(
                            text = "RULE EVALUATION AUDIT LEDGER",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF475569),
                            letterSpacing = 0.5.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        card.ledger.rules.forEach { rule ->
                            RuleLedgerRow(rule = rule)
                            Spacer(modifier = Modifier.height(4.dp))
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // C. Candidate Hours Evaluation Trace (if present)
                    val hourlyEvals = card.actionWindow.hourlyEvaluations
                    if (!hourlyEvals.isNullOrEmpty()) {
                        Text(
                            text = "HOURLY FORECAST AUDIT TRACE",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF475569),
                            letterSpacing = 0.5.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        HourlyEvaluationsTable(evaluations = hourlyEvals.take(8))
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // D. Impact & Potential Consequences
                    if (!card.primaryRisk.isNullOrBlank()) {
                        Text(
                            text = "OPERATIONAL IMPACT & RISK",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF475569),
                            letterSpacing = 0.5.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFFFFBEB),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(10.dp)) {
                                Text(
                                    text = card.primaryRisk,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = Color(0xFF92400E)
                                )
                                if (!card.lossPotential.isNullOrBlank()) {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "Loss Potential: ${card.lossPotential}",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFFB45309)
                                    )
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // E. Action Alternatives / Fallbacks
                    if (card.alternatives.isNotEmpty()) {
                        Text(
                            text = "RECOMMENDED CONTINGENCIES",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF475569),
                            letterSpacing = 0.5.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        card.alternatives.forEach { alt ->
                            Row(
                                modifier = Modifier.padding(vertical = 2.dp),
                                verticalAlignment = Alignment.Top
                            ) {
                                Text(
                                    text = "→",
                                    fontSize = 12.sp,
                                    color = WeatherPrimary,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(end = 6.dp)
                                )
                                Text(
                                    text = alt,
                                    fontSize = 12.sp,
                                    color = Color(0xFF1E293B)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // F. Provenance and Attribution Footer
                    HorizontalDivider(color = Color(0xFFE2E8F0), thickness = 1.dp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "Deterministic Vayubodhak Decision Engine v2.0",
                            fontSize = 10.sp,
                            color = Color(0xFF94A3B8)
                        )
                        if (card.ledger != null) {
                            Text(
                                text = "Audit ID: ${card.ledger.decisionId}",
                                fontSize = 10.sp,
                                color = Color(0xFF94A3B8)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ActionWindowSection(actionWindow: ActionWindow) {
    if (actionWindow.isAvailable && actionWindow.bestWindow != null) {
        val best = actionWindow.bestWindow
        Column(modifier = Modifier.fillMaxWidth()) {
            // Best Window Primary Banner
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFFF0FDF4),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.5.dp, Color(0xFF86EFAC), RoundedCornerShape(12.dp))
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(text = "🎯", fontSize = 14.sp)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "BEST ACTION WINDOW",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF166534),
                                letterSpacing = 0.5.sp
                            )
                        }

                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color(0xFFDCFCE7)
                        ) {
                            Text(
                                text = "Score: ${String.format(Locale.ROOT, "%.0f", best.score)}/100",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF15803D),
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = best.summary,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Metrics Grid (Duration, Wind, Rain Prob, Rain Total)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ActionWindowMetricChip(
                            label = "Duration",
                            value = "${best.durationHours} hrs",
                            modifier = Modifier.weight(1f)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        ActionWindowMetricChip(
                            label = "Avg Wind",
                            value = "${String.format(Locale.ROOT, "%.1f", best.avgWindSpeedKmh)} km/h",
                            modifier = Modifier.weight(1f)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        ActionWindowMetricChip(
                            label = "Max Rain %",
                            value = "${String.format(Locale.ROOT, "%.0f", best.maxRainProbabilityPct)}%",
                            modifier = Modifier.weight(1f)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        ActionWindowMetricChip(
                            label = "Expected Rain",
                            value = "${best.totalRainfallMm} mm",
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // Fallback Windows (if any)
            if (actionWindow.fallbackWindows.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "ALTERNATIVE ACTION WINDOWS",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF64748B),
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(4.dp))
                actionWindow.fallbackWindows.forEach { fallback ->
                    FallbackWindowRow(fallback = fallback)
                    Spacer(modifier = Modifier.height(4.dp))
                }
            }
        }
    } else {
        // Unavailable State (Honest & Explicit)
        Surface(
            shape = RoundedCornerShape(12.dp),
            color = Color(0xFFFFF7ED),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFFED7AA), RoundedCornerShape(12.dp))
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "⏳", fontSize = 16.sp)
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "NO SUITABLE WINDOW FOUND",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = SeverityOrange
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = actionWindow.reason,
                        fontSize = 12.sp,
                        color = Color(0xFF431407),
                        lineHeight = 16.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun ActionWindowMetricChip(
    label: String,
    value: String,
    modifier: Modifier = Modifier
) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = Color.White,
        modifier = modifier.border(0.5.dp, Color(0xFFCBD5E1), RoundedCornerShape(8.dp))
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 6.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = label,
                fontSize = 9.sp,
                color = Color(0xFF64748B),
                fontWeight = FontWeight.Medium
            )
            Text(
                text = value,
                fontSize = 11.sp,
                color = Color(0xFF0F172A),
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun FallbackWindowRow(fallback: ActionWindowPeriod) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = Color(0xFFF8FAFC),
        modifier = Modifier
            .fillMaxWidth()
            .border(0.5.dp, Color(0xFFE2E8F0), RoundedCornerShape(8.dp))
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = fallback.summary,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF1E293B)
                )
                Text(
                    text = "${fallback.durationHours}h • Wind: ${String.format(Locale.ROOT, "%.1f", fallback.avgWindSpeedKmh)} km/h • Rain: ${String.format(Locale.ROOT, "%.0f", fallback.maxRainProbabilityPct)}%",
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )
            }
            Text(
                text = "Score: ${String.format(Locale.ROOT, "%.0f", fallback.score)}",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF475569)
            )
        }
    }
}

@Composable
private fun UncertaintyTrustCallout(uncertainty: com.weathergpt.domain.model.decision.DecisionUncertainty) {
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = Color(0xFFF8FAFC),
        modifier = Modifier
            .fillMaxWidth()
            .border(0.5.dp, Color(0xFFE2E8F0), RoundedCornerShape(10.dp))
    ) {
        Row(
            modifier = Modifier.padding(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = "🛡️", fontSize = 14.sp)
            Spacer(modifier = Modifier.width(8.dp))
            Column {
                Text(
                    text = "Forecast Uncertainty & Model Coverage",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF334155)
                )
                Text(
                    text = uncertainty.uncertaintyNote,
                    fontSize = 11.sp,
                    color = Color(0xFF64748B),
                    lineHeight = 15.sp
                )
            }
        }
    }
}

@Composable
private fun RuleLedgerRow(rule: LedgerRuleEvaluation) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = if (rule.satisfied) Color(0xFFF0FDF4) else Color(0xFFFEF2F2),
        modifier = Modifier
            .fillMaxWidth()
            .border(
                0.5.dp,
                if (rule.satisfied) Color(0xFFBBF7D0) else Color(0xFFFECACA),
                RoundedCornerShape(8.dp)
            )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = if (rule.satisfied) Icons.Default.CheckCircle else Icons.Default.Close,
                    contentDescription = if (rule.satisfied) "Satisfied" else "Violated",
                    tint = if (rule.satisfied) SeverityGreen else SeverityRed,
                    modifier = Modifier.size(14.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Column {
                    Text(
                        text = rule.ruleName.replace("_", " ").uppercase(Locale.ROOT),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1E293B)
                    )
                    Text(
                        text = "Observed: ${rule.observedValue} ${rule.unit} (${rule.operator} limit ${rule.threshold} ${rule.unit})",
                        fontSize = 10.sp,
                        color = Color(0xFF64748B)
                    )
                }
            }

            Text(
                text = if (rule.satisfied) "PASS" else "FAIL",
                fontSize = 11.sp,
                fontWeight = FontWeight.ExtraBold,
                color = if (rule.satisfied) SeverityGreen else SeverityRed
            )
        }
    }
}

@Composable
private fun HourlyEvaluationsTable(evaluations: List<CandidateHourEvaluation>) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = Color(0xFFF8FAFC),
        modifier = Modifier
            .fillMaxWidth()
            .border(0.5.dp, Color(0xFFE2E8F0), RoundedCornerShape(8.dp))
    ) {
        Column(modifier = Modifier.padding(8.dp)) {
            evaluations.forEachIndexed { index, hour ->
                val timeLabel = try {
                    hour.timeIso.substringAfter("T").take(5)
                } catch (e: Exception) {
                    hour.timeIso
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 3.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = timeLabel,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1E293B),
                        modifier = Modifier.width(45.dp)
                    )
                    Text(
                        text = "Wind: ${hour.windSpeedKmh}k",
                        fontSize = 10.sp,
                        color = Color(0xFF475569)
                    )
                    Text(
                        text = "Rain: ${String.format(Locale.ROOT, "%.0f", hour.rainProbabilityPct)}%",
                        fontSize = 10.sp,
                        color = Color(0xFF475569)
                    )
                    Text(
                        text = if (hour.passed) "PASS" else "FAIL",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (hour.passed) SeverityGreen else SeverityRed
                    )
                }
                if (index < evaluations.size - 1) {
                    HorizontalDivider(color = Color(0xFFE2E8F0), thickness = 0.5.dp)
                }
            }
        }
    }
}

@Composable
private fun AlertImpactSection(
    alert: com.weathergpt.domain.model.decision.AlertImpactInfo,
    uncertainty: com.weathergpt.domain.model.decision.DecisionUncertainty
) {
    val statusBgColor = when (alert.affectedAreaStatus) {
        com.weathergpt.domain.model.decision.ExposureState.INSIDE -> Color(0xFFFEE2E2)
        com.weathergpt.domain.model.decision.ExposureState.BUFFER -> Color(0xFFFEF9C3)
        com.weathergpt.domain.model.decision.ExposureState.OUTSIDE -> Color(0xFFF1F5F9)
        com.weathergpt.domain.model.decision.ExposureState.UNKNOWN -> Color(0xFFF8FAFC)
    }

    val statusTextColor = when (alert.affectedAreaStatus) {
        com.weathergpt.domain.model.decision.ExposureState.INSIDE -> SeverityRed
        com.weathergpt.domain.model.decision.ExposureState.BUFFER -> SeverityOrange
        com.weathergpt.domain.model.decision.ExposureState.OUTSIDE -> Color(0xFF334155)
        com.weathergpt.domain.model.decision.ExposureState.UNKNOWN -> Color(0xFF64748B)
    }

    val statusTitle = when (alert.affectedAreaStatus) {
        com.weathergpt.domain.model.decision.ExposureState.INSIDE -> "DIRECTLY AFFECTED"
        com.weathergpt.domain.model.decision.ExposureState.BUFFER -> "NEAR WARNING BOUNDARY"
        com.weathergpt.domain.model.decision.ExposureState.OUTSIDE -> "OUTSIDE ACTIVE WARNING AREA"
        com.weathergpt.domain.model.decision.ExposureState.UNKNOWN -> "AFFECTED AREA UNVERIFIED"
    }

    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color(0xFFF8FAFC),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            // 1. Alert Header (Hazard + Source + Official Badge)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Text(text = "⚠️", fontSize = 16.sp)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = alert.hazard ?: "${alert.alertSeverity ?: "Severe"} Weather Warning",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                }

                if (alert.isOfficial) {
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = Color(0xFFDCFCE7),
                        modifier = Modifier.padding(start = 6.dp)
                    ) {
                        Text(
                            text = "✓ OFFICIAL",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF166534),
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            // Dynamic Source Authority Line (NEVER hardcoded)
            if (!alert.issuingOffice.isNullOrBlank()) {
                Text(
                    text = "Source: ${alert.issuingOffice}",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF64748B)
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 2. Spatial Exposure Status Banner
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = statusBgColor,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(10.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = statusTitle,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = statusTextColor,
                            letterSpacing = 0.5.sp
                        )

                        // Exposure data availability indicator
                        if (alert.exposureStatus == "UNAVAILABLE" || !uncertainty.exposureDataAvailable) {
                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = Color(0xFFE2E8F0)
                            ) {
                                Text(
                                    text = "Exposure data unavailable",
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Color(0xFF475569),
                                    modifier = Modifier.padding(horizontal = 5.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    val detailMessage = when (alert.affectedAreaStatus) {
                        com.weathergpt.domain.model.decision.ExposureState.INSIDE ->
                            alert.exposureSummary ?: "Location intersects active warning perimeter."
                        com.weathergpt.domain.model.decision.ExposureState.BUFFER ->
                            "Location is near warning boundary (within 25 km buffer zone)."
                        com.weathergpt.domain.model.decision.ExposureState.OUTSIDE ->
                            "Official warning detected, but your selected location is outside the active warning area."
                        com.weathergpt.domain.model.decision.ExposureState.UNKNOWN ->
                            "Affected area could not be verified."
                    }

                    Text(
                        text = detailMessage,
                        fontSize = 12.sp,
                        color = statusTextColor.copy(alpha = 0.95f),
                        lineHeight = 16.sp
                    )

                    if (!alert.affectedAreaName.isNullOrBlank()) {
                        Spacer(modifier = Modifier.height(3.dp))
                        Text(
                            text = "Affected Area: ${alert.affectedAreaName}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF334155)
                        )
                    }
                }
            }

            // 3. Impact Metrics Chip Row
            if (alert.compositeImpactScore != null || !alert.riskCategory.isNullOrBlank() || !alert.alertId.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    if (alert.compositeImpactScore != null) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color.White,
                            modifier = Modifier
                                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = "Impact: ${String.format(Locale.ROOT, "%.1f", alert.compositeImpactScore)}/10.0",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF0F172A)
                            )
                        }
                    }

                    if (!alert.riskCategory.isNullOrBlank()) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color.White,
                            modifier = Modifier
                                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = "Risk: ${alert.riskCategory.uppercase(Locale.ROOT)}",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF0F172A)
                            )
                        }
                    }

                    if (!alert.alertId.isNullOrBlank()) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color.White,
                            modifier = Modifier
                                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = "ID: ${alert.alertId}",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color(0xFF64748B)
                            )
                        }
                    }
                }
            }
        }
    }
}
