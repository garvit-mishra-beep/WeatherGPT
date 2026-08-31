package com.weathergpt.presentation.map

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.res.stringResource
import com.weathergpt.R
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.weathergpt.core.map.RenderableMapSpecification

@Composable
fun TechnicalMapCanvas(
    specification: RenderableMapSpecification,
    timelineStepMinutes: Int = 0,
    isPlaying: Boolean = false,
    onTogglePlayback: () -> Unit = {},
    onTimelineChange: (Int) -> Unit = {},
    modifier: Modifier = Modifier
) {
    var zoomLevel by remember { mutableFloatStateOf(specification.zoom.toFloat().coerceIn(4f, 10f)) }

    val infiniteTransition = rememberInfiniteTransition(label = "RadarPulse")
    val pulseRadius by infiniteTransition.animateFloat(
        initialValue = 6f,
        targetValue = 24f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "PulseRadius"
    )
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 0.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "PulseAlpha"
    )

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(Color(0xFFF3F7FA))
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
    ) {
        // Geographical Canvas with Regional Towns & Radar Clouds
        Canvas(modifier = Modifier.fillMaxSize()) {
            val width = size.width
            val height = size.height

            // 1. Grid lines
            drawCoordinatesGrid(width, height)

            // 2. Regional landmass & towns
            drawRegionalMap(width, height)

            // 3. Realistic colorful Doppler radar precipitation clouds
            drawRadarReflectivityBlobs(width, height, timelineStepMinutes)

            // 4. Pulsing beacon at Jhansi
            val jhansiX = width * 0.48f
            val jhansiY = height * 0.54f

            drawCircle(
                color = Color(0xFF0284C7).copy(alpha = pulseAlpha),
                radius = pulseRadius * (zoomLevel / 5f),
                center = Offset(jhansiX, jhansiY)
            )
            drawCircle(
                color = Color(0xFF0284C7),
                radius = 6f,
                center = Offset(jhansiX, jhansiY)
            )
            drawCircle(
                color = Color.White,
                radius = 3f,
                center = Offset(jhansiX, jhansiY)
            )
        }

        // Floating Right Controls: GPS Target, Zoom (+), Zoom (−)
        Column(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .padding(end = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Card(
                shape = RoundedCornerShape(8.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.95f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                IconButton(
                    onClick = { /* Reset center */ },
                    modifier = Modifier.size(36.dp)
                ) {
                    Text(text = "⌖", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                }
            }

            Card(
                shape = RoundedCornerShape(8.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.95f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                IconButton(
                    onClick = { zoomLevel = (zoomLevel + 0.5f).coerceAtMost(10f) },
                    modifier = Modifier.size(36.dp)
                ) {
                    Text(text = "+", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                }
            }

            Card(
                shape = RoundedCornerShape(8.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.95f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                IconButton(
                    onClick = { zoomLevel = (zoomLevel - 0.5f).coerceAtLeast(4f) },
                    modifier = Modifier.size(36.dp)
                ) {
                    Text(text = "−", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                }
            }
        }

        // Floating Bottom Timeline Card matching Pragya's Screen 4
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
            elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .padding(10.dp)
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(16.dp))
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // Play / Pause Icon
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .background(Color(0xFF1B5E20))
                                .clickable { onTogglePlayback() },
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = if (isPlaying) "⏸" else "▶",
                                color = Color.White,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        Spacer(modifier = Modifier.width(10.dp))

                        Text(
                            text = "09:30 AM",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF0F172A)
                        )
                    }

                    Row(
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = "-2h", fontSize = 11.sp, color = Color(0xFF64748B))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(6.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF1B5E20))
                            )
                            Spacer(modifier = Modifier.width(3.dp))
                            Text(text = "Now", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B5E20))
                        }
                        Text(text = "+2h", fontSize = 11.sp, color = Color(0xFF64748B))
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                // Green Timeline Slider
                Slider(
                    value = timelineStepMinutes.toFloat(),
                    onValueChange = { onTimelineChange(it.toInt()) },
                    valueRange = -120f..120f,
                    steps = 7,
                    colors = SliderDefaults.colors(
                        thumbColor = Color(0xFF1B5E20),
                        activeTrackColor = Color(0xFF1B5E20),
                        inactiveTrackColor = Color(0xFFE2E8F0)
                    ),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(24.dp)
                )

                Spacer(modifier = Modifier.height(6.dp))

                // Reflectivity Color Legend Bar
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = stringResource(R.string.map_legend_light), fontSize = 10.sp, color = Color(0xFF64748B))
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .width(120.dp)
                                .height(6.dp)
                                .clip(RoundedCornerShape(3.dp))
                                .background(
                                    Brush.horizontalGradient(
                                        colors = listOf(
                                            Color(0xFF38BDF8), // light
                                            Color(0xFF22C55E), // moderate
                                            Color(0xFFEAB308), // heavy
                                            Color(0xFFEF4444)  // severe
                                        )
                                    )
                                )
                        )
                        Text(text = "◆ " + stringResource(R.string.map_legend_moderate), fontSize = 10.sp, fontWeight = FontWeight.Medium, color = Color(0xFF1B5E20))
                    }
                    Text(text = stringResource(R.string.map_legend_heavy), fontSize = 10.sp, color = Color(0xFF64748B))
                }
            }
        }
    }
}

private fun DrawScope.drawCoordinatesGrid(w: Float, h: Float) {
    val gridColor = Color(0xFFE2E8F0).copy(alpha = 0.7f)
    for (i in 1..4) {
        drawLine(
            color = gridColor,
            start = Offset(0f, h * (i / 5f)),
            end = Offset(w, h * (i / 5f)),
            strokeWidth = 1f
        )
        drawLine(
            color = gridColor,
            start = Offset(w * (i / 5f), 0f),
            end = Offset(w * (i / 5f), h),
            strokeWidth = 1f
        )
    }
}

private fun DrawScope.drawRegionalMap(w: Float, h: Float) {
    // Land contours
    val path = Path().apply {
        moveTo(w * 0.1f, h * 0.2f)
        cubicTo(w * 0.2f, h * 0.1f, w * 0.4f, h * 0.25f, w * 0.6f, h * 0.15f)
        cubicTo(w * 0.8f, h * 0.1f, w * 0.9f, h * 0.35f, w * 0.85f, h * 0.6f)
        cubicTo(w * 0.75f, h * 0.85f, w * 0.45f, h * 0.9f, w * 0.25f, h * 0.8f)
        close()
    }
    drawPath(
        path = path,
        color = Color(0xFFF1F5F9),
        style = Stroke(width = 2f)
    )

    // Town Labels matching Pragya's Map
    val paint = android.graphics.Paint().apply {
        color = android.graphics.Color.parseColor("#475569")
        textSize = 28f
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }

    val towns = listOf(
        Pair("Gwalior", Offset(w * 0.35f, h * 0.30f)),
        Pair("Datia", Offset(w * 0.43f, h * 0.38f)),
        Pair("Orai", Offset(w * 0.75f, h * 0.38f)),
        Pair("Jhansi", Offset(w * 0.46f, h * 0.52f)),
        Pair("Lalitpur", Offset(w * 0.25f, h * 0.58f)),
        Pair("Tikamgarh", Offset(w * 0.58f, h * 0.70f)),
        Pair("Chhatarpur", Offset(w * 0.68f, h * 0.78f))
    )

    towns.forEach { (name, pos) ->
        drawCircle(color = Color(0xFF94A3B8), radius = 3f, center = pos)
        drawContext.canvas.nativeCanvas.drawText(name, pos.x + 8f, pos.y + 8f, paint)
    }
}

private fun DrawScope.drawRadarReflectivityBlobs(w: Float, h: Float, timelineStep: Int) {
    // Dynamic offsets based on timeline slider
    val shiftX = timelineStep * 0.15f
    val shiftY = timelineStep * 0.08f

    // Primary cloud cluster over North-East (Orai / Jhansi)
    val cluster1 = Offset(w * 0.65f + shiftX, h * 0.38f + shiftY)
    drawCircle(
        brush = Brush.radialGradient(
            colors = listOf(
                Color(0xFFEAB308).copy(alpha = 0.85f),
                Color(0xFF22C55E).copy(alpha = 0.75f),
                Color(0xFF38BDF8).copy(alpha = 0.60f),
                Color.Transparent
            ),
            center = cluster1,
            radius = w * 0.22f
        ),
        radius = w * 0.22f,
        center = cluster1
    )

    // Secondary cluster over South-West (Lalitpur)
    val cluster2 = Offset(w * 0.30f + shiftX, h * 0.72f + shiftY)
    drawCircle(
        brush = Brush.radialGradient(
            colors = listOf(
                Color(0xFF22C55E).copy(alpha = 0.75f),
                Color(0xFF38BDF8).copy(alpha = 0.60f),
                Color.Transparent
            ),
            center = cluster2,
            radius = w * 0.18f
        ),
        radius = w * 0.18f,
        center = cluster2
    )
}
