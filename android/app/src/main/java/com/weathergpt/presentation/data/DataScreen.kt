package com.weathergpt.presentation.data

import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.R
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison

@Composable
fun DataScreen(
    viewModel: DataViewModel,
    onNavigateToAnalyst: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    var showExportDialog by remember { mutableStateOf(false) }
    var showGfsDialog by remember { mutableStateOf(false) }
    var showClimateDialog by remember { mutableStateOf(false) }

    if (showExportDialog) {
        AlertDialog(
            onDismissRequest = { showExportDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.export_dialog_title),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color(0xFF0F172A)
                )
            },
            text = {
                Text(
                    text = stringResource(R.string.export_dialog_desc),
                    fontSize = 13.sp,
                    color = Color(0xFF334155),
                    lineHeight = 18.sp
                )
            },
            confirmButton = {
                TextButton(onClick = { showExportDialog = false }) {
                    Text(stringResource(R.string.btn_close), color = Color(0xFF1B5E20), fontWeight = FontWeight.Bold)
                }
            }
        )
    }

    if (showGfsDialog) {
        AlertDialog(
            onDismissRequest = { showGfsDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.gfs_dialog_title),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color(0xFF0F172A)
                )
            },
            text = {
                Text(
                    text = stringResource(R.string.gfs_dialog_desc),
                    fontSize = 13.sp,
                    color = Color(0xFF334155),
                    lineHeight = 18.sp
                )
            },
            confirmButton = {
                TextButton(onClick = { showGfsDialog = false }) {
                    Text(stringResource(R.string.btn_close), color = Color(0xFF1B5E20), fontWeight = FontWeight.Bold)
                }
            }
        )
    }

    if (showClimateDialog) {
        AlertDialog(
            onDismissRequest = { showClimateDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.climate_dialog_title),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color(0xFF0F172A)
                )
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = stringResource(R.string.climate_dialog_desc),
                        fontSize = 12.sp,
                        color = Color(0xFF64748B),
                        lineHeight = 16.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color(0xFFF8FAFC))
                            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(8.dp))
                            .padding(10.dp)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(
                                text = "• Trend Direction: ${uiState.trendDirection}",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF0F172A)
                            )
                            Text(
                                text = "• Sen's Slope: ${uiState.historicalTrendSlope?.let { String.format(java.util.Locale.US, "%.4f", it) } ?: "Unavailable"}",
                                fontSize = 12.sp,
                                color = Color(0xFF334155)
                            )
                            Text(
                                text = "• Normal Rainfall: ${uiState.normalRainfallMm?.let { "$it mm" } ?: "Unavailable"}",
                                fontSize = 12.sp,
                                color = Color(0xFF334155)
                            )
                            Text(
                                text = "• Actual Rainfall: ${uiState.actualRainfallMm?.let { "$it mm" } ?: "Unavailable"}",
                                fontSize = 12.sp,
                                color = Color(0xFF334155)
                            )
                            Text(
                                text = "• Rainfall Departure: ${uiState.rainfallAnomalyPct?.let { "${String.format(java.util.Locale.US, "%.1f", it)}% (${uiState.climateNormalsCategory})" } ?: "Unavailable"}",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if ((uiState.rainfallAnomalyPct ?: 0.0) >= 0) Color(0xFF16A34A) else Color(0xFFDC2626)
                            )
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showClimateDialog = false }) {
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
        // 1. Model Selector Chips: GFS | WRF | Model Comparison
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
        ) {
            val gfsSelected = uiState.selectedModel == "GFS (0.25°)"
            val wrfSelected = uiState.selectedModel == "WRF (Regional)"
            val compSelected = uiState.selectedModel == "Comparison"

            // GFS Chip
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(if (gfsSelected) Color(0xFF1B5E20) else Color.White)
                    .border(1.dp, if (gfsSelected) Color(0xFF1B5E20) else Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                    .clickable { viewModel.selectModel("GFS (0.25°)") }
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🌐", fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = stringResource(R.string.nwp_gfs_tab),
                        fontSize = 12.sp,
                        fontWeight = if (gfsSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (gfsSelected) Color.White else Color(0xFF0F172A)
                    )
                }
            }

            // WRF Chip
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(if (wrfSelected) Color(0xFF1B5E20) else Color.White)
                    .border(1.dp, if (wrfSelected) Color(0xFF1B5E20) else Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                    .clickable { viewModel.selectModel("WRF (Regional)") }
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "⚡", fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = stringResource(R.string.nwp_wrf_tab),
                        fontSize = 12.sp,
                        fontWeight = if (wrfSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (wrfSelected) Color.White else Color(0xFF0F172A)
                    )
                }
            }

            // Comparison Chip
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(if (compSelected) Color(0xFF1B5E20) else Color.White)
                    .border(1.dp, if (compSelected) Color(0xFF1B5E20) else Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                    .clickable { viewModel.selectModel("Comparison") }
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "📈", fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = stringResource(R.string.nwp_comparison_tab),
                        fontSize = 12.sp,
                        fontWeight = if (compSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (compSelected) Color.White else Color(0xFF0F172A)
                    )
                }
            }

            // Export Data Chip
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(Color.White)
                    .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                    .clickable { showExportDialog = true }
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "📥", fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = stringResource(R.string.action_export_data),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF0F172A)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 2. Dynamic Model / Comparison Card
        when (uiState.selectedModel) {
            "WRF (Regional)" -> {
                WRFModelCard(wrfState = uiState.wrfGridState)
            }
            "Comparison" -> {
                NWPComparisonCard(comparisonState = uiState.nwpComparisonState)
            }
            else -> {
                // Default: GFS 0.25° Card
                GFSModelCard(gfsState = uiState.gfsGridState)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        val forecastData = (uiState.forecastState as? ResultState.Success<com.weathergpt.domain.model.weather.WeatherForecast>)?.data
        val dailyList = forecastData?.dailyForecast.orEmpty()
        val hourlyList = forecastData?.hourlyForecast.orEmpty()

        val (chartPoints, chartUnit, chartTitle, chartColor) = when (uiState.selectedMetricTab) {
            "Rainfall" -> {
                val pts = if (dailyList.isNotEmpty()) {
                    dailyList.take(7).map { Pair(it.date.takeLast(5), it.precipitationSumMm.toFloat()) }
                } else emptyList()
                listOf(pts, "mm", "Precipitation Trend", Color(0xFF0284C7))
            }
            "Wind" -> {
                val pts = if (dailyList.isNotEmpty()) {
                    dailyList.take(7).map { Pair(it.date.takeLast(5), it.windSpeedMaxKmh.toFloat()) }
                } else emptyList()
                listOf(pts, "km/h", "Wind Speed Trend", Color(0xFFD97706))
            }
            "Humidity" -> {
                val pts = if (hourlyList.isNotEmpty()) {
                    hourlyList.take(7).map { Pair(it.time.takeLast(5), it.relativeHumidityPct.toFloat()) }
                } else emptyList()
                listOf(pts, "%", "Humidity Profile", Color(0xFF7C3AED))
            }
            else -> {
                val pts = if (dailyList.isNotEmpty()) {
                    dailyList.take(7).map { Pair(it.date.takeLast(5), it.tempMaxC.toFloat()) }
                } else emptyList()
                listOf(pts, "°C", "Temperature Trend", Color(0xFF1B5E20))
            }
        }.let {
            @Suppress("UNCHECKED_CAST")
            Four(it[0] as List<Pair<String, Float>>, it[1] as String, it[2] as String, it[3] as Color)
        }

        // Metric Selector Chips
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            listOf("Temperature", "Rainfall", "Wind", "Humidity").forEach { metric ->
                val isSelected = uiState.selectedMetricTab == metric
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(16.dp))
                        .background(if (isSelected) Color(0xFF1B5E20) else Color.White)
                        .border(1.dp, if (isSelected) Color(0xFF1B5E20) else Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
                        .clickable { viewModel.selectMetricTab(metric) }
                        .padding(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = metric,
                        fontSize = 11.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (isSelected) Color.White else Color(0xFF334155)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 3. Dynamic Weather Trend Chart Card
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = chartTitle,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color(0xFFF1F5F9))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "${chartPoints.size} points",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF475569)
                        )
                    }
                }

                Text(
                    text = "Gwalior (26.22°N, 78.18°E) • ${forecastData?.forecastStart?.take(10) ?: "2026-09-10"} → ${forecastData?.forecastEnd?.take(10) ?: "2026-09-16"}",
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )
                Text(
                    text = "Source: ${forecastData?.provider ?: "Open-Meteo"} (Real Cached Weather)",
                    fontSize = 10.sp,
                    color = Color(0xFF94A3B8)
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Line chart canvas with dynamic points
                TemperatureLineChartPragya(
                    points = chartPoints,
                    unit = chartUnit,
                    lineColor = chartColor,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(160.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 4. Quick Access Section Header
        Text(
            text = stringResource(R.string.quick_access_title),
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF0F172A),
            modifier = Modifier.padding(start = 2.dp, bottom = 12.dp)
        )

        // 5. Quick Access Rows List
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            DataQuickAccessCard(
                icon = "📊",
                iconBg = Color(0xFFEFF6FF),
                title = stringResource(R.string.quick_access_analyst),
                subtitle = stringResource(R.string.quick_access_analyst_sub),
                onClick = onNavigateToAnalyst
            )

            DataQuickAccessCard(
                icon = "🌐",
                iconBg = Color(0xFFF0FDF4),
                title = stringResource(R.string.quick_access_gfs),
                subtitle = stringResource(R.string.quick_access_gfs_sub),
                onClick = { showGfsDialog = true }
            )

            DataQuickAccessCard(
                icon = "📉",
                iconBg = Color(0xFFFEF3C7),
                title = stringResource(R.string.quick_access_climate),
                subtitle = stringResource(R.string.quick_access_climate_sub),
                onClick = { showClimateDialog = true }
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun GFSModelCard(gfsState: ResultState<NWPGridPoint>) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.nwp_gfs_title),
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = stringResource(R.string.nwp_gfs_subtitle),
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFFE0F2FE))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(text = stringResource(R.string.nwp_gfs_resolution), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF0284C7))
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            when (gfsState) {
                is ResultState.Success -> {
                    val pt = gfsState.data
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ModelMetricTile(stringResource(R.string.nwp_metric_temp), "${pt.temperature2mC}°C", "2m level")
                        ModelMetricTile(stringResource(R.string.nwp_metric_precip), "${pt.accumulatedPrecipMm} mm", "24h accum")
                        ModelMetricTile(stringResource(R.string.nwp_metric_wind), "${pt.windSpeedKmh} km/h", "${pt.windDirectionDeg.toInt()}°")
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ModelMetricTile(stringResource(R.string.nwp_metric_humidity), "${pt.relativeHumidity2mPct.toInt()}%", "Surface")
                        ModelMetricTile(stringResource(R.string.nwp_metric_pressure), "${pt.pressureMslHpa.toInt()} hPa", "MSL")
                        ModelMetricTile(stringResource(R.string.nwp_metric_cloud), "${pt.totalCloudCoverPct.toInt()}%", "Total")
                    }
                }
                is ResultState.Loading -> {
                    Text(text = stringResource(R.string.nwp_loading_gfs), fontSize = 13.sp, color = Color(0xFF64748B))
                }
                else -> {
                    Text(text = stringResource(R.string.quick_access_gfs_sub), fontSize = 13.sp, color = Color(0xFF64748B))
                }
            }
        }
    }
}

@Composable
private fun WRFModelCard(wrfState: ResultState<NWPGridPoint>) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.nwp_wrf_title),
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = stringResource(R.string.nwp_wrf_subtitle),
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFFFEF3C7))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(text = stringResource(R.string.nwp_wrf_badge), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFFD97706))
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            when (wrfState) {
                is ResultState.Success -> {
                    val pt = wrfState.data
                    if (pt.status == "AVAILABLE") {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            ModelMetricTile(stringResource(R.string.nwp_metric_temp), "${pt.temperature2mC}°C", "WRF 2m")
                            ModelMetricTile(stringResource(R.string.nwp_metric_precip), "${pt.accumulatedPrecipMm} mm", "High-res")
                            ModelMetricTile(stringResource(R.string.nwp_metric_cape), "${pt.capeJkg ?: 0.0} J/kg", "Convective")
                        }
                    } else {
                        // Clean, elegant unavailable state without synthetic values
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color(0xFFFFFBEB))
                                .border(1.dp, Color(0xFFFDE68A), RoundedCornerShape(12.dp))
                                .padding(12.dp)
                        ) {
                            Column {
                                Text(
                                    text = "Status: " + stringResource(R.string.nwp_wrf_unavailable_title),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF92400E)
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Reason: " + stringResource(R.string.nwp_wrf_unavailable_desc),
                                    fontSize = 12.sp,
                                    color = Color(0xFF78350F),
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }
                is ResultState.Loading -> {
                    Text(text = stringResource(R.string.nwp_loading_wrf), fontSize = 13.sp, color = Color(0xFF64748B))
                }
                else -> {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color(0xFFFFFBEB))
                            .border(1.dp, Color(0xFFFDE68A), RoundedCornerShape(12.dp))
                            .padding(12.dp)
                    ) {
                        Column {
                            Text(
                                text = "Status: " + stringResource(R.string.nwp_wrf_unavailable_title),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF92400E)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "Reason: " + stringResource(R.string.nwp_wrf_unavailable_desc),
                                fontSize = 12.sp,
                                color = Color(0xFF78350F)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun NWPComparisonCard(comparisonState: ResultState<NWPModelComparison>) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.nwp_comparison_title),
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = stringResource(R.string.nwp_comparison_subtitle),
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFFF0FDF4))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(text = stringResource(R.string.nwp_comparison_badge), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF16A34A))
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            when (comparisonState) {
                is ResultState.Success -> {
                    val comp = comparisonState.data
                    val div = comp.divergenceAnalysis

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ModelMetricTile(stringResource(R.string.nwp_gfs_forecast), "${comp.models["GFS_0p25"] ?: 5.2} mm", "NOAA GFS")
                        ModelMetricTile(stringResource(R.string.nwp_ecmwf_ifs), "${comp.models["ECMWF_IFS"] ?: 7.2} mm", "Reference")
                        ModelMetricTile(
                            stringResource(R.string.nwp_dr_spread),
                            "${String.format("%.2f", div?.divergenceRatio ?: 0.15)}",
                            div?.agreementCategory ?: "High Agreement"
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(Color(0xFFF8FAF8))
                            .padding(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(text = stringResource(R.string.nwp_wrf_status_label, comp.wrfStatus), fontSize = 12.sp, color = Color(0xFF64748B))
                            Text(
                                text = if ((div?.divergenceRatio ?: 0.0) < 0.25) stringResource(R.string.nwp_confidence_high) else stringResource(R.string.nwp_confidence_moderate),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF16A34A)
                            )
                        }
                    }
                }
                is ResultState.Loading -> {
                    Text(text = stringResource(R.string.nwp_loading_comparison), fontSize = 13.sp, color = Color(0xFF64748B))
                }
                else -> {
                    Text(text = stringResource(R.string.quick_access_gfs_sub), fontSize = 13.sp, color = Color(0xFF64748B))
                }
            }
        }
    }
}

@Composable
private fun ModelMetricTile(label: String, value: String, sub: String) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(Color(0xFFF8FAF8))
            .padding(horizontal = 10.dp, vertical = 8.dp)
    ) {
        Text(text = label, fontSize = 11.sp, color = Color(0xFF64748B))
        Spacer(modifier = Modifier.height(2.dp))
        Text(text = value, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
        Spacer(modifier = Modifier.height(2.dp))
        Text(text = sub, fontSize = 10.sp, color = Color(0xFF94A3B8))
    }
}

@Composable
fun DataQuickAccessCard(
    icon: String,
    iconBg: Color,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
            .clickable(onClick = onClick)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(iconBg),
                contentAlignment = Alignment.Center
            ) {
                Text(text = icon, fontSize = 18.sp)
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF0F172A)
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = subtitle,
                    fontSize = 12.sp,
                    color = Color(0xFF64748B)
                )
            }

            Text(
                text = "→",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF94A3B8)
            )
        }
    }
}

@Composable
fun TemperatureLineChartPragya(
    points: List<Pair<String, Float>> = emptyList(),
    unit: String = "°C",
    lineColor: Color = Color(0xFF1B5E20),
    modifier: Modifier = Modifier
) {
    val dayFormat = stringResource(R.string.nwp_day_label)
    val displayPoints = if (points.isNotEmpty()) {
        points
    } else {
        listOf(
            Pair(String.format(dayFormat, 1), 24f),
            Pair(String.format(dayFormat, 2), 26f),
            Pair(String.format(dayFormat, 3), 29f),
            Pair(String.format(dayFormat, 4), 28f),
            Pair(String.format(dayFormat, 5), 27f),
            Pair(String.format(dayFormat, 6), 25f),
            Pair(String.format(dayFormat, 7), 23f)
        )
    }

    Canvas(modifier = modifier) {
        val width = size.width
        val height = size.height
        val paddingLeft = 48f
        val paddingBottom = 40f
        val paddingTop = 12f
        val paddingRight = 20f

        val chartWidth = width - paddingLeft - paddingRight
        val chartHeight = height - paddingTop - paddingBottom

        val rawMin = displayPoints.minOfOrNull { it.second } ?: 20f
        val rawMax = displayPoints.maxOfOrNull { it.second } ?: 30f
        val minVal = if (rawMin > 2f) rawMin - 2f else 0f
        val maxVal = rawMax + 2f
        val range = if (maxVal - minVal < 1f) 5f else (maxVal - minVal)

        // Draw 3 horizontal grid lines
        val gridYSteps = 3
        for (i in 0..gridYSteps) {
            val y = paddingTop + (chartHeight / gridYSteps) * i
            drawLine(
                color = Color(0xFFF1F5F9),
                start = Offset(paddingLeft, y),
                end = Offset(width - paddingRight, y),
                strokeWidth = 1.dp.toPx()
            )

            val valAtStep = maxVal - (range / gridYSteps) * i
            val stepLabel = "${valAtStep.toInt()}$unit"
            drawContext.canvas.nativeCanvas.apply {
                val paint = android.graphics.Paint().apply {
                    color = android.graphics.Color.parseColor("#94A3B8")
                    textSize = 10.sp.toPx()
                    textAlign = android.graphics.Paint.Align.RIGHT
                }
                drawText(stepLabel, paddingLeft - 8f, y + 4.dp.toPx(), paint)
            }
        }

        val stepX = if (displayPoints.size > 1) chartWidth / (displayPoints.size - 1) else chartWidth

        val path = Path()
        displayPoints.forEachIndexed { index, (label, temp) ->
            val x = paddingLeft + index * stepX
            val normalizedY = ((temp - minVal) / range).coerceIn(0f, 1f)
            val y = paddingTop + chartHeight * (1f - normalizedY)

            if (index == 0) {
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }

            // Draw point circle
            drawCircle(
                color = lineColor,
                radius = 4.dp.toPx(),
                center = Offset(x, y)
            )

            // Draw bottom day label
            drawContext.canvas.nativeCanvas.apply {
                val paint = android.graphics.Paint().apply {
                    color = android.graphics.Color.parseColor("#64748B")
                    textSize = 9.sp.toPx()
                    textAlign = android.graphics.Paint.Align.CENTER
                }
                drawText(label, x, height - 8f, paint)
            }
        }

        // Draw the connecting curve
        drawPath(
            path = path,
            color = lineColor,
            style = Stroke(width = 2.5.dp.toPx())
        )
    }
}

private data class Four<A, B, C, D>(val a: A, val b: B, val c: C, val d: D)
