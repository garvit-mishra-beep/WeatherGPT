package com.weathergpt.presentation.farmer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.weathergpt.WeatherGPTApplication
import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

import com.weathergpt.domain.model.farmer.FarmerProfile

data class FarmerProfileUiState(
    // Mode
    val isEditMode: Boolean = false,
    val isSavedSuccessfully: Boolean = false,
    val validationError: String? = null,

    // Section 1 — Farmer Information
    val fullName: String = "Gwalior Farmer",
    val mobileNumber: String = "",
    val farmerId: String = "",
    val village: String = "Morar",
    val district: String = "Gwalior",
    val state: String = "Madhya Pradesh",
    val pincode: String = "",

    // Section 2 — Farm / Field Information
    val fieldName: String = "Field Alpha",
    val plotNumber: String = "",
    val surveyNumber: String = "",
    val fieldAreaText: String = "2.5",
    val areaUnit: String = "hectare",

    // Section 3 — Crop Information
    val cropName: String = "Wheat",
    val variety: String = "Sharbati",
    val cropStage: String = "Vegetative",
    val sowingDate: String = "",
    val expectedHarvestDate: String = "",
    val cropIrrigationType: String = "Drip",

    // Section 4 — Soil Information
    val soilType: String = "Alluvial / Loam",
    val soilMoistureAvailability: String = "Irrigated",

    // Section 5 — Farm Practices
    val irrigationMethod: String = "Drip",
    val farmingActivity: String = "Crop Production",

    // Section 6 — Preferences
    val preferredLanguage: String = "English",
    val temperatureUnit: String = "Celsius",
    val notificationsEnabled: Boolean = true,

    // Coordinates & Advisories
    val latitude: Double = 26.2183,
    val longitude: Double = 78.1828,
    val irrigationState: ResultState<IrrigationAdvisory> = ResultState.Idle,
    val sprayState: ResultState<SpraySuitability> = ResultState.Idle
)

class FarmerProfileViewModel(
    private val repository: WeatherGPTRepository,
    private val locationManager: SharedLocationManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(FarmerProfileUiState())
    val uiState: StateFlow<FarmerProfileUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            loadSavedProfile()
            locationManager.locationState.collectLatest { loc ->
                _uiState.value = _uiState.value.copy(
                    latitude = loc.latitude,
                    longitude = loc.longitude
                )
                loadAdvisories()
            }
        }
    }

    private suspend fun loadSavedProfile() {
        when (val res = repository.getFarmerProfile()) {
            is ResultState.Success -> {
                val p = res.data
                val current = _uiState.value
                _uiState.value = current.copy(
                    fullName = if (current.fullName != "Gwalior Farmer") current.fullName else p.fullName.ifBlank { "Gwalior Farmer" },
                    mobileNumber = current.mobileNumber.ifBlank { p.mobileNumber ?: "" },
                    farmerId = current.farmerId.ifBlank { p.farmerId ?: "" },
                    village = if (current.village != "Morar") current.village else p.village ?: "Morar",
                    district = if (current.district != "Gwalior") current.district else p.district.ifBlank { "Gwalior" },
                    state = if (current.state != "Madhya Pradesh") current.state else p.state.ifBlank { "Madhya Pradesh" },
                    pincode = current.pincode.ifBlank { p.pincode ?: "" },
                    fieldName = if (current.fieldName != "Field Alpha") current.fieldName else p.fieldName ?: "Field Alpha",
                    plotNumber = current.plotNumber.ifBlank { p.plotNumber ?: "" },
                    surveyNumber = current.surveyNumber.ifBlank { p.surveyNumber ?: "" },
                    fieldAreaText = if (current.fieldAreaText != "2.5") current.fieldAreaText else p.farmArea?.toString() ?: "2.5",
                    areaUnit = if (current.areaUnit != "hectare") current.areaUnit else p.areaUnit ?: "hectare",
                    cropName = if (current.cropName != "Wheat") current.cropName else p.crop.ifBlank { "Wheat" },
                    variety = if (current.variety != "Sharbati") current.variety else p.variety ?: "Sharbati",
                    cropStage = if (current.cropStage != "Vegetative") current.cropStage else p.cropStage.ifBlank { "Vegetative" },
                    sowingDate = current.sowingDate.ifBlank { p.sowingDate ?: "" },
                    expectedHarvestDate = current.expectedHarvestDate.ifBlank { p.expectedHarvestDate ?: "" },
                    cropIrrigationType = if (current.cropIrrigationType != "Drip") current.cropIrrigationType else p.irrigationType ?: "Drip",
                    soilType = if (current.soilType != "Alluvial / Loam") current.soilType else p.soilType ?: "Alluvial / Loam",
                    soilMoistureAvailability = if (current.soilMoistureAvailability != "Irrigated") current.soilMoistureAvailability else p.soilMoistureAvailability ?: "Irrigated",
                    irrigationMethod = if (current.irrigationMethod != "Drip") current.irrigationMethod else p.irrigationType ?: "Drip",
                    farmingActivity = if (current.farmingActivity != "Crop Production") current.farmingActivity else p.farmingActivity ?: "Crop Production",
                    preferredLanguage = if (current.preferredLanguage != "English") current.preferredLanguage else p.preferredLanguage ?: "English",
                    temperatureUnit = if (current.temperatureUnit != "Celsius") current.temperatureUnit else p.temperatureUnit ?: "Celsius",
                    notificationsEnabled = p.notificationsEnabled,
                    isEditMode = false
                )
            }
            else -> {}
        }
    }

    fun loadAdvisories() {
        viewModelScope.launch {
            val lat = _uiState.value.latitude
            val lon = _uiState.value.longitude

            _uiState.value = _uiState.value.copy(
                irrigationState = ResultState.Loading,
                sprayState = ResultState.Loading
            )

            val cropNormalized = when {
                _uiState.value.cropName.contains("wheat", ignoreCase = true) ||
                        _uiState.value.cropName.contains("गेहूं") || _uiState.value.cropName.contains("गहू") ||
                        _uiState.value.cropName.contains("গম") || _uiState.value.cropName.contains("கோதுமை") ||
                        _uiState.value.cropName.contains("గోధుమ") || _uiState.value.cropName.contains("ઘઉં") ||
                        _uiState.value.cropName.contains("ಗೋಧಿ") || _uiState.value.cropName.contains("ഗോതമ്പ്") ||
                        _uiState.value.cropName.contains("ਕਣਕ") -> "wheat"

                _uiState.value.cropName.contains("rice", ignoreCase = true) || _uiState.value.cropName.contains("paddy", ignoreCase = true) ||
                        _uiState.value.cropName.contains("धान") || _uiState.value.cropName.contains("चावल") ||
                        _uiState.value.cropName.contains("तांदूळ") || _uiState.value.cropName.contains("भात") ||
                        _uiState.value.cropName.contains("ধান") || _uiState.value.cropName.contains("அரிசி") || _uiState.value.cropName.contains("நெல்") ||
                        _uiState.value.cropName.contains("వరి") || _uiState.value.cropName.contains("బియ్యం") ||
                        _uiState.value.cropName.contains("ચોખા") || _uiState.value.cropName.contains("ડાંગર") ||
                        _uiState.value.cropName.contains("ಭತ್ತ") || _uiState.value.cropName.contains("ಅಕ್ಕಿ") ||
                        _uiState.value.cropName.contains("നെല്ല്") || _uiState.value.cropName.contains("അരി") ||
                        _uiState.value.cropName.contains("ਝੋਨਾ") || _uiState.value.cropName.contains("ਚੌਲ") -> "rice"

                _uiState.value.cropName.contains("cotton", ignoreCase = true) ||
                        _uiState.value.cropName.contains("कपास") || _uiState.value.cropName.contains("कापूस") ||
                        _uiState.value.cropName.contains("তুলা") || _uiState.value.cropName.contains("பருத்தி") ||
                        _uiState.value.cropName.contains("పత్తి") || _uiState.value.cropName.contains("કપાસ") ||
                        _uiState.value.cropName.contains("ಹತ್ತಿ") || _uiState.value.cropName.contains("പരുത്തി") ||
                        _uiState.value.cropName.contains("ਕਪਾਹ") -> "cotton"

                _uiState.value.cropName.contains("mustard", ignoreCase = true) ||
                        _uiState.value.cropName.contains("सरसों") || _uiState.value.cropName.contains("मोहरी") ||
                        _uiState.value.cropName.contains("সরিষা") || _uiState.value.cropName.contains("கடுகு") ||
                        _uiState.value.cropName.contains("ఆవాలు") || _uiState.value.cropName.contains("રાઈ") ||
                        _uiState.value.cropName.contains("ಸಾಸಿವೆ") || _uiState.value.cropName.contains("കടുക്") ||
                        _uiState.value.cropName.contains("ਸਰ੍ਹੋਂ") -> "mustard"

                _uiState.value.cropName.contains("sugarcane", ignoreCase = true) ||
                        _uiState.value.cropName.contains("गन्ना") || _uiState.value.cropName.contains("ऊस") ||
                        _uiState.value.cropName.contains("আখ") || _uiState.value.cropName.contains("கரும்பு") ||
                        _uiState.value.cropName.contains("చెరకు") || _uiState.value.cropName.contains("શેરડી") ||
                        _uiState.value.cropName.contains("ಕಬ್ಬು") || _uiState.value.cropName.contains("കരിമ്പ്") ||
                        _uiState.value.cropName.contains("ਗੰਨਾ") -> "sugarcane"

                _uiState.value.cropName.contains("maize", ignoreCase = true) || _uiState.value.cropName.contains("corn", ignoreCase = true) ||
                        _uiState.value.cropName.contains("मक्का") || _uiState.value.cropName.contains("मका") ||
                        _uiState.value.cropName.contains("ভুট্টা") || _uiState.value.cropName.contains("மக்காச்சோளம்") ||
                        _uiState.value.cropName.contains("మొక్కజొన్న") || _uiState.value.cropName.contains("મકાઈ") ||
                        _uiState.value.cropName.contains("ಮೆಕ್ಕೆಜೋಳ") || _uiState.value.cropName.contains("ചോളം") ||
                        _uiState.value.cropName.contains("ਮੱਕੀ") -> "maize"

                else -> _uiState.value.cropName.lowercase()
            }

            val stageNormalized = when {
                _uiState.value.cropStage.contains("sowing", ignoreCase = true) ||
                        _uiState.value.cropStage.contains("बुवाई") || _uiState.value.cropStage.contains("अंकुरण") ||
                        _uiState.value.cropStage.contains("पेरणी") || _uiState.value.cropStage.contains("বপন") ||
                        _uiState.value.cropStage.contains("விதைத்தல்") || _uiState.value.cropStage.contains("విత్తనం") ||
                        _uiState.value.cropStage.contains("વાવણી") || _uiState.value.cropStage.contains("ಬಿತ್ತನೆ") ||
                        _uiState.value.cropStage.contains("വിതയ്ക്കൽ") || _uiState.value.cropStage.contains("ਬਿਜਾਈ") -> "initial"

                _uiState.value.cropStage.contains("vegetative", ignoreCase = true) ||
                        _uiState.value.cropStage.contains("वृद्धि") || _uiState.value.cropStage.contains("वानस्पतिक") ||
                        _uiState.value.cropStage.contains("वाढ") || _uiState.value.cropStage.contains("বৃদ্ধি") ||
                        _uiState.value.cropStage.contains("வளர்ச்சி") || _uiState.value.cropStage.contains("పెరుగుదల") ||
                        _uiState.value.cropStage.contains("વિકાસ") || _uiState.value.cropStage.contains("ಬೆಳವಣಿಗೆ") ||
                        _uiState.value.cropStage.contains("വളർച്ച") || _uiState.value.cropStage.contains("ਵਾਧਾ") -> "crop_development"

                _uiState.value.cropStage.contains("flowering", ignoreCase = true) ||
                        _uiState.value.cropStage.contains("फूल") || _uiState.value.cropStage.contains("फुलोरा") ||
                        _uiState.value.cropStage.contains("ফুল") || _uiState.value.cropStage.contains("பூக்கும்") ||
                        _uiState.value.cropStage.contains("పూత") || _uiState.value.cropStage.contains("ફૂલ") ||
                        _uiState.value.cropStage.contains("ಹೂ ಬಿಡುವ") || _uiState.value.cropStage.contains("പൂവിടൽ") ||
                        _uiState.value.cropStage.contains("ਫੁੱਲ") -> "mid_season"

                _uiState.value.cropStage.contains("maturity", ignoreCase = true) ||
                        _uiState.value.cropStage.contains("कटाई") || _uiState.value.cropStage.contains("परिपक्वता") ||
                        _uiState.value.cropStage.contains("कापणी") || _uiState.value.cropStage.contains("পাকা") ||
                        _uiState.value.cropStage.contains("அறுவடை") || _uiState.value.cropStage.contains("కోత") ||
                        _uiState.value.cropStage.contains("પાકવું") || _uiState.value.cropStage.contains("ಕೊಯ್ಲು") ||
                        _uiState.value.cropStage.contains("വിളവെടുപ്പ്") || _uiState.value.cropStage.contains("വിളവെഴുപ്പ്") ||
                        _uiState.value.cropStage.contains("ਵਾਢੀ") -> "late_season"

                else -> "mid_season"
            }

            val soilNormalized = when {
                _uiState.value.soilType.contains("Alluvial", ignoreCase = true) ||
                        _uiState.value.soilType.contains("दोमट") || _uiState.value.soilType.contains("जलोढ़") ||
                        _uiState.value.soilType.contains("गाळाची") || _uiState.value.soilType.contains("পলি") ||
                        _uiState.value.soilType.contains("வண்டல்") || _uiState.value.soilType.contains("ఒండ్రు") ||
                        _uiState.value.soilType.contains("કાંપવાળી") || _uiState.value.soilType.contains("ಮೆಕ್ಕಲು") ||
                        _uiState.value.soilType.contains("എക്കൽ") || _uiState.value.soilType.contains("ਜਲੋਢ") -> "alluvial_loam"

                _uiState.value.soilType.contains("Black", ignoreCase = true) ||
                        _uiState.value.soilType.contains("काली") || _uiState.value.soilType.contains("काळी") ||
                        _uiState.value.soilType.contains("কালো") || _uiState.value.soilType.contains("கரிசல்") ||
                        _uiState.value.soilType.contains("నల్ల") || _uiState.value.soilType.contains("કાળી") ||
                        _uiState.value.soilType.contains("ಕಪ್ಪು") || _uiState.value.soilType.contains("കറുത്ത") ||
                        _uiState.value.soilType.contains("ਕਾਲੀ") -> "black_cotton"

                _uiState.value.soilType.contains("Red", ignoreCase = true) ||
                        _uiState.value.soilType.contains("लाल") || _uiState.value.soilType.contains("तांबडी") ||
                        _uiState.value.soilType.contains("লাল") || _uiState.value.soilType.contains("செம்மண்") ||
                        _uiState.value.soilType.contains("ఎర్ర") || _uiState.value.soilType.contains("લાલ") ||
                        _uiState.value.soilType.contains("ಕೆಂಪು") || _uiState.value.soilType.contains("ചുവന്ന") ||
                        _uiState.value.soilType.contains("ਲਾਲ") -> "red_sandy"

                _uiState.value.soilType.contains("Clay", ignoreCase = true) ||
                        _uiState.value.soilType.contains("चिकनी") || _uiState.value.soilType.contains("चေး") ||
                        _uiState.value.soilType.contains("এঁটেল") || _uiState.value.soilType.contains("களிமண்") ||
                        _uiState.value.soilType.contains("బంక") || _uiState.value.soilType.contains("బంకమట్టి") ||
                        _uiState.value.soilType.contains("బంకమన్ను") || _uiState.value.soilType.contains("ચીકણી") ||
                        _uiState.value.soilType.contains("ಜೇಡಿಮಣ್ಣು") || _uiState.value.soilType.contains("കളിമണ്ണ്") ||
                        _uiState.value.soilType.contains("ਚੀਕਣੀ") -> "clay"

                else -> "alluvial_loam"
            }

            val irrResult = repository.getIrrigationAdvisory(
                latitude = lat,
                longitude = lon,
                cropName = cropNormalized,
                cropStage = stageNormalized,
                soilType = soilNormalized
            )

            val currentWeatherRes = repository.getCurrentWeather(lat, lon)
            val currentTemp = (currentWeatherRes as? ResultState.Success)?.data?.temperatureC ?: 28.0
            val currentWind = (currentWeatherRes as? ResultState.Success)?.data?.windSpeedKmh ?: 12.0
            val currentHumidity = (currentWeatherRes as? ResultState.Success)?.data?.relativeHumidityPct ?: 60.0

            val sprayResult = repository.getSprayWindowAdvisory(
                windSpeedKmh = currentWind,
                rainProbabilityPct = 10.0,
                tempC = currentTemp,
                relativeHumidityPct = currentHumidity
            )

            _uiState.value = _uiState.value.copy(
                irrigationState = irrResult,
                sprayState = sprayResult
            )
        }
    }

    fun setCrop(crop: String) {
        _uiState.value = _uiState.value.copy(cropName = crop, validationError = null)
        loadAdvisories()
    }

    fun setCropStage(stage: String) {
        _uiState.value = _uiState.value.copy(cropStage = stage, validationError = null)
        loadAdvisories()
    }

    fun setSoilType(soil: String) {
        _uiState.value = _uiState.value.copy(soilType = soil, validationError = null)
        loadAdvisories()
    }

    fun setFieldArea(area: String) {
        _uiState.value = _uiState.value.copy(fieldAreaText = area, validationError = null)
    }

    fun setFullName(value: String) { _uiState.value = _uiState.value.copy(fullName = value, validationError = null) }
    fun setMobileNumber(value: String) { _uiState.value = _uiState.value.copy(mobileNumber = value, validationError = null) }
    fun setFarmerId(value: String) { _uiState.value = _uiState.value.copy(farmerId = value, validationError = null) }
    fun setVillage(value: String) { _uiState.value = _uiState.value.copy(village = value, validationError = null) }
    fun setDistrict(value: String) { _uiState.value = _uiState.value.copy(district = value, validationError = null) }
    fun setState(value: String) { _uiState.value = _uiState.value.copy(state = value, validationError = null) }
    fun setPincode(value: String) { _uiState.value = _uiState.value.copy(pincode = value, validationError = null) }

    fun setFieldName(value: String) { _uiState.value = _uiState.value.copy(fieldName = value, validationError = null) }
    fun setPlotNumber(value: String) { _uiState.value = _uiState.value.copy(plotNumber = value, validationError = null) }
    fun setSurveyNumber(value: String) { _uiState.value = _uiState.value.copy(surveyNumber = value, validationError = null) }
    fun setAreaUnit(value: String) { _uiState.value = _uiState.value.copy(areaUnit = value, validationError = null) }

    fun setVariety(value: String) { _uiState.value = _uiState.value.copy(variety = value, validationError = null) }
    fun setSowingDate(value: String) { _uiState.value = _uiState.value.copy(sowingDate = value, validationError = null) }
    fun setExpectedHarvestDate(value: String) { _uiState.value = _uiState.value.copy(expectedHarvestDate = value, validationError = null) }
    fun setCropIrrigationType(value: String) { _uiState.value = _uiState.value.copy(cropIrrigationType = value, validationError = null) }

    fun setSoilMoistureAvailability(value: String) { _uiState.value = _uiState.value.copy(soilMoistureAvailability = value, validationError = null) }
    fun setIrrigationMethod(value: String) { _uiState.value = _uiState.value.copy(irrigationMethod = value, validationError = null) }
    fun setFarmingActivity(value: String) { _uiState.value = _uiState.value.copy(farmingActivity = value, validationError = null) }

    fun setPreferredLanguage(value: String) { _uiState.value = _uiState.value.copy(preferredLanguage = value, validationError = null) }
    fun setTemperatureUnit(value: String) { _uiState.value = _uiState.value.copy(temperatureUnit = value, validationError = null) }
    fun setNotificationsEnabled(value: Boolean) { _uiState.value = _uiState.value.copy(notificationsEnabled = value, validationError = null) }

    fun setEditMode(edit: Boolean) { _uiState.value = _uiState.value.copy(isEditMode = edit, validationError = null) }
    fun toggleEditMode() { _uiState.value = _uiState.value.copy(isEditMode = !_uiState.value.isEditMode, validationError = null) }

    fun saveProfile(): Boolean {
        val s = _uiState.value
        val area = s.fieldAreaText.toDoubleOrNull()
        if (area == null || area <= 0.0) {
            _uiState.value = s.copy(
                validationError = "Please enter a valid positive field area"
            )
            return false
        }
        if (s.fullName.isBlank()) {
            _uiState.value = s.copy(validationError = "Full Name is required")
            return false
        }
        if (s.district.isBlank()) {
            _uiState.value = s.copy(validationError = "District is required")
            return false
        }
        if (s.state.isBlank()) {
            _uiState.value = s.copy(validationError = "State is required")
            return false
        }
        if (s.cropName.isBlank()) {
            _uiState.value = s.copy(validationError = "Crop is required")
            return false
        }
        if (s.cropStage.isBlank()) {
            _uiState.value = s.copy(validationError = "Crop Stage is required")
            return false
        }
        if (s.mobileNumber.isNotBlank() && (s.mobileNumber.length != 10 || s.mobileNumber.any { !it.isDigit() })) {
            _uiState.value = s.copy(validationError = "Mobile Number must be 10 digits")
            return false
        }
        if (s.pincode.isNotBlank() && (s.pincode.length != 6 || s.pincode.any { !it.isDigit() })) {
            _uiState.value = s.copy(validationError = "Pincode must be 6 digits")
            return false
        }

        val profile = FarmerProfile(
            fullName = s.fullName.trim(),
            mobileNumber = s.mobileNumber.trim().ifBlank { null },
            farmerId = s.farmerId.trim().ifBlank { null },
            village = s.village.trim().ifBlank { null },
            district = s.district.trim(),
            state = s.state.trim(),
            pincode = s.pincode.trim().ifBlank { null },
            fieldName = s.fieldName.trim().ifBlank { null },
            plotNumber = s.plotNumber.trim().ifBlank { null },
            surveyNumber = s.surveyNumber.trim().ifBlank { null },
            farmArea = area,
            areaUnit = s.areaUnit,
            crop = s.cropName.trim(),
            variety = s.variety.trim().ifBlank { null },
            cropStage = s.cropStage.trim(),
            sowingDate = s.sowingDate.trim().ifBlank { null },
            expectedHarvestDate = s.expectedHarvestDate.trim().ifBlank { null },
            soilType = s.soilType,
            soilMoistureAvailability = s.soilMoistureAvailability,
            irrigationType = s.irrigationMethod,
            farmingActivity = s.farmingActivity,
            preferredLanguage = s.preferredLanguage,
            temperatureUnit = s.temperatureUnit,
            notificationsEnabled = s.notificationsEnabled
        )

        viewModelScope.launch {
            repository.saveFarmerProfile(profile)
        }

        _uiState.value = s.copy(
            validationError = null,
            isSavedSuccessfully = true,
            isEditMode = false
        )
        loadAdvisories()
        return true
    }

    fun resetSaveState() {
        _uiState.value = _uiState.value.copy(isSavedSuccessfully = false)
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = (this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as WeatherGPTApplication)
                FarmerProfileViewModel(
                    repository = app.container.repository,
                    locationManager = app.container.sharedLocationManager
                )
            }
        }
    }
}
