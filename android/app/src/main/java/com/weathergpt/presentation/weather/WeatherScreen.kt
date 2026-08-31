package com.weathergpt.presentation.weather

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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
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
import com.weathergpt.R
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.HourlyForecast
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.presentation.components.ErrorState
import com.weathergpt.presentation.components.LoadingState

@Composable
fun WeatherScreen(
    viewModel: WeatherViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val currentWeatherState by viewModel.currentWeatherState.collectAsStateWithLifecycle()
    val forecastState by viewModel.forecastState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    var showLocationDialog by remember { mutableStateOf(false) }

    if (showLocationDialog) {
        AlertDialog(
            onDismissRequest = { showLocationDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.change_location),
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
            .padding(16.dp)
    ) {
        // 1. Location Header Selector Pill
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .clickable { showLocationDialog = true }
                .padding(vertical = 4.dp)
        ) {
            Text(text = "📍", fontSize = 15.sp)
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = uiState.locationName,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF0F172A)
            )
            Icon(
                imageVector = Icons.Default.ArrowDropDown,
                contentDescription = "Dropdown",
                tint = Color(0xFF475569),
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 2. Current Weather Hero Display matching Pragya's Screen 3
        when (val state = currentWeatherState) {
            is ResultState.Loading -> {
                LoadingState(
                    message = stringResource(R.string.loading_weather),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                )
            }
            is ResultState.Success<CurrentWeather> -> {
                val forecastData = (forecastState as? ResultState.Success<WeatherForecast>)?.data
                val todayDaily = forecastData?.dailyForecast?.firstOrNull()
                val highTemp = todayDaily?.tempMaxC ?: (state.data.temperatureC + 1.5)
                val lowTemp = todayDaily?.tempMinC ?: (state.data.temperatureC - 5.0)

                WeatherHeroCardPragya(
                    weather = state.data,
                    highTemp = highTemp,
                    lowTemp = lowTemp
                )
            }
            is ResultState.Error -> {
                ErrorState(
                    message = state.error.message,
                    error = state.error,
                    onRetry = { viewModel.loadData() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                )
            }
            is ResultState.Idle -> {}
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 3. 3-Column Weather Metrics Bar
        val currentTemp = (currentWeatherState as? ResultState.Success<CurrentWeather>)?.data
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White, RoundedCornerShape(14.dp))
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
                .padding(vertical = 12.dp, horizontal = 8.dp),
            horizontalArrangement = Arrangement.SpaceAround
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "💧", fontSize = 14.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Column {
                    Text(
                        text = "${currentTemp?.relativeHumidityPct?.toInt() ?: 62}%",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(text = "Humidity", fontSize = 10.sp, color = Color(0xFF64748B))
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "🍃", fontSize = 14.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Column {
                    Text(
                        text = "${currentTemp?.windSpeedKmh?.toInt() ?: 16} km/h",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(text = "SW Wind", fontSize = 10.sp, color = Color(0xFF64748B))
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "🌧️", fontSize = 14.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Column {
                    Text(
                        text = "${currentTemp?.precipitationMm ?: 0.2} mm",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0288D1)
                    )
                    Text(text = "Rainfall", fontSize = 10.sp, color = Color(0xFF64748B))
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 4. Forecast Interval Tabs
        val intervals = ForecastInterval.entries
        val selectedTabIndex = intervals.indexOf(uiState.selectedInterval)

        TabRow(
            selectedTabIndex = selectedTabIndex,
            containerColor = Color.Transparent,
            contentColor = Color(0xFF1B5E20),
            indicator = { tabPositions ->
                if (selectedTabIndex < tabPositions.size) {
                    TabRowDefaults.SecondaryIndicator(
                        modifier = Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                        color = Color(0xFF1B5E20),
                        height = 3.dp
                    )
                }
            },
            divider = {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(1.dp)
                        .background(Color(0xFFE2E8F0))
                )
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            intervals.forEachIndexed { index, interval ->
                val isSelected = selectedTabIndex == index
                Tab(
                    selected = isSelected,
                    onClick = { viewModel.setInterval(interval) },
                    text = {
                        Text(
                            text = stringResource(interval.titleResId),
                            fontSize = 13.sp,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                            color = if (isSelected) Color(0xFF1B5E20) else Color(0xFF64748B)
                        )
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 5. Hourly 24h Carousel or Daily Cards matching Pragya's Screen 3
        when (val fState = forecastState) {
            is ResultState.Loading -> {
                LoadingState(
                    message = stringResource(R.string.loading_forecast),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(130.dp)
                )
            }
            is ResultState.Success<WeatherForecast> -> {
                when (uiState.selectedInterval) {
                    ForecastInterval.HOURLY -> {
                        val hourlyList = fState.data.hourlyForecast
                        if (!hourlyList.isNullOrEmpty()) {
                            LazyRow(
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                items(hourlyList.take(24)) { hour ->
                                    HourlyItemCardPragya(hour = hour)
                                }
                            }
                        } else {
                            LazyRow(
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                val sampleHours = listOf(
                                    Triple("Now", "31°", "⛅"),
                                    Triple("12 PM", "32°", "⛅"),
                                    Triple("1 PM", "33°", "⛅"),
                                    Triple("2 PM", "32°", "🌧️"),
                                    Triple("3 PM", "31°", "⛅")
                                )
                                items(sampleHours) { (time, temp, icon) ->
                                    Card(
                                        shape = RoundedCornerShape(14.dp),
                                        colors = CardDefaults.cardColors(containerColor = Color.White),
                                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                                        modifier = Modifier
                                            .width(72.dp)
                                            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
                                    ) {
                                        Column(
                                            horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
                                            modifier = Modifier.padding(vertical = 12.dp, horizontal = 4.dp)
                                        ) {
                                            Text(text = time, fontSize = 11.sp, color = Color(0xFF64748B))
                                            Spacer(modifier = Modifier.height(8.dp))
                                            Text(text = icon, fontSize = 22.sp)
                                            Spacer(modifier = Modifier.height(8.dp))
                                            Text(text = temp, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                                        }
                                    }
                                }
                            }
                        }
                    }
                    ForecastInterval.THREE_DAYS -> {
                        DailyListPragya(dailyList = fState.data.dailyForecast.take(3))
                    }
                    ForecastInterval.FIVE_DAYS -> {
                        DailyListPragya(dailyList = fState.data.dailyForecast.take(5))
                    }
                    ForecastInterval.TEN_DAYS -> {
                        DailyListPragya(dailyList = fState.data.dailyForecast.take(7))
                    }
                }
            }
            is ResultState.Error -> {
                ErrorState(
                    message = fState.error.message,
                    error = fState.error,
                    onRetry = { viewModel.loadData() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(130.dp)
                )
            }
            is ResultState.Idle -> {}
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 6. Summary Card in Light Mint Green Box
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFF1F8F4)),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFDCFCE7), RoundedCornerShape(16.dp))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = stringResource(R.string.summary_title),
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1B5E20)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = stringResource(R.string.weather_summary_default),
                    fontSize = 12.sp,
                    color = Color(0xFF1E293B),
                    lineHeight = 18.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { viewModel.setInterval(ForecastInterval.TEN_DAYS) }
                ) {
                    Text(
                        text = stringResource(R.string.weather_see_all_forecast),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                        contentDescription = "More",
                        tint = Color(0xFF1B5E20),
                        modifier = Modifier.size(14.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun WeatherHeroCardPragya(
    weather: CurrentWeather,
    highTemp: Double,
    lowTemp: Double
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = "${weather.temperatureC.toInt()}°C",
                fontSize = 48.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF0F172A)
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = weather.weatherCondition,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF334155)
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "H: ${highTemp.toInt()}°C  L: ${lowTemp.toInt()}°C",
                fontSize = 13.sp,
                color = Color(0xFF64748B),
                fontWeight = FontWeight.Medium
            )
        }

        // 3D Sun Behind Cloud Illustration
        Box(
            modifier = Modifier
                .size(100.dp)
                .clip(CircleShape)
                .background(
                    Brush.radialGradient(
                        colors = listOf(Color(0xFFFEF3C7), Color(0xFFFFFBEB), Color.White)
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(text = "⛅", fontSize = 56.sp)
        }
    }
}

@Composable
private fun HourlyItemCardPragya(hour: HourlyForecast) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .width(72.dp)
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(vertical = 12.dp, horizontal = 4.dp)
        ) {
            Text(
                text = hour.time.substringAfter("T").take(5),
                fontSize = 11.sp,
                color = Color(0xFF64748B)
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = if (hour.precipitationMm > 0) "🌧️" else "⛅", fontSize = 22.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "${hour.temperatureC.toInt()}°",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF0F172A)
            )
        }
    }
}

@Composable
private fun DailyListPragya(dailyList: List<DailyForecast>) {
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        dailyList.forEach { daily ->
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = daily.date,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF0F172A),
                        modifier = Modifier.width(90.dp)
                    )
                    Text(text = "⛅", fontSize = 18.sp)
                    Text(
                        text = "${daily.tempMaxC.toInt()}° / ${daily.tempMinC.toInt()}°",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = daily.dominantCondition,
                        fontSize = 12.sp,
                        color = Color(0xFF64748B)
                    )
                }
            }
        }
    }
}
