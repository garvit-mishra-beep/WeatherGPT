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
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun FarmerProfileScreen(
    viewModel: FarmerProfileViewModel,
    onSavedSuccessfully: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        if (!uiState.isEditMode) {
            FarmerProfileSummaryView(
                uiState = uiState,
                onEditClick = { viewModel.setEditMode(true) }
            )
        } else {
            FarmerProfileEditForm(
                uiState = uiState,
                viewModel = viewModel,
                onSave = {
                    if (viewModel.saveProfile()) {
                        onSavedSuccessfully()
                    }
                },
                onCancel = { viewModel.setEditMode(false) }
            )
        }

        // Min 88dp bottom clearance to prevent overlap with bottom navigation bar
        Spacer(modifier = Modifier.height(96.dp))
    }
}

// ============================================================================
// 1. SUMMARY VIEW (Read Mode)
// ============================================================================
@Composable
private fun FarmerProfileSummaryView(
    uiState: FarmerProfileUiState,
    onEditClick: () -> Unit
) {
    // Header
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = "Farmer Profile",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF0F172A)
            )
            Text(
                text = "Personalized Agricultural Context",
                fontSize = 13.sp,
                color = Color(0xFF64748B)
            )
        }

        Button(
            onClick = onEditClick,
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20))
        ) {
            Icon(Icons.Default.Edit, contentDescription = "Edit", tint = Color.White, modifier = Modifier.size(16.dp))
            Spacer(modifier = Modifier.width(6.dp))
            Text("Edit Profile", fontSize = 13.sp, fontWeight = FontWeight.Bold)
        }
    }

    if (uiState.isSavedSuccessfully) {
        Spacer(modifier = Modifier.height(12.dp))
        Card(
            shape = RoundedCornerShape(10.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Default.Check, contentDescription = "Saved", tint = Color(0xFF1B5E20), modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Profile saved. Agronomic decisions are now personalized.",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF1B5E20)
                )
            }
        }
    }

    Spacer(modifier = Modifier.height(18.dp))

    // Section 1: Farmer Information Card
    ProfileSummaryCard(
        title = "SECTION 1 — FARMER INFORMATION",
        icon = "👤",
        items = listOf(
            "Full Name" to uiState.fullName,
            "Mobile" to uiState.mobileNumber.ifBlank { "Not provided" },
            "Farmer ID" to uiState.farmerId.ifBlank { "Not provided" },
            "Village" to uiState.village.ifBlank { "Not provided" },
            "District" to uiState.district,
            "State" to uiState.state,
            "Pincode" to uiState.pincode.ifBlank { "Not provided" }
        )
    )

    Spacer(modifier = Modifier.height(14.dp))

    // Section 2: Farm / Field Information Card
    ProfileSummaryCard(
        title = "SECTION 2 — FARM & FIELD DETAILS",
        icon = "🏞️",
        items = listOf(
            "Field Name" to uiState.fieldName.ifBlank { "Not provided" },
            "Plot Number" to uiState.plotNumber.ifBlank { "Not provided" },
            "Survey Number" to uiState.surveyNumber.ifBlank { "Not provided" },
            "Farm Area" to "${uiState.fieldAreaText} ${uiState.areaUnit}"
        )
    )

    Spacer(modifier = Modifier.height(14.dp))

    // Section 3: Crop Information Card
    ProfileSummaryCard(
        title = "SECTION 3 — CROP INFORMATION",
        icon = "🌾",
        items = listOf(
            "Current Crop" to uiState.cropName,
            "Variety" to uiState.variety.ifBlank { "Standard / Local" },
            "Crop Growth Stage" to uiState.cropStage,
            "Sowing Date" to uiState.sowingDate.ifBlank { "Not recorded" },
            "Expected Harvest Date" to uiState.expectedHarvestDate.ifBlank { "Not recorded" },
            "Irrigation Type" to uiState.cropIrrigationType
        )
    )

    Spacer(modifier = Modifier.height(14.dp))

    // Section 4: Soil Information Card
    ProfileSummaryCard(
        title = "SECTION 4 — SOIL CHARACTERISTICS",
        icon = "🧱",
        items = listOf(
            "Soil Type" to uiState.soilType,
            "Moisture Availability" to uiState.soilMoistureAvailability
        )
    )

    Spacer(modifier = Modifier.height(14.dp))

    // Section 5: Farm Practices Card
    ProfileSummaryCard(
        title = "SECTION 5 — FARM PRACTICES",
        icon = "🚜",
        items = listOf(
            "Irrigation Method" to uiState.irrigationMethod,
            "Primary Activity" to uiState.farmingActivity
        )
    )

    Spacer(modifier = Modifier.height(14.dp))

    // Section 6: Preferences Card
    ProfileSummaryCard(
        title = "SECTION 6 — PREFERENCES",
        icon = "⚙️",
        items = listOf(
            "Preferred Language" to uiState.preferredLanguage,
            "Temperature Unit" to uiState.temperatureUnit,
            "Weather Alerts Notifications" to if (uiState.notificationsEnabled) "Enabled" else "Disabled"
        )
    )

    Spacer(modifier = Modifier.height(24.dp))

    Button(
        onClick = onEditClick,
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20)),
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp)
    ) {
        Icon(Icons.Default.Edit, contentDescription = null, tint = Color.White)
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "Edit Profile",
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
    }
}

// ============================================================================
// 2. EDIT FORM (Interactive Multi-Section Form)
// ============================================================================
@Composable
private fun FarmerProfileEditForm(
    uiState: FarmerProfileUiState,
    viewModel: FarmerProfileViewModel,
    onSave: () -> Unit,
    onCancel: () -> Unit
) {
    // Dropdown options
    val cropsList = listOf("Wheat", "Rice", "Cotton", "Mustard", "Sugarcane", "Maize", "Gram", "Soybean", "Bajra")
    val stagesList = listOf("Seedling", "Vegetative", "Flowering", "Fruiting", "Maturity", "Harvest", "Unknown")
    val soilsList = listOf("Alluvial", "Black Soil", "Red Soil", "Loamy", "Sandy", "Clay", "Other", "Unknown")
    val moistureList = listOf("Irrigated", "Rainfed", "Partially Irrigated", "Unknown")
    val irrigationMethodsList = listOf("Drip", "Sprinkler", "Flood", "Furrow", "Rainfed", "Other")
    val activitiesList = listOf("Crop Production", "Horticulture", "Livestock", "Mixed Farming")
    val areaUnitsList = listOf("hectare", "acre")
    val languagesList = listOf("English", "Hindi")
    val tempUnitsList = listOf("Celsius", "Fahrenheit")

    // Form Title
    Text(
        text = "Farmer Profile",
        fontSize = 24.sp,
        fontWeight = FontWeight.Bold,
        color = Color(0xFF0F172A)
    )
    Text(
        text = "Enter field, crop, and soil parameters to personalize advisory decisions",
        fontSize = 13.sp,
        color = Color(0xFF64748B)
    )

    Spacer(modifier = Modifier.height(16.dp))

    // Validation Error Banner
    if (uiState.validationError != null) {
        Card(
            shape = RoundedCornerShape(10.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFFEE2E2)),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFEF4444), RoundedCornerShape(10.dp))
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Default.Warning, contentDescription = "Error", tint = Color(0xFFDC2626), modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = uiState.validationError ?: "",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFFB91C1C)
                )
            }
        }
        Spacer(modifier = Modifier.height(16.dp))
    }

    // SECTION 1 — FARMER INFORMATION
    FormSectionCard(title = "SECTION 1 — FARMER INFORMATION", icon = "👤") {
        FormTextField(
            label = "Full Name",
            value = uiState.fullName,
            onValueChange = { viewModel.setFullName(it) },
            isRequired = true
        )
        Spacer(modifier = Modifier.height(10.dp))
        FormTextField(
            label = "Mobile Number",
            value = uiState.mobileNumber,
            onValueChange = { viewModel.setMobileNumber(it) },
            keyboardType = KeyboardType.Phone,
            placeholder = "10-digit mobile number"
        )
        Spacer(modifier = Modifier.height(10.dp))
        FormTextField(
            label = "Village",
            value = uiState.village,
            onValueChange = { viewModel.setVillage(it) }
        )
        Spacer(modifier = Modifier.height(10.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "District",
                    value = uiState.district,
                    onValueChange = { viewModel.setDistrict(it) },
                    isRequired = true
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "State",
                    value = uiState.state,
                    onValueChange = { viewModel.setState(it) },
                    isRequired = true
                )
            }
        }
        Spacer(modifier = Modifier.height(10.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "Pincode",
                    value = uiState.pincode,
                    onValueChange = { viewModel.setPincode(it) },
                    keyboardType = KeyboardType.Number,
                    placeholder = "6 digits"
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "Farmer ID (Optional)",
                    value = uiState.farmerId,
                    onValueChange = { viewModel.setFarmerId(it) },
                    placeholder = "e.g. PMKISAN-984"
                )
            }
        }
    }

    Spacer(modifier = Modifier.height(16.dp))

    // SECTION 2 — FARM / FIELD INFORMATION
    FormSectionCard(title = "SECTION 2 — FARM & FIELD DETAILS", icon = "🏞️") {
        FormTextField(
            label = "Field Name",
            value = uiState.fieldName,
            onValueChange = { viewModel.setFieldName(it) },
            placeholder = "e.g. North Plot"
        )
        Spacer(modifier = Modifier.height(10.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "Plot Number",
                    value = uiState.plotNumber,
                    onValueChange = { viewModel.setPlotNumber(it) }
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "Survey Number",
                    value = uiState.surveyNumber,
                    onValueChange = { viewModel.setSurveyNumber(it) }
                )
            }
        }
        Spacer(modifier = Modifier.height(10.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1.2f)) {
                FormTextField(
                    label = "Farm Area",
                    value = uiState.fieldAreaText,
                    onValueChange = { viewModel.setFieldArea(it) },
                    isRequired = true,
                    keyboardType = KeyboardType.Decimal
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                FormDropdownSelector(
                    label = "Unit",
                    selectedOption = uiState.areaUnit,
                    options = areaUnitsList,
                    onSelect = { viewModel.setAreaUnit(it) }
                )
            }
        }
    }

    Spacer(modifier = Modifier.height(16.dp))

    // SECTION 3 — CROP INFORMATION
    FormSectionCard(title = "SECTION 3 — CROP INFORMATION", icon = "🌾") {
        FormDropdownSelector(
            label = "Crop",
            selectedOption = uiState.cropName,
            options = cropsList,
            isRequired = true,
            onSelect = { viewModel.setCrop(it) }
        )
        Spacer(modifier = Modifier.height(10.dp))
        FormTextField(
            label = "Variety",
            value = uiState.variety,
            onValueChange = { viewModel.setVariety(it) },
            placeholder = "e.g. Sharbati, HD-2967"
        )
        Spacer(modifier = Modifier.height(10.dp))
        FormDropdownSelector(
            label = "Crop Growth Stage",
            selectedOption = uiState.cropStage,
            options = stagesList,
            isRequired = true,
            onSelect = { viewModel.setCropStage(it) }
        )
        Spacer(modifier = Modifier.height(10.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "Sowing Date",
                    value = uiState.sowingDate,
                    onValueChange = { viewModel.setSowingDate(it) },
                    placeholder = "YYYY-MM-DD"
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                FormTextField(
                    label = "Exp. Harvest Date",
                    value = uiState.expectedHarvestDate,
                    onValueChange = { viewModel.setExpectedHarvestDate(it) },
                    placeholder = "YYYY-MM-DD"
                )
            }
        }
        Spacer(modifier = Modifier.height(10.dp))
        FormDropdownSelector(
            label = "Irrigation Type",
            selectedOption = uiState.cropIrrigationType,
            options = irrigationMethodsList,
            onSelect = { viewModel.setCropIrrigationType(it) }
        )
    }

    Spacer(modifier = Modifier.height(16.dp))

    // SECTION 4 — SOIL INFORMATION
    FormSectionCard(title = "SECTION 4 — SOIL CHARACTERISTICS", icon = "🧱") {
        FormDropdownSelector(
            label = "Soil Type",
            selectedOption = uiState.soilType,
            options = soilsList,
            onSelect = { viewModel.setSoilType(it) }
        )
        Spacer(modifier = Modifier.height(10.dp))
        FormDropdownSelector(
            label = "Soil Moisture Availability",
            selectedOption = uiState.soilMoistureAvailability,
            options = moistureList,
            onSelect = { viewModel.setSoilMoistureAvailability(it) }
        )
    }

    Spacer(modifier = Modifier.height(16.dp))

    // SECTION 5 — FARM PRACTICES
    FormSectionCard(title = "SECTION 5 — FARM PRACTICES", icon = "🚜") {
        FormDropdownSelector(
            label = "Irrigation Method",
            selectedOption = uiState.irrigationMethod,
            options = irrigationMethodsList,
            onSelect = { viewModel.setIrrigationMethod(it) }
        )
        Spacer(modifier = Modifier.height(10.dp))
        FormDropdownSelector(
            label = "Primary Farming Activity",
            selectedOption = uiState.farmingActivity,
            options = activitiesList,
            onSelect = { viewModel.setFarmingActivity(it) }
        )
    }

    Spacer(modifier = Modifier.height(16.dp))

    // SECTION 6 — PREFERENCES
    FormSectionCard(title = "SECTION 6 — PREFERENCES", icon = "⚙️") {
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1f)) {
                FormDropdownSelector(
                    label = "Language",
                    selectedOption = uiState.preferredLanguage,
                    options = languagesList,
                    onSelect = { viewModel.setPreferredLanguage(it) }
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                FormDropdownSelector(
                    label = "Temp Unit",
                    selectedOption = uiState.temperatureUnit,
                    options = tempUnitsList,
                    onSelect = { viewModel.setTemperatureUnit(it) }
                )
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Weather Warning Notifications",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF0F172A)
                )
                Text(
                    text = "Receive local warning alerts for this profile",
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )
            }
            Switch(
                checked = uiState.notificationsEnabled,
                onCheckedChange = { viewModel.setNotificationsEnabled(it) },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.White,
                    checkedTrackColor = Color(0xFF1B5E20)
                )
            )
        }
    }

    Spacer(modifier = Modifier.height(24.dp))

    // Action Buttons
    Button(
        onClick = onSave,
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20)),
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp)
    ) {
        Icon(Icons.Default.Check, contentDescription = null, tint = Color.White)
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "SAVE FARMER PROFILE",
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
    }

    Spacer(modifier = Modifier.height(10.dp))

    OutlinedButton(
        onClick = onCancel,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
    ) {
        Text("Cancel", fontSize = 14.sp, color = Color(0xFF475569))
    }
}

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

@Composable
private fun FormSectionCard(
    title: String,
    icon: String,
    content: @Composable () -> Unit
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = icon, fontSize = 16.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = title,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1B5E20)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(color = Color(0xFFF1F5F9))
            Spacer(modifier = Modifier.height(12.dp))
            content()
        }
    }
}

@Composable
private fun FormTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    isRequired: Boolean = false,
    placeholder: String = "",
    keyboardType: KeyboardType = KeyboardType.Text
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Row {
            Text(
                text = label,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF334155)
            )
            if (isRequired) {
                Text(
                    text = " *",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFDC2626)
                )
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            singleLine = true,
            placeholder = {
                if (placeholder.isNotBlank()) {
                    Text(text = placeholder, fontSize = 13.sp, color = Color(0xFF94A3B8))
                }
            },
            keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Color(0xFF1B5E20),
                unfocusedBorderColor = Color(0xFFCBD5E1),
                focusedContainerColor = Color.White,
                unfocusedContainerColor = Color.White
            ),
            shape = RoundedCornerShape(10.dp),
            modifier = Modifier.fillMaxWidth()
        )
    }
}

@Composable
private fun FormDropdownSelector(
    label: String,
    selectedOption: String,
    options: List<String>,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
    isRequired: Boolean = false
) {
    var expanded by remember { mutableStateOf(false) }

    Column(modifier = modifier.fillMaxWidth()) {
        Row {
            Text(
                text = label,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF334155)
            )
            if (isRequired) {
                Text(
                    text = " *",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFDC2626)
                )
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        Box(modifier = Modifier.fillMaxWidth()) {
            Card(
                shape = RoundedCornerShape(10.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFCBD5E1), RoundedCornerShape(10.dp))
                    .clickable { expanded = true }
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 13.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = selectedOption.ifBlank { "Select" },
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        color = if (selectedOption.isNotBlank()) Color(0xFF0F172A) else Color(0xFF94A3B8)
                    )
                    Icon(
                        imageVector = Icons.Default.ArrowDropDown,
                        contentDescription = "Dropdown",
                        tint = Color(0xFF64748B),
                        modifier = Modifier.size(20.dp)
                    )
                }
            }

            DropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false }
            ) {
                options.forEach { option ->
                    DropdownMenuItem(
                        text = { Text(text = option, fontSize = 13.sp) },
                        onClick = {
                            onSelect(option)
                            expanded = false
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun ProfileSummaryCard(
    title: String,
    icon: String,
    items: List<Pair<String, String>>
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = icon, fontSize = 16.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = title,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1B5E20)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(color = Color(0xFFF1F5F9))
            Spacer(modifier = Modifier.height(8.dp))

            items.forEachIndexed { index, (k, v) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = k, fontSize = 13.sp, color = Color(0xFF64748B))
                    Text(text = v, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF0F172A))
                }
                if (index < items.size - 1) {
                    HorizontalDivider(color = Color(0xFFF8FAFC), thickness = 0.5.dp)
                }
            }
        }
    }
}
