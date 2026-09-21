package com.weathergpt.presentation.components

import androidx.annotation.StringRes
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.weathergpt.R

enum class IntelligenceBrain(
    val id: String,
    val title: String,
    val displayTag: String,
    @StringRes val titleResId: Int,
    @StringRes val descResId: Int,
    val emojiIcon: String,
    val iconBgColor: Color
) {
    AUTO(
        id = "auto",
        title = "Auto",
        displayTag = "Auto",
        titleResId = R.string.brain_auto_title,
        descResId = R.string.brain_auto_desc,
        emojiIcon = "🤖",
        iconBgColor = Color(0xFFE8F5E9)
    ),
    GENERAL(
        id = "general",
        title = "General",
        displayTag = "General",
        titleResId = R.string.brain_general_title,
        descResId = R.string.brain_general_desc,
        emojiIcon = "💬",
        iconBgColor = Color(0xFFF3E8FF)
    ),
    FARMER(
        id = "farmer",
        title = "Farmer",
        displayTag = "Farmer",
        titleResId = R.string.brain_farmer_title,
        descResId = R.string.brain_farmer_desc,
        emojiIcon = "🌾",
        iconBgColor = Color(0xFFE8F5E9)
    ),
    RESEARCHER(
        id = "researcher",
        title = "Researcher",
        displayTag = "Researcher",
        titleResId = R.string.brain_researcher_title,
        descResId = R.string.brain_researcher_desc,
        emojiIcon = "🧪",
        iconBgColor = Color(0xFFF3E8FF)
    ),
    ANALYST(
        id = "analyst",
        title = "Analyst",
        displayTag = "Analyst",
        titleResId = R.string.brain_analyst_title,
        descResId = R.string.brain_analyst_desc,
        emojiIcon = "📊",
        iconBgColor = Color(0xFFEFF6FF)
    )
}

@Composable
fun BrainCard(
    brain: IntelligenceBrain,
    isSelected: Boolean,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier
) {
    val containerColor = if (isSelected) Color(0xFFF1F8F4) else Color.White
    val borderColor = if (isSelected) Color(0xFF2E7D32) else Color(0xFFE2E8F0)
    val borderWidth = if (isSelected) 1.5.dp else 1.dp

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = containerColor),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isSelected) 2.dp else 0.5.dp),
        modifier = modifier
            .fillMaxWidth()
            .border(borderWidth, borderColor, RoundedCornerShape(16.dp))
            .clickable { onSelect() }
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                modifier = Modifier.weight(1f),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Leading Brain Emblem Icon
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(CircleShape)
                        .background(brain.iconBgColor),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = brain.emojiIcon, fontSize = 20.sp)
                }

                Spacer(modifier = Modifier.width(14.dp))

                Column {
                    Text(
                        text = stringResource(brain.titleResId),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF0F172A)
                    )
                    Spacer(modifier = Modifier.height(3.dp))
                    Text(
                        text = stringResource(brain.descResId),
                        fontSize = 12.sp,
                        color = Color(0xFF475569),
                        lineHeight = 16.sp
                    )
                }
            }

            Spacer(modifier = Modifier.width(10.dp))

            // Selection Indicator: Green circle with checkmark when selected
            if (isSelected) {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF2E7D32)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = stringResource(R.string.cd_selected),
                        tint = Color.White,
                        modifier = Modifier.size(16.dp)
                    )
                }
            } else {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .border(1.5.dp, Color(0xFFCBD5E1), CircleShape)
                )
            }
        }
    }
}
