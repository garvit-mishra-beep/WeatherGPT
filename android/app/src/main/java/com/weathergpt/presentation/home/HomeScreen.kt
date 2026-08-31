package com.weathergpt.presentation.home

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.R
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.presentation.components.ErrorState
import com.weathergpt.presentation.components.LoadingState

@Composable
fun HomeScreen(
    viewModel: HomeViewModel,
    onNavigateToBrainSelection: () -> Unit,
    onNavigateToWeather: () -> Unit,
    onNavigateToMap: () -> Unit,
    onNavigateToAlerts: () -> Unit,
    onNavigateToFarmer: () -> Unit,
    onNavigateToData: () -> Unit,
    onNavigateToChat: (String?) -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val weatherState by viewModel.weatherState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    var showLocationDialog by remember { mutableStateOf(false) }
    var showVoiceUnavailableSnackbar by remember { mutableStateOf(false) }

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

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .verticalScroll(scrollState)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        // 1. Top Header Branding with Menu & Notification Bar
        HomeTopHeaderBar(
            onMenuClick = onNavigateToBrainSelection,
            onNotificationClick = onNavigateToAlerts
        )

        Spacer(modifier = Modifier.height(16.dp))

        // 2. User Greeting
        Text(
            text = stringResource(R.string.home_greeting, uiState.userName),
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF0F172A)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = stringResource(R.string.home_intro),
            fontSize = 13.sp,
            color = Color(0xFF475569),
            lineHeight = 18.sp
        )

        Spacer(modifier = Modifier.height(16.dp))

        // 3. Conversational Search / Chat Input Field with Send Button
        val defaultQuery = stringResource(R.string.home_search_placeholder)
        ConversationalChatInputBar(
            queryInput = uiState.queryInput,
            onQueryChange = { viewModel.setQueryInput(it) },
            onSendClick = {
                val query = uiState.queryInput.ifBlank { defaultQuery }
                onNavigateToChat(query)
            }
        )

        Spacer(modifier = Modifier.height(20.dp))

        // 4. Quick Action Workflows ("त्वरित विकल्प")
        Text(
            text = stringResource(R.string.home_quick_actions),
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF0F172A),
            modifier = Modifier.padding(start = 2.dp, bottom = 10.dp)
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            QuickActionItem(
                title = stringResource(R.string.action_will_it_rain),
                icon = "🌧️",
                onClick = onNavigateToWeather,
                modifier = Modifier.weight(1f)
            )
            QuickActionItem(
                title = stringResource(R.string.action_forecast),
                icon = "📅",
                onClick = onNavigateToWeather,
                modifier = Modifier.weight(1f)
            )
            QuickActionItem(
                title = stringResource(R.string.action_alerts),
                icon = "⚠️",
                onClick = onNavigateToAlerts,
                modifier = Modifier.weight(1f)
            )
            QuickActionItem(
                title = stringResource(R.string.action_map),
                icon = "📍",
                onClick = onNavigateToMap,
                modifier = Modifier.weight(1f)
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 5. Current Weather Card (Live Real Data matching Pragya's Card)
        when (val state = weatherState) {
            is ResultState.Loading -> {
                LoadingState(
                    message = stringResource(R.string.loading_weather),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                )
            }
            is ResultState.Success<CurrentWeather> -> {
                LiveWeatherCardPragya(
                    weather = state.data,
                    locationName = uiState.locationName,
                    onCardClick = onNavigateToWeather,
                    onLocationClick = { showLocationDialog = true }
                )
            }
            is ResultState.Error -> {
                ErrorState(
                    message = state.error.message,
                    error = state.error,
                    onRetry = { viewModel.loadWeather() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                )
            }
            is ResultState.Idle -> {
                LiveWeatherCardPragya(
                    weather = null,
                    locationName = uiState.locationName,
                    onCardClick = { viewModel.loadWeather() },
                    onLocationClick = { showLocationDialog = true }
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun HomeTopHeaderBar(
    onMenuClick: () -> Unit,
    onNotificationClick: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Left hamburger icon
        IconButton(
            onClick = onMenuClick,
            modifier = Modifier.size(36.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Menu,
                contentDescription = "Menu",
                tint = Color(0xFF0F172A)
            )
        }

        // Center Brand Emblem & Subtitle
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFE8F5E9)),
                contentAlignment = Alignment.Center
            ) {
                Text(text = "🌿", fontSize = 18.sp)
            }

            Spacer(modifier = Modifier.width(8.dp))

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = stringResource(R.string.app_tagline),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1B5E20)
                )
                Text(
                    text = stringResource(R.string.app_subtitle),
                    fontSize = 10.sp,
                    color = Color(0xFF475569),
                    fontWeight = FontWeight.Medium
                )
            }
        }

        // Right Notification Bell
        IconButton(
            onClick = onNotificationClick,
            modifier = Modifier.size(36.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Notifications,
                contentDescription = "Notifications",
                tint = Color(0xFF0F172A)
            )
        }
    }
}

@Composable
private fun ConversationalChatInputBar(
    queryInput: String,
    onQueryChange: (String) -> Unit,
    onSendClick: () -> Unit
) {
    OutlinedTextField(
        value = queryInput,
        onValueChange = onQueryChange,
        placeholder = {
            Text(
                text = stringResource(R.string.home_search_placeholder),
                color = Color(0xFF94A3B8),
                fontSize = 14.sp
            )
        },
        trailingIcon = {
            Box(
                modifier = Modifier
                    .padding(end = 6.dp)
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(Color(0xFF1B5E20))
                    .clickable { onSendClick() },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = "Send",
                    tint = Color.White,
                    modifier = Modifier.size(16.dp)
                )
            }
        },
        singleLine = true,
        shape = RoundedCornerShape(28.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedContainerColor = Color.White,
            unfocusedContainerColor = Color.White,
            focusedBorderColor = Color(0xFF2E7D32),
            unfocusedBorderColor = Color(0xFFE2E8F0)
        ),
        modifier = Modifier
            .fillMaxWidth()
            .height(54.dp)
    )
}

@Composable
private fun QuickActionItem(
    title: String,
    icon: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = modifier
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
            .clickable { onClick() }
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 12.dp, horizontal = 4.dp)
        ) {
            Text(text = icon, fontSize = 22.sp)
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = title,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF0F172A),
                maxLines = 1
            )
        }
    }
}

@Composable
private fun LiveWeatherCardPragya(
    weather: CurrentWeather?,
    locationName: String,
    onCardClick: () -> Unit,
    onLocationClick: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.5.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
            .clickable { onCardClick() }
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header Location Row + Live Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { onLocationClick() }
                ) {
                    Text(text = "📍", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = locationName,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFFE8F5E9))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = "● Live",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                }
            }

            Spacer(modifier = Modifier.height(4.dp))
            val obsTime = weather?.observationTime?.takeIf { it.isNotBlank() } ?: "09:41 AM"
            Text(
                text = "${stringResource(R.string.today)} • $obsTime",
                fontSize = 11.sp,
                color = Color(0xFF64748B)
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Main Temp & Illustration Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "${weather?.temperatureC?.toInt() ?: 31}°",
                        fontSize = 44.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = weather?.weatherCondition ?: "Partly Cloudy",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF334155)
                    )
                    Text(
                        text = stringResource(R.string.weather_condition_stable),
                        fontSize = 11.sp,
                        color = Color(0xFF2E7D32),
                        fontWeight = FontWeight.Medium
                    )
                }

                // 3D Weather Sun Behind Cloud Illustration
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(CircleShape)
                        .background(
                            Brush.radialGradient(
                                colors = listOf(Color(0xFFFEF3C7), Color(0xFFFFFBEB), Color.White)
                            )
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "⛅", fontSize = 48.sp)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Bottom Metrics Row
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFFF8FAFC), RoundedCornerShape(12.dp))
                    .padding(vertical = 8.dp, horizontal = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "▲", fontSize = 10.sp, color = Color(0xFFD97706))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Feels like ${weather?.feelsLikeC?.toInt() ?: 34}°C",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF334155)
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "💧", fontSize = 11.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Humidity ${weather?.relativeHumidityPct?.toInt() ?: 62}%",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF334155)
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🍃", fontSize = 11.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Wind ${weather?.windSpeedKmh?.toInt() ?: 16} km/h SW",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF334155)
                    )
                }
            }
        }
    }
}
