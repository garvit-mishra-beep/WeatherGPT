package com.weathergpt.domain.model.farmer

data class CropWaterBalanceMetrics(
    val referenceEt0MmDay: Double,
    val cropKc: Double,
    val dailyWaterDemandMm: Double,
    val forecastRainfall48hMm: Double,
    val netDeficitMm: Double,
    val finalDepletionMm: Double
)

data class IrrigationAdvisory(
    val action: String, // e.g. "IRRIGATE", "WAIT_RAIN_EXPECTED", "MONITOR"
    val urgency: String, // "high", "medium", "low"
    val metrics: CropWaterBalanceMetrics,
    val rationale: String,
    val calculationMethod: String
)

data class SpraySuitability(
    val isSuitable: Boolean,
    val conditionLevel: String, // "optimal", "unfavorable"
    val recommendation: String,
    val windSuitable: Boolean,
    val rainProbabilitySuitable: Boolean,
    val calculationMethod: String
)

/**
 * Persistent Farmer Profile model representing complete farmer, field, crop,
 * soil, farming practice, and application preference context.
 */
data class FarmerProfile(
    val id: Long = 1L,
    // Section 1 — Farmer Information
    val fullName: String = "Gwalior Farmer",
    val mobileNumber: String? = null,
    val farmerId: String? = null,
    val village: String? = "Morar",
    val district: String = "Gwalior",
    val state: String = "Madhya Pradesh",
    val pincode: String? = null,

    // Section 2 — Farm / Field Information
    val fieldName: String? = null,
    val plotNumber: String? = null,
    val surveyNumber: String? = null,
    val farmArea: Double? = 2.5,
    val areaUnit: String? = "hectare",

    // Section 3 — Crop Information
    val crop: String = "Wheat",
    val variety: String? = "Sharbati",
    val cropStage: String = "Vegetative",
    val sowingDate: String? = null,
    val expectedHarvestDate: String? = null,

    // Section 4 — Soil Information
    val soilType: String? = null,
    val soilMoistureAvailability: String? = null,

    // Section 5 — Farm Practices
    val irrigationType: String? = null,
    val farmingActivity: String? = null,

    // Section 6 — Preferences
    val preferredLanguage: String? = "English",
    val temperatureUnit: String? = "Celsius",
    val notificationsEnabled: Boolean = true,

    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
) {
    companion object {
        val CROP_STAGE_OPTIONS = listOf(
            "Seedling",
            "Vegetative",
            "Flowering",
            "Fruiting",
            "Maturity",
            "Harvest",
            "Unknown"
        )

        val SOIL_TYPE_OPTIONS = listOf(
            "Alluvial",
            "Black Soil",
            "Red Soil",
            "Loamy",
            "Sandy",
            "Clay",
            "Other",
            "Unknown"
        )

        val SOIL_MOISTURE_OPTIONS = listOf(
            "Irrigated",
            "Rainfed",
            "Partially Irrigated",
            "Unknown"
        )

        val IRRIGATION_METHOD_OPTIONS = listOf(
            "Drip",
            "Sprinkler",
            "Flood",
            "Furrow",
            "Rainfed",
            "Other"
        )

        val FARMING_ACTIVITY_OPTIONS = listOf(
            "Crop Production",
            "Horticulture",
            "Livestock",
            "Mixed Farming"
        )

        val AREA_UNIT_OPTIONS = listOf(
            "hectare",
            "acre"
        )

        val PREFERRED_LANGUAGE_OPTIONS = listOf(
            "English",
            "Hindi"
        )

        val TEMPERATURE_UNIT_OPTIONS = listOf(
            "Celsius",
            "Fahrenheit"
        )
    }
}

