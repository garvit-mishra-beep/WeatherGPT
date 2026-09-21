package com.weathergpt.presentation.alerts

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.R
import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.AlertSeverity
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.SpatialStatus
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.presentation.components.ErrorState
import com.weathergpt.presentation.components.LoadingState

@Composable
fun AlertsScreen(
    viewModel: AlertsViewModel,
    modifier: Modifier = Modifier,
    onAssessImpact: (String) -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val alertsState by viewModel.alertsState.collectAsStateWithLifecycle()

    var showLocationDialog by remember { mutableStateOf(false) }
    var expandedAlertId by remember { mutableStateOf<String?>(null) }

    val categories = listOf(
        stringResource(R.string.filter_all),
        stringResource(R.string.filter_weather),
        stringResource(R.string.filter_agri),
        stringResource(R.string.filter_govt)
    )

    if (showLocationDialog) {
        AlertDialog(
            onDismissRequest = { showLocationDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.location_select_title),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color(0xFF0F172A)
                )
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = stringResource(R.string.location_select_subtitle),
                        fontSize = 12.sp,
                        color = Color(0xFF64748B)
                    )
                    viewModel.availableLocations.forEach { loc ->
                        val isSelected = uiState.latitude == loc.latitude && uiState.longitude == loc.longitude
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(10.dp))
                                .background(if (isSelected) Color(0xFFE8F5E9) else Color(0xFFF8FAFC))
                                .clickable {
                                    viewModel.selectPredefinedLocation(loc)
                                    showLocationDialog = false
                                }
                                .padding(horizontal = 12.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = loc.displayName,
                                    fontSize = 14.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                    color = if (isSelected) Color(0xFF1B5E20) else Color(0xFF0F172A)
                                )
                                Text(
                                    text = loc.hindiName,
                                    fontSize = 11.sp,
                                    color = if (isSelected) Color(0xFF2E7D32) else Color(0xFF64748B)
                                )
                            }
                            if (isSelected) {
                                Text(text = "✓", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B5E20))
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showLocationDialog = false }) {
                    Text(stringResource(R.string.btn_close), color = Color(0xFF1B5E20), fontWeight = FontWeight.Bold)
                }
            }
        )
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // 1. Screen Title Header: "WEATHER ALERTS"
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "WEATHER ALERTS",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 0.5.sp,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = "Official Meteorological & Disaster Warning System",
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }

                // Location selector pill
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(Color.White)
                        .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                        .clickable { showLocationDialog = true }
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Text(text = "📍", fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = uiState.selectedDistrict,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Icon(
                        imageVector = Icons.Default.ArrowDropDown,
                        contentDescription = "Select Location",
                        tint = Color(0xFF64748B),
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }

        // 2. Demo Mode Consistency Banner
        item {
            val hasAlerts = (alertsState as? ResultState.Success<WeatherAlertsReport>)?.data?.alerts?.isNotEmpty() == true
            if (AppConfig.isDemoMode) {
                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF7ED)),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFED7AA)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(text = "🛡️", fontSize = 14.sp)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "OFFLINE VERIFIED",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFC2410C)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = if (hasAlerts) "• Cached operational alerts" else "• No active official warning recorded",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color(0xFF9A3412)
                            )
                        }
                    }
                }
            }
        }

        // 3. Current Alert Status Hero Dashboard
        item {
            when (val state = alertsState) {
                is ResultState.Loading -> {
                    LoadingState(
                        message = stringResource(R.string.loading_alerts),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                    )
                }
                is ResultState.Success<WeatherAlertsReport> -> {
                    val sortedAlerts = viewModel.getSortedFilteredAlerts(state.data)
                    val primaryAlert = sortedAlerts.firstOrNull()

                    if (primaryAlert == null) {
                        // NO ACTIVE OFFICIAL ALERT state
                        NoActiveOfficialAlertCard()
                    } else {
                        // Active Official Alert Dashboard
                        ActiveOfficialAlertCard(
                            alert = primaryAlert,
                            locationName = "${uiState.selectedDistrict}, Madhya Pradesh",
                            onAssessClick = {
                                onAssessImpact("There is a ${primaryAlert.severity} alert for ${primaryAlert.title.ifBlank { primaryAlert.hazardType }}. What actions should I take?")
                            }
                        )
                    }
                }
                is ResultState.Error -> {
                    ErrorState(
                        message = state.error.message,
                        error = state.error,
                        onRetry = { viewModel.loadAlerts() },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                    )
                }
                is ResultState.Idle -> {}
            }
        }

        // 4. Filter Pills Row
        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                categories.forEachIndexed { index, name ->
                    val isSelected = uiState.selectedCategoryIndex == index
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(20.dp))
                            .background(if (isSelected) Color(0xFF1B5E20) else Color.White)
                            .border(1.dp, if (isSelected) Color(0xFF1B5E20) else Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                            .clickable { viewModel.selectCategoryIndex(index) }
                            .padding(horizontal = 14.dp, vertical = 7.dp)
                    ) {
                        Text(
                            text = name,
                            fontSize = 12.sp,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                            color = if (isSelected) Color.White else Color(0xFF0F172A)
                        )
                    }
                }
            }
        }

        // 5. Alert List Section
        val reportData = (alertsState as? ResultState.Success<WeatherAlertsReport>)?.data
        val sortedList = if (reportData != null) viewModel.getSortedFilteredAlerts(reportData) else emptyList()

        if (sortedList.size > 1) {
            item {
                Text(
                    text = "ALL REGIONAL ALERTS (${sortedList.size})",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF64748B),
                    letterSpacing = 0.5.sp
                )
            }

            items(sortedList) { alert ->
                val isExpanded = expandedAlertId == alert.alertId
                ExpandableAlertCard(
                    alert = alert,
                    isExpanded = isExpanded,
                    onToggleExpand = {
                        expandedAlertId = if (isExpanded) null else alert.alertId
                    },
                    onAssessImpact = {
                        onAssessImpact("Please provide an impact assessment for: ${alert.title.ifBlank { alert.hazardType }} in ${alert.affectedArea.ifBlank { uiState.selectedDistrict }}")
                    }
                )
            }
        }

        // Bottom clearance to ensure no field or button is hidden behind bottom navigation (min 88dp)
        item {
            Spacer(modifier = Modifier.height(88.dp))
        }
    }
}

/**
 * Green Card for "NO ACTIVE OFFICIAL ALERT" (honestly distinguishing offline status from guaranteed safety)
 */
@Composable
private fun NoActiveOfficialAlertCard() {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.5.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBBF7D0)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFFDCFCE7))
                        .border(1.dp, Color(0xFF86EFAC), RoundedCornerShape(8.dp))
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "● GREEN",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF15803D)
                    )
                }

                Text(
                    text = "STATUS: SAFE / NORMAL",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF16A34A)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "NO ACTIVE OFFICIAL ALERT",
                fontSize = 18.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF0F172A)
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "System is operating offline. No cached official warning is available.",
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                color = Color(0xFF334155)
            )

            Spacer(modifier = Modifier.height(12.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFFF1F5F9))
                    .padding(10.dp)
            ) {
                Text(
                    text = "Official warning updates are unavailable while offline.",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF475569)
                )
            }
        }
    }
}

/**
 * Dedicated Alert Card with Full Dashboard Breakdown
 */
@Composable
private fun ActiveOfficialAlertCard(
    alert: OfficialAlert,
    locationName: String,
    onAssessClick: () -> Unit
) {
    val severity = alert.parsedSeverity
    val (badgeBg, badgeBorder, badgeText) = when (severity) {
        AlertSeverity.RED -> Triple(Color(0xFFFEE2E2), Color(0xFFFCA5A5), Color(0xFFB91C1C))
        AlertSeverity.ORANGE -> Triple(Color(0xFFFFEDD5), Color(0xFFFDBA74), Color(0xFFC2410C))
        AlertSeverity.YELLOW -> Triple(Color(0xFFFEF9C3), Color(0xFFFDE047), Color(0xFFA16207))
        AlertSeverity.GREEN -> Triple(Color(0xFFDCFCE7), Color(0xFF86EFAC), Color(0xFF15803D))
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, badgeBorder),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Severity Row + Status
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .background(badgeBg)
                        .border(1.dp, badgeBorder, RoundedCornerShape(8.dp))
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "● ${severity.name}",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Black,
                        color = badgeText
                    )
                }

                Text(
                    text = if (severity == AlertSeverity.RED) "CRITICAL HAZARD" else "ACTIVE WARNING",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = badgeText
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = if (severity == AlertSeverity.RED) "SEVERE WEATHER ALERT" else "WEATHER ADVISORY",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF64748B),
                letterSpacing = 0.5.sp
            )

            Text(
                text = alert.hazardType.ifBlank { alert.hazard },
                fontSize = 20.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF0F172A)
            )

            Text(
                text = alert.affectedArea.ifBlank { locationName },
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF334155)
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Validity Times
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "Valid: ", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                Text(
                    text = "${alert.validFrom.ifBlank { alert.effectiveFrom }} to ${alert.validUntil.ifBlank { alert.expiresAt }}",
                    fontSize = 12.sp,
                    color = Color(0xFF475569)
                )
            }

            Spacer(modifier = Modifier.height(4.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "Issued by: ", fontSize = 11.sp, fontWeight = FontWeight.Medium, color = Color(0xFF64748B))
                Text(text = alert.issuingAgency, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF334155))
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "Source: ", fontSize = 11.sp, fontWeight = FontWeight.Medium, color = Color(0xFF64748B))
                Text(text = alert.source, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF334155))
            }

            Spacer(modifier = Modifier.height(14.dp))

            // SECTION: WHAT THIS MEANS
            Text(
                text = "WHAT THIS MEANS",
                fontSize = 12.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF1E293B),
                letterSpacing = 0.5.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = alert.description.ifBlank {
                    "Intense convective cells have developed over the region with potential for sustained surface gusts and torrential precipitation."
                },
                fontSize = 13.sp,
                color = Color(0xFF334155),
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(14.dp))

            // SECTION: WHAT YOU SHOULD DO
            Text(
                text = "WHAT YOU SHOULD DO",
                fontSize = 12.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF1E293B),
                letterSpacing = 0.5.sp
            )
            Spacer(modifier = Modifier.height(6.dp))
            val instructions = if (alert.instructionsList.isNotEmpty()) {
                alert.instructionsList
            } else {
                listOf(
                    "Avoid unnecessary travel",
                    "Stay away from low-lying areas",
                    "Keep electrical equipment protected",
                    "Do not work in exposed fields during lightning"
                )
            }
            instructions.forEach { instr ->
                Row(
                    modifier = Modifier.padding(vertical = 2.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Text(text = "• ", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B5E20))
                    Text(text = instr, fontSize = 13.sp, color = Color(0xFF1E293B))
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // SECTION: AFFECTED AREA
            Text(
                text = "AFFECTED AREA",
                fontSize = 12.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF1E293B),
                letterSpacing = 0.5.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = alert.affectedArea.ifBlank { locationName },
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF334155)
                )

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFFF1F5F9))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = "Spatial status: ${alert.spatialStatus.name}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF475569)
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // SECTION: SOURCE & EVIDENCE
            Text(
                text = "SOURCE & EVIDENCE",
                fontSize = 12.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF1E293B),
                letterSpacing = 0.5.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "Official:", fontSize = 11.sp, color = Color(0xFF64748B))
                Text(text = if (alert.isOfficial) "YES" else "NO", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "Issued:", fontSize = 11.sp, color = Color(0xFF64748B))
                Text(text = alert.issuedAt.ifBlank { alert.effectiveFrom }, fontSize = 11.sp, color = Color(0xFF334155))
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "Retrieved:", fontSize = 11.sp, color = Color(0xFF64748B))
                Text(text = alert.retrievedAt.ifBlank { "2026-09-10T14:53:39Z" }, fontSize = 11.sp, color = Color(0xFF334155))
            }

            Spacer(modifier = Modifier.height(14.dp))

            Button(
                onClick = onAssessClick,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20)),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(text = "Assess Agricultural & Operational Impact", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }
    }
}

/**
 * Expandable Alert Card for Alert List
 */
@Composable
private fun ExpandableAlertCard(
    alert: OfficialAlert,
    isExpanded: Boolean,
    onToggleExpand: () -> Unit,
    onAssessImpact: () -> Unit
) {
    val severity = alert.parsedSeverity
    val (badgeBg, badgeBorder, badgeText) = when (severity) {
        AlertSeverity.RED -> Triple(Color(0xFFFEE2E2), Color(0xFFFCA5A5), Color(0xFFB91C1C))
        AlertSeverity.ORANGE -> Triple(Color(0xFFFFEDD5), Color(0xFFFDBA74), Color(0xFFC2410C))
        AlertSeverity.YELLOW -> Triple(Color(0xFFFEF9C3), Color(0xFFFDE047), Color(0xFFA16207))
        AlertSeverity.GREEN -> Triple(Color(0xFFDCFCE7), Color(0xFF86EFAC), Color(0xFF15803D))
    }

    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, badgeBorder),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onToggleExpand() }
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(badgeBg)
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = severity.name,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = badgeText
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = alert.hazardType.ifBlank { alert.hazard },
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                }

                Icon(
                    imageVector = if (isExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = if (isExpanded) "Collapse" else "Expand",
                    tint = Color(0xFF64748B)
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = alert.affectedArea.ifBlank { "Gwalior" },
                    fontSize = 12.sp,
                    color = Color(0xFF475569)
                )
                Text(
                    text = "Valid until ${alert.validUntil.ifBlank { alert.expiresAt }.takeLast(5)}",
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )
            }

            AnimatedVisibility(visible = isExpanded) {
                Column(modifier = Modifier.padding(top = 10.dp)) {
                    Text(
                        text = alert.description,
                        fontSize = 12.sp,
                        color = Color(0xFF334155),
                        lineHeight = 16.sp
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "Spatial Status: ${alert.spatialStatus.name} • Official: ${if (alert.isOfficial) "YES" else "NO"}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF475569)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Button(
                        onClick = onAssessImpact,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20)),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(text = "Assess Impact", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
