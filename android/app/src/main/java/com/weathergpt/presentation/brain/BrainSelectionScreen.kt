package com.weathergpt.presentation.brain

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import com.weathergpt.presentation.components.BrainCard
import com.weathergpt.presentation.components.IntelligenceBrain
import com.weathergpt.presentation.components.PrimaryButton

@Composable
fun BrainSelectionScreen(
    viewModel: BrainSelectionViewModel,
    onBrainSelectedAndConfirmed: (IntelligenceBrain) -> Unit,
    modifier: Modifier = Modifier
) {
    val selectedBrain by viewModel.selectedBrain.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        // Screen Subtitle Note
        Text(
            text = stringResource(R.string.brain_selection_subtitle),
            style = MaterialTheme.typography.bodyMedium,
            color = Color(0xFF64748B),
            modifier = Modifier.padding(bottom = 16.dp, start = 2.dp)
        )

        // Brain Selection Cards List
        Column(
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            IntelligenceBrain.entries.forEach { brain ->
                BrainCard(
                    brain = brain,
                    isSelected = selectedBrain == brain,
                    onSelect = {
                        viewModel.selectBrain(brain)
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Bottom Auto Brain Learning Note Box (from Pragya's design)
        Card(
            shape = RoundedCornerShape(14.dp),
            colors = CardDefaults.cardColors(
                containerColor = Color(0xFFFFFBEB),
                contentColor = Color(0xFF78350F)
            ),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFFDE68A), RoundedCornerShape(14.dp))
        ) {
            Row(
                modifier = Modifier.padding(14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFFEF3C7)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "⚡", fontSize = 16.sp)
                }
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    text = stringResource(R.string.brain_note_desc),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF92400E),
                    lineHeight = 16.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Apply and confirm action button
        PrimaryButton(
            text = "${stringResource(R.string.btn_apply_save)} (${stringResource(selectedBrain.titleResId)})",
            onClick = { onBrainSelectedAndConfirmed(selectedBrain) }
        )

        Spacer(modifier = Modifier.height(16.dp))
    }
}
