package com.weathergpt.presentation.farmer

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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.R

@Composable
fun FarmerProfileScreen(
    viewModel: FarmerProfileViewModel,
    onSavedSuccessfully: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    var cropMenuExpanded by remember { mutableStateOf(false) }
    var stageMenuExpanded by remember { mutableStateOf(false) }
    var soilMenuExpanded by remember { mutableStateOf(false) }

    val crops = listOf(
        stringResource(R.string.crop_wheat),
        stringResource(R.string.crop_rice),
        stringResource(R.string.crop_cotton),
        stringResource(R.string.crop_mustard),
        stringResource(R.string.crop_sugarcane),
        stringResource(R.string.crop_maize)
    )
    val stages = listOf(
        stringResource(R.string.stage_sowing),
        stringResource(R.string.stage_vegetative),
        stringResource(R.string.stage_flowering),
        stringResource(R.string.stage_maturity)
    )
    val soils = listOf(
        stringResource(R.string.soil_alluvial),
        stringResource(R.string.soil_black_cotton),
        stringResource(R.string.soil_red_sandy),
        stringResource(R.string.soil_clay)
    )

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        // 1. Step Indicator Bar (1/4 with Progress Bar)
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "1/4",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF1B5E20)
            )
            Spacer(modifier = Modifier.width(12.dp))
            LinearProgressIndicator(
                progress = { 0.25f },
                color = Color(0xFF1B5E20),
                trackColor = Color(0xFFE2E8F0),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 2. Section Header with Sprout Emblem 🌱
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFE8F5E9)),
                contentAlignment = Alignment.Center
            ) {
                Text(text = "🌱", fontSize = 22.sp)
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column {
                Text(
                    text = stringResource(R.string.farmer_crop_header),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF0F172A)
                )
                Text(
                    text = stringResource(R.string.farmer_crop_subheader),
                    fontSize = 12.sp,
                    color = Color(0xFF64748B)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 3. Form Input Rows
        // Field 1: मुख्य फसल
        FormDropdownSelector(
            label = stringResource(R.string.label_crop),
            selectedOption = uiState.cropName,
            options = crops,
            expanded = cropMenuExpanded,
            onExpandedChange = { cropMenuExpanded = it },
            onSelect = {
                viewModel.setCrop(it)
                cropMenuExpanded = false
            }
        )

        Spacer(modifier = Modifier.height(14.dp))

        // Field 2: फसल की अवस्था
        FormDropdownSelector(
            label = stringResource(R.string.label_stage),
            selectedOption = uiState.cropStage,
            options = stages,
            expanded = stageMenuExpanded,
            onExpandedChange = { stageMenuExpanded = it },
            onSelect = {
                viewModel.setCropStage(it)
                stageMenuExpanded = false
            }
        )

        Spacer(modifier = Modifier.height(14.dp))

        // Field 3: मिट्टी का प्रकार
        FormDropdownSelector(
            label = stringResource(R.string.label_soil),
            selectedOption = uiState.soilType,
            options = soils,
            expanded = soilMenuExpanded,
            onExpandedChange = { soilMenuExpanded = it },
            onSelect = {
                viewModel.setSoilType(it)
                soilMenuExpanded = false
            }
        )

        Spacer(modifier = Modifier.height(14.dp))

        // Field 4: खेत का क्षेत्रफल (एकड़)
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 14.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = stringResource(R.string.label_area),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF0F172A),
                    modifier = Modifier.weight(1f)
                )

                OutlinedTextField(
                    value = uiState.fieldAreaText,
                    onValueChange = { viewModel.setFieldArea(it) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                        focusedBorderColor = Color(0xFF1B5E20),
                        unfocusedBorderColor = Color.Transparent
                    ),
                    modifier = Modifier.width(90.dp)
                )
            }
        }

        if (uiState.validationError != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = uiState.validationError ?: "",
                color = Color(0xFFDC2626),
                fontSize = 12.sp,
                modifier = Modifier.padding(start = 4.dp)
            )
        }

        Spacer(modifier = Modifier.weight(1f, fill = false))
        Spacer(modifier = Modifier.height(32.dp))

        // 4. Bottom Green Action Button
        Button(
            onClick = {
                if (viewModel.saveProfile()) {
                    onSavedSuccessfully()
                }
            },
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20)),
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = stringResource(R.string.btn_next),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Spacer(modifier = Modifier.width(6.dp))
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = "Next",
                    tint = Color.White,
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun FormDropdownSelector(
    label: String,
    selectedOption: String,
    options: List<String>,
    expanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    onSelect: (String) -> Unit
) {
    Box(modifier = Modifier.fillMaxWidth()) {
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
                .clickable { onExpandedChange(true) }
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 14.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = label,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF0F172A)
                )

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = selectedOption,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(
                        imageVector = Icons.Default.ArrowDropDown,
                        contentDescription = "Dropdown",
                        tint = Color(0xFF475569),
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }

        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { onExpandedChange(false) }
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(text = option, fontSize = 14.sp) },
                    onClick = { onSelect(option) }
                )
            }
        }
    }
}
