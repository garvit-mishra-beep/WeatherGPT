package com.weathergpt.core.location

import android.content.Context
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class PredefinedLocation(
    val districtName: String,
    val stateName: String,
    val latitude: Double,
    val longitude: Double,
    val hindiName: String
) {
    val displayName: String get() = "$districtName, $stateName"
}

data class LocationState(
    val latitude: Double = 21.1702,
    val longitude: Double = 72.8311,
    val districtName: String = "Surat",
    val stateName: String = "Gujarat",
    val subDistrictName: String? = null,
    val formattedAddress: String = "Surat, Gujarat",
    val isResolving: Boolean = false
)

class SharedLocationManager(
    private val context: Context? = null
) {
    private val _locationState = MutableStateFlow(
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            LocationState(
                latitude = DEMO_GWALIOR_LATITUDE,
                longitude = DEMO_GWALIOR_LONGITUDE,
                districtName = DEMO_GWALIOR_DISTRICT,
                stateName = DEMO_GWALIOR_STATE,
                formattedAddress = DEMO_GWALIOR_LOCATION_NAME
            )
        } else {
            LocationState()
        }
    )
    val locationState: StateFlow<LocationState> = _locationState.asStateFlow()

    init {
        loadPersistedLocation()
    }

    val availableLocations: List<PredefinedLocation> = listOf(
        PredefinedLocation(DEMO_GWALIOR_DISTRICT, DEMO_GWALIOR_STATE, DEMO_GWALIOR_LATITUDE, DEMO_GWALIOR_LONGITUDE, DEMO_GWALIOR_HINDI_NAME),
        PredefinedLocation("Indore", "Madhya Pradesh", 22.7196, 75.8577, "इंदौर, मध्य प्रदेश"),
        PredefinedLocation("Delhi", "Delhi", 28.6139, 77.2090, "दिल्ली, दिल्ली"),
        PredefinedLocation("New Delhi", "Delhi", 28.6139, 77.2090, "नई दिल्ली, दिल्ली"),
        PredefinedLocation("Mumbai", "Maharashtra", 19.0760, 72.8777, "मुंबई, महाराष्ट्र"),
        PredefinedLocation("Chennai", "Tamil Nadu", 13.0827, 80.2707, "चेन्नई, तमिलनाडु"),
        PredefinedLocation("Surat", "Gujarat", 21.1702, 72.8311, "सूरत, गुजरात"),
        PredefinedLocation("Pune", "Maharashtra", 18.5204, 73.8567, "पुणे, महाराष्ट्र"),
        PredefinedLocation("Ahmedabad", "Gujarat", 23.0225, 72.5714, "अहमदाबाद, गुजरात"),
        PredefinedLocation("Jaipur", "Rajasthan", 26.9124, 75.7873, "जयपुर, राजस्थान"),
        PredefinedLocation("Lucknow", "Uttar Pradesh", 26.8467, 80.9462, "लखनऊ, उत्तर प्रदेश"),
        PredefinedLocation("Patna", "Bihar", 25.5941, 85.1376, "पटना, बिहार"),
        PredefinedLocation("Kolkata", "West Bengal", 22.5726, 88.3639, "कोलकाता, पश्चिम बंगाल"),
        PredefinedLocation("Bengaluru", "Karnataka", 12.9716, 77.5946, "बेंगलुरु, कर्नाटक")
    )

    fun selectGwaliorDemoLocation() {
        updateLocation(
            district = DEMO_GWALIOR_DISTRICT,
            state = DEMO_GWALIOR_STATE,
            latitude = DEMO_GWALIOR_LATITUDE,
            longitude = DEMO_GWALIOR_LONGITUDE
        )
    }

    fun selectPredefinedLocation(location: PredefinedLocation) {
        updateLocation(
            district = location.districtName,
            state = location.stateName,
            latitude = location.latitude,
            longitude = location.longitude
        )
    }

    fun updateCoordinates(latitude: Double, longitude: Double) {
        _locationState.value = _locationState.value.copy(
            latitude = latitude,
            longitude = longitude
        )
        persistLocation()
    }

    fun updateLocation(
        district: String,
        state: String,
        latitude: Double,
        longitude: Double,
        subDistrict: String? = null
    ) {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            _locationState.value = LocationState(
                latitude = DEMO_GWALIOR_LATITUDE,
                longitude = DEMO_GWALIOR_LONGITUDE,
                districtName = DEMO_GWALIOR_DISTRICT,
                stateName = DEMO_GWALIOR_STATE,
                subDistrictName = null,
                formattedAddress = DEMO_GWALIOR_LOCATION_NAME,
                isResolving = false
            )
            return
        }
        val formatted = if (subDistrict != null) {
            "$subDistrict, $district, $state"
        } else {
            "$district, $state"
        }
        _locationState.value = _locationState.value.copy(
            latitude = latitude,
            longitude = longitude,
            districtName = district,
            stateName = state,
            subDistrictName = subDistrict,
            formattedAddress = formatted,
            isResolving = false
        )
        persistLocation()
    }

    suspend fun resolveLocationHierarchy(repository: WeatherGPTRepository) {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            selectGwaliorDemoLocation()
            return
        }
        _locationState.value = _locationState.value.copy(isResolving = true)
        val lat = _locationState.value.latitude
        val lon = _locationState.value.longitude

        when (val result = repository.getLocationHierarchy(lat, lon)) {
            is ResultState.Success<LocationHierarchy> -> {
                val data = result.data
                val district = data.district?.name ?: _locationState.value.districtName
                val state = data.state?.name ?: _locationState.value.stateName
                val subDistrict = data.subdistrict?.name
                updateLocation(
                    district = district,
                    state = state,
                    latitude = lat,
                    longitude = lon,
                    subDistrict = subDistrict
                )
            }
            else -> {
                _locationState.value = _locationState.value.copy(isResolving = false)
            }
        }
    }

    private fun loadPersistedLocation() {
        if (com.weathergpt.core.config.AppConfig.isDemoMode) {
            _locationState.value = LocationState(
                latitude = DEMO_GWALIOR_LATITUDE,
                longitude = DEMO_GWALIOR_LONGITUDE,
                districtName = DEMO_GWALIOR_DISTRICT,
                stateName = DEMO_GWALIOR_STATE,
                formattedAddress = DEMO_GWALIOR_LOCATION_NAME
            )
            return
        }
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val dist = prefs.getString(KEY_DISTRICT, null)
            val st = prefs.getString(KEY_STATE, null)
            val lat = prefs.getString(KEY_LATITUDE, null)?.toDoubleOrNull()
            val lon = prefs.getString(KEY_LONGITUDE, null)?.toDoubleOrNull()
            if (dist != null && st != null && lat != null && lon != null) {
                _locationState.value = LocationState(
                    latitude = lat,
                    longitude = lon,
                    districtName = dist,
                    stateName = st,
                    formattedAddress = "$dist, $st"
                )
            }
        } catch (_: Throwable) {
            // Non-fatal
        }
    }

    private fun persistLocation() {
        if (context == null) return
        try {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val current = _locationState.value
            prefs.edit()
                .putString(KEY_DISTRICT, current.districtName)
                .putString(KEY_STATE, current.stateName)
                .putString(KEY_LATITUDE, current.latitude.toString())
                .putString(KEY_LONGITUDE, current.longitude.toString())
                .apply()
        } catch (_: Throwable) {
            // Non-fatal
        }
    }

    companion object {
        const val DEMO_GWALIOR_LATITUDE = 26.2183
        const val DEMO_GWALIOR_LONGITUDE = 78.1828
        const val DEMO_GWALIOR_DISTRICT = "Gwalior"
        const val DEMO_GWALIOR_STATE = "Madhya Pradesh"
        const val DEMO_GWALIOR_LOCATION_NAME = "Gwalior, Madhya Pradesh"
        const val DEMO_GWALIOR_HINDI_NAME = "ग्वालियर, मध्य प्रदेश"

        private const val PREFS_NAME = "weathergpt_location_prefs"
        private const val KEY_DISTRICT = "selected_district"
        private const val KEY_STATE = "selected_state"
        private const val KEY_LATITUDE = "selected_latitude"
        private const val KEY_LONGITUDE = "selected_longitude"
    }
}
