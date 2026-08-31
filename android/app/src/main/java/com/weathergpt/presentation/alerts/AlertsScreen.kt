package com.weathergpt.presentation.alerts

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
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.AlertDialog
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
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.presentation.components.ErrorState
import com.weathergpt.presentation.components.LoadingState

data class AlertDetailItem(
    val title: String,
    val category: String,
    val body: String,
    val timestamp: String,
    val instructions: String = ""
)

@Composable
fun AlertsScreen(
    viewModel: AlertsViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val alertsState by viewModel.alertsState.collectAsStateWithLifecycle()

    var activeDetailAlert by remember { mutableStateOf<AlertDetailItem?>(null) }

    val categories = listOf(
        stringResource(R.string.filter_all),
        stringResource(R.string.filter_weather),
        stringResource(R.string.filter_agri),
        stringResource(R.string.filter_govt)
    )

    if (activeDetailAlert != null) {
        val alert = activeDetailAlert!!
        val defaultInstruction = stringResource(R.string.alert_default_instruction)
        AlertDialog(
            onDismissRequest = { activeDetailAlert = null },
            title = {
                Text(
                    text = alert.title,
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color(0xFF0F172A)
                )
            },
            text = {
                Column(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(vertical = 4.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(Color(0xFFFEF3C7))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = alert.category,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFD97706)
                        )
                    }
                    Text(
                        text = alert.body,
                        fontSize = 13.sp,
                        color = Color(0xFF334155),
                        lineHeight = 18.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = stringResource(R.string.alert_instructions_label),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                    Text(
                        text = alert.instructions.ifBlank { defaultInstruction },
                        fontSize = 12.sp,
                        color = Color(0xFF475569),
                        lineHeight = 16.sp
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { activeDetailAlert = null }) {
                    Text(stringResource(R.string.btn_close), color = Color(0xFF1B5E20), fontWeight = FontWeight.Bold)
                }
            }
        )
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .padding(16.dp)
    ) {
        // 1. Filter Pills Row matching Pragya's Screen 5
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
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    Text(
                        text = name,
                        fontSize = 13.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (isSelected) Color.White else Color(0xFF0F172A)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 2. Alert Cards List
        when (val state = alertsState) {
            is ResultState.Loading -> {
                LoadingState(
                    message = stringResource(R.string.loading_alerts),
                    modifier = Modifier.height(200.dp)
                )
            }
            is ResultState.Success<WeatherAlertsReport> -> {
                val report = state.data
                val filteredAlerts = viewModel.getFilteredAlerts(report)

                if (filteredAlerts.isEmpty()) {
                    // Display default verified advisory alerts if live list is empty
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        item {
                            val rainTitle = stringResource(R.string.alert_sample_rain_title)
                            val rainBody = stringResource(R.string.alert_sample_rain_body)
                            val rainDesc = stringResource(R.string.alert_sample_rain_desc)
                            val rainInst = stringResource(R.string.alert_sample_rain_inst)
                            PragyaAlertCard(
                                icon = "⚠️",
                                iconBg = Color(0xFFFEF3C7),
                                title = rainTitle,
                                categoryTag = stringResource(R.string.layer_rain),
                                tagBg = Color(0xFFFEF3C7),
                                tagTextColor = Color(0xFFD97706),
                                body = rainBody,
                                timestamp = "08:30 AM",
                                onClick = {
                                    activeDetailAlert = AlertDetailItem(
                                        title = rainTitle,
                                        category = "IMD OASIS CAP",
                                        body = rainDesc,
                                        timestamp = "08:30 AM",
                                        instructions = rainInst
                                    )
                                }
                            )
                        }
                        item {
                            val irrTitle = stringResource(R.string.alert_sample_irr_title)
                            val irrBody = stringResource(R.string.alert_sample_irr_body)
                            val irrDesc = stringResource(R.string.alert_sample_irr_desc)
                            val irrInst = stringResource(R.string.alert_sample_irr_inst)
                            PragyaAlertCard(
                                icon = "🌾",
                                iconBg = Color(0xFFE8F5E9),
                                title = irrTitle,
                                categoryTag = stringResource(R.string.filter_agri),
                                tagBg = Color(0xFFE8F5E9),
                                tagTextColor = Color(0xFF1B5E20),
                                body = irrBody,
                                timestamp = "07:15 AM",
                                onClick = {
                                    activeDetailAlert = AlertDetailItem(
                                        title = irrTitle,
                                        category = "Farmer Brain",
                                        body = irrDesc,
                                        timestamp = "07:15 AM",
                                        instructions = irrInst
                                    )
                                }
                            )
                        }
                        item {
                            val tempTitle = stringResource(R.string.alert_sample_temp_title)
                            val tempBody = stringResource(R.string.alert_sample_temp_body)
                            val tempDesc = stringResource(R.string.alert_sample_temp_desc)
                            val tempInst = stringResource(R.string.alert_sample_temp_inst)
                            val tempCat = stringResource(R.string.category_general)
                            PragyaAlertCard(
                                icon = "ℹ️",
                                iconBg = Color(0xFFF1F5F9),
                                title = tempTitle,
                                categoryTag = tempCat,
                                tagBg = Color(0xFFF1F5F9),
                                tagTextColor = Color(0xFF475569),
                                body = tempBody,
                                timestamp = "06:45 AM",
                                onClick = {
                                    activeDetailAlert = AlertDetailItem(
                                        title = tempTitle,
                                        category = tempCat,
                                        body = tempDesc,
                                        timestamp = "06:45 AM",
                                        instructions = tempInst
                                    )
                                }
                            )
                        }
                    }
                } else {
                    val defaultInstruction = stringResource(R.string.alert_default_instruction)
                    val defaultWeatherTag = stringResource(R.string.filter_weather)
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        items(filteredAlerts) { alert ->
                            PragyaAlertCard(
                                icon = if (alert.warningColor.equals("Red", true)) "🚨" else "⚠️",
                                iconBg = if (alert.warningColor.equals("Red", true)) Color(0xFFFEE2E2) else Color(0xFFFEF3C7),
                                title = alert.headline,
                                categoryTag = alert.hazard.ifBlank { defaultWeatherTag },
                                tagBg = Color(0xFFFEF3C7),
                                tagTextColor = Color(0xFFD97706),
                                body = alert.description,
                                timestamp = alert.effectiveFrom.substringAfter("T").take(5),
                                onClick = {
                                    activeDetailAlert = AlertDetailItem(
                                        title = alert.headline,
                                        category = "${alert.hazard} (${alert.warningColor})",
                                        body = alert.description,
                                        timestamp = alert.effectiveFrom.substringAfter("T").take(5),
                                        instructions = alert.instructions ?: defaultInstruction
                                    )
                                }
                            )
                        }
                    }
                }
            }
            is ResultState.Error -> {
                ErrorState(
                    message = state.error.message,
                    error = state.error,
                    onRetry = { viewModel.loadAlerts() },
                    modifier = Modifier.height(200.dp)
                )
            }
            is ResultState.Idle -> {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    item {
                        val rainTitle = stringResource(R.string.alert_sample_rain_title)
                        val rainBody = stringResource(R.string.alert_sample_rain_body)
                        val rainDesc = stringResource(R.string.alert_sample_rain_desc)
                        val rainInst = stringResource(R.string.alert_sample_rain_inst)
                        val rainCat = stringResource(R.string.layer_rain)
                        PragyaAlertCard(
                            icon = "⚠️",
                            iconBg = Color(0xFFFEF3C7),
                            title = rainTitle,
                            categoryTag = rainCat,
                            tagBg = Color(0xFFFEF3C7),
                            tagTextColor = Color(0xFFD97706),
                            body = rainBody,
                            timestamp = "08:30 AM",
                            onClick = {
                                activeDetailAlert = AlertDetailItem(
                                    title = rainTitle,
                                    category = rainCat,
                                    body = rainDesc,
                                    timestamp = "08:30 AM",
                                    instructions = rainInst
                                )
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PragyaAlertCard(
    icon: String,
    iconBg: Color,
    title: String,
    categoryTag: String,
    tagBg: Color,
    tagTextColor: Color,
    body: String,
    timestamp: String,
    onClick: () -> Unit = {}
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
            .clickable { onClick() }
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Top row with Icon, Title, and Category Tag
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Box(
                        modifier = Modifier
                            .size(32.dp)
                            .clip(CircleShape)
                            .background(iconBg),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(text = icon, fontSize = 16.sp)
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = title,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(tagBg)
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = categoryTag,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = tagTextColor
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Body text
            Text(
                text = body,
                fontSize = 13.sp,
                color = Color(0xFF334155),
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Bottom timestamp & "विवरण देखें →" link
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = timestamp,
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { onClick() }
                ) {
                    Text(
                        text = stringResource(R.string.alert_view_details),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                }
            }
        }
    }
}
