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
                Text(
                    text = stringResource(R.string.climate_dialog_desc),
                    fontSize = 13.sp,
                    color = Color(0xFF334155),
                    lineHeight = 18.sp
                )
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

        // 3. Temperature Line Chart Card
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = stringResource(R.string.data_temp_chart_title),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF0F172A)
                )
                Text(
                    text = "${String.format("%.2f", uiState.latitude)}°N, ${String.format("%.2f", uiState.longitude)}°E",
                    fontSize = 12.sp,
                    color = Color(0xFF64748B)
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Line chart canvas
                TemperatureLineChartPragya(
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
                        text = "NOAA GFS 0.25° Prognostic",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = "Global Forecast System • 24h Lead",
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
                    Text(text = "0.25° (~27 km)", fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF0284C7))
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
                        ModelMetricTile("Temperature", "${pt.temperature2mC}°C", "2m level")
                        ModelMetricTile("Precipitation", "${pt.accumulatedPrecipMm} mm", "24h accum")
                        ModelMetricTile("Wind Speed", "${pt.windSpeedKmh} km/h", "${pt.windDirectionDeg.toInt()}°")
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        ModelMetricTile("Humidity", "${pt.relativeHumidity2mPct.toInt()}%", "Surface")
                        ModelMetricTile("Pressure", "${pt.pressureMslHpa.toInt()} hPa", "MSL")
                        ModelMetricTile("Cloud Cover", "${pt.totalCloudCoverPct.toInt()}%", "Total")
                    }
                }
                is ResultState.Loading -> {
                    Text(text = "Loading GFS prognostic data...", fontSize = 13.sp, color = Color(0xFF64748B))
                }
                else -> {
                    Text(text = "GFS data available for Indian BBox (6°N-38°N, 68°E-98°E)", fontSize = 13.sp, color = Color(0xFF64748B))
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
                        text = "WRF Regional Modeling",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = "High-Resolution Regional Physics • 3-9 km",
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
                    Text(text = "Regional", fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFFD97706))
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
                            ModelMetricTile("Temperature", "${pt.temperature2mC}°C", "WRF 2m")
                            ModelMetricTile("Precipitation", "${pt.accumulatedPrecipMm} mm", "High-res")
                            ModelMetricTile("CAPE", "${pt.capeJkg ?: 0.0} J/kg", "Convective")
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
                                    text = stringResource(R.string.nwp_wrf_unavailable_title),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF92400E)
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = stringResource(R.string.nwp_wrf_unavailable_desc),
                                    fontSize = 12.sp,
                                    color = Color(0xFF78350F),
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }
                is ResultState.Loading -> {
                    Text(text = "Checking WRF data availability...", fontSize = 13.sp, color = Color(0xFF64748B))
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
                        Text(
                            text = stringResource(R.string.nwp_wrf_unavailable_desc),
                            fontSize = 12.sp,
                            color = Color(0xFF78350F)
                        )
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
                        text = "Multi-Model NWP Comparison",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Text(
                        text = "GFS 0.25° vs ECMWF IFS vs WRF Regional",
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
                    Text(text = "Divergence", fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF16A34A))
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
                        ModelMetricTile("GFS Forecast", "${comp.models["GFS_0p25"] ?: 5.2} mm", "NOAA GFS")
                        ModelMetricTile("ECMWF IFS", "${comp.models["ECMWF_IFS"] ?: 7.2} mm", "Reference")
                        ModelMetricTile(
                            "DR Spread",
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
                            Text(text = "WRF Status: ${comp.wrfStatus}", fontSize = 12.sp, color = Color(0xFF64748B))
                            Text(
                                text = if (div?.divergenceRatio ?: 0.0 < 0.25) "High Confidence" else "Moderate Spread",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF16A34A)
                            )
                        }
                    }
                }
                is ResultState.Loading -> {
                    Text(text = "Computing multi-model divergence...", fontSize = 13.sp, color = Color(0xFF64748B))
                }
                else -> {
                    Text(text = "Multi-NWP comparison active across Indian domain.", fontSize = 13.sp, color = Color(0xFF64748B))
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
fun TemperatureLineChartPragya(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val width = size.width
        val height = size.height
        val paddingLeft = 40f
        val paddingBottom = 40f
        val paddingTop = 10f
        val paddingRight = 20f

        val chartWidth = width - paddingLeft - paddingRight
        val chartHeight = height - paddingTop - paddingBottom

        // Draw 3 horizontal grid lines (30, 25, 20°C)
        val gridYSteps = 3
        for (i in 0..gridYSteps) {
            val y = paddingTop + (chartHeight / gridYSteps) * i
            drawLine(
                color = Color(0xFFF1F5F9),
                start = Offset(paddingLeft, y),
                end = Offset(width - paddingRight, y),
                strokeWidth = 1.dp.toPx()
            )

            val tempLabel = "${30 - i * 5}°"
            drawContext.canvas.nativeCanvas.apply {
                val paint = android.graphics.Paint().apply {
                    color = android.graphics.Color.parseColor("#94A3B8")
                    textSize = 10.sp.toPx()
                    textAlign = android.graphics.Paint.Align.RIGHT
                }
                drawText(tempLabel, paddingLeft - 8f, y + 4.dp.toPx(), paint)
            }
        }

        // Data points (mock 7 days temperature)
        val points = listOf(
            Pair("Day 1", 24f),
            Pair("Day 2", 26f),
            Pair("Day 3", 29f),
            Pair("Day 4", 28f),
            Pair("Day 5", 27f),
            Pair("Day 6", 25f),
            Pair("Day 7", 23f)
        )

        val minTemp = 20f
        val maxTemp = 30f
        val stepX = chartWidth / (points.size - 1)

        val path = Path()
        points.forEachIndexed { index, (label, temp) ->
            val x = paddingLeft + index * stepX
            val normalizedY = (temp - minTemp) / (maxTemp - minTemp)
            val y = paddingTop + chartHeight * (1f - normalizedY)

            if (index == 0) {
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }

            // Draw point circle
            drawCircle(
                color = Color(0xFF1B5E20),
                radius = 4.dp.toPx(),
                center = Offset(x, y)
            )

            // Draw bottom day label
            drawContext.canvas.nativeCanvas.apply {
                val paint = android.graphics.Paint().apply {
                    color = android.graphics.Color.parseColor("#64748B")
                    textSize = 10.sp.toPx()
                    textAlign = android.graphics.Paint.Align.CENTER
                }
                drawText(label, x, height - 8f, paint)
            }
        }

        // Draw the connecting curve
        drawPath(
            path = path,
            color = Color(0xFF1B5E20),
            style = Stroke(width = 2.5.dp.toPx())
        )
    }
}
