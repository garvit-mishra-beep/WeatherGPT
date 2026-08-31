package com.weathergpt.presentation.map

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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

@Composable
fun MapScreen(
    viewModel: MapViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    val layerTabs = listOf(
        WeatherMapLayer.RAIN to R.string.layer_rain,
        WeatherMapLayer.TEMPERATURE to R.string.layer_temp,
        WeatherMapLayer.WIND to R.string.layer_wind,
        WeatherMapLayer.HUMIDITY to R.string.layer_humidity
    )

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        // 1. Layer Selector Pills matching Pragya's Screen 4
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            layerTabs.forEach { (layer, labelRes) ->
                val isSelected = uiState.selectedLayer == layer
                val label = stringResource(labelRes)
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(if (isSelected) Color(0xFF1B5E20) else Color.White)
                        .border(1.dp, if (isSelected) Color(0xFF1B5E20) else Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                        .clickable { viewModel.setLayer(layer) }
                        .padding(horizontal = 14.dp, vertical = 7.dp)
                ) {
                    Text(
                        text = label,
                        fontSize = 12.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (isSelected) Color.White else Color(0xFF475569)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 2. Immersive Graphical Map Canvas with Floating Controls & Timeline Card
        TechnicalMapCanvas(
            specification = uiState.mapSpec,
            timelineStepMinutes = uiState.timelineStepMinutes,
            isPlaying = uiState.isPlaying,
            onTogglePlayback = { viewModel.togglePlayback() },
            onTimelineChange = { viewModel.setTimelineStep(it) },
            modifier = Modifier
                .fillMaxWidth()
                .height(440.dp)
        )

        Spacer(modifier = Modifier.height(16.dp))
    }
}
