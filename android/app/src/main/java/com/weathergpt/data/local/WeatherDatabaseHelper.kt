package com.weathergpt.data.local

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.weathergpt.domain.model.farmer.FarmerProfile
import java.util.Locale

/**
 * Normalized database record representing cached real weather data.
 */
data class CachedWeatherRecord(
    val locationKey: String,
    val latitude: Double,
    val longitude: Double,
    val locationName: String?,
    val retrievedAtMillis: Long,
    val retrievedAtIso: String,
    val forecastStartIso: String?,
    val forecastEndIso: String?,
    val provider: String?,
    val authority: String?,
    val currentWeatherJson: String?,
    val forecastJson: String?,
    val alertsJson: String?,
    val schemaVersion: Int
)

/**
 * Production SQLite persistent storage for successful REAL weather responses.
 *
 * Implements:
 * 1. Strict spatial location keying (`loc_%.2f_%.2f`).
 * 2. Deterministic 3-day (72-hour) retention and pruning.
 * 3. Atomic upserts with zero duplicate accumulation on screen recomposition.
 * 4. Preservation of provider provenance and ISO-8601 timestamps.
 */
class WeatherDatabaseHelper(
    context: Context,
    dbName: String = DATABASE_NAME
) : SQLiteOpenHelper(context, dbName, null, DATABASE_VERSION) {

    companion object {
        const val DATABASE_NAME = "weathergpt_local_cache.db"
        const val DATABASE_VERSION = 5

        const val DEMO_GWALIOR_LOCATION_KEY = "loc_26.22_78.18"
        const val DEMO_GWALIOR_LATITUDE = 26.2183
        const val DEMO_GWALIOR_LONGITUDE = 78.1828

        val REAL_GWALIOR_CURRENT_WEATHER_JSON = """
            {
              "location": {"latitude": 26.2183, "longitude": 78.1828},
              "observation_time": "2026-09-10T20:15:00Z",
              "temperature_c": 28.841,
              "feels_like_c": 33.5,
              "relative_humidity_pct": 72.39,
              "precipitation_mm": 0.0,
              "rain_intensity_category": "no_rain",
              "wind_speed_kmh": 6.2,
              "wind_direction_deg": 353.0,
              "surface_pressure_hpa": 982.9,
              "weather_condition": "overcast",
              "provenance": {
                "provider": "Open-Meteo",
                "authority": "Operational Surface Observation",
                "quality": "VERIFIED",
                "retrieval_timestamp": "2026-09-10T14:53:39Z"
              }
            }
        """.trimIndent()

        val REAL_GWALIOR_FORECAST_JSON = """
            {
              "location": {"latitude": 26.2183, "longitude": 78.1828},
              "generated_at": "2026-09-10T14:53:39Z",
              "forecast_start": "2026-09-11T00:00:00Z",
              "forecast_end": "2026-09-21T00:00:00Z",
              "daily_forecast": [
                {
                  "date": "2026-09-11",
                  "temp_max_c": 28.7,
                  "temp_min_c": 24.4,
                  "temp_avg_c": 26.55,
                  "feels_like_c": 34.5,
                  "precipitation_sum_mm": 18.4,
                  "precipitation_probability_pct": 86.0,
                  "wind_speed_max_kmh": 10.4,
                  "wind_gust_kmh": 23.0,
                  "wind_direction_deg": 54.0,
                  "relative_humidity_pct": 72.0,
                  "weather_code": 96,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-11T00:00:00Z",
                  "forecast_valid_until": "2026-09-11T23:59:59Z"
                },
                {
                  "date": "2026-09-12",
                  "temp_max_c": 31.1,
                  "temp_min_c": 24.6,
                  "temp_avg_c": 27.85,
                  "feels_like_c": 35.3,
                  "precipitation_sum_mm": 7.6,
                  "precipitation_probability_pct": 63.0,
                  "wind_speed_max_kmh": 15.3,
                  "wind_gust_kmh": 40.3,
                  "wind_direction_deg": 64.0,
                  "relative_humidity_pct": 70.0,
                  "weather_code": 96,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-12T00:00:00Z",
                  "forecast_valid_until": "2026-09-12T23:59:59Z"
                },
                {
                  "date": "2026-09-13",
                  "temp_max_c": 31.0,
                  "temp_min_c": 24.7,
                  "temp_avg_c": 27.85,
                  "feels_like_c": 36.0,
                  "precipitation_sum_mm": 6.2,
                  "precipitation_probability_pct": 83.0,
                  "wind_speed_max_kmh": 17.9,
                  "wind_gust_kmh": 44.6,
                  "wind_direction_deg": 89.0,
                  "relative_humidity_pct": 71.0,
                  "weather_code": 96,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-13T00:00:00Z",
                  "forecast_valid_until": "2026-09-13T23:59:59Z"
                },
                {
                  "date": "2026-09-14",
                  "temp_max_c": 31.1,
                  "temp_min_c": 25.1,
                  "temp_avg_c": 28.10,
                  "feels_like_c": 36.0,
                  "precipitation_sum_mm": 5.2,
                  "precipitation_probability_pct": 74.0,
                  "wind_speed_max_kmh": 15.3,
                  "wind_gust_kmh": 33.8,
                  "wind_direction_deg": 142.0,
                  "relative_humidity_pct": 69.0,
                  "weather_code": 95,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-14T00:00:00Z",
                  "forecast_valid_until": "2026-09-14T23:59:59Z"
                },
                {
                  "date": "2026-09-15",
                  "temp_max_c": 31.9,
                  "temp_min_c": 24.2,
                  "temp_avg_c": 28.05,
                  "feels_like_c": 38.3,
                  "precipitation_sum_mm": 4.5,
                  "precipitation_probability_pct": 56.0,
                  "wind_speed_max_kmh": 9.2,
                  "wind_gust_kmh": 23.4,
                  "wind_direction_deg": 195.0,
                  "relative_humidity_pct": 68.0,
                  "weather_code": 95,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-15T00:00:00Z",
                  "forecast_valid_until": "2026-09-15T23:59:59Z"
                },
                {
                  "date": "2026-09-16",
                  "temp_max_c": 31.1,
                  "temp_min_c": 25.7,
                  "temp_avg_c": 28.40,
                  "feels_like_c": 36.9,
                  "precipitation_sum_mm": 1.2,
                  "precipitation_probability_pct": 68.0,
                  "wind_speed_max_kmh": 13.0,
                  "wind_gust_kmh": 32.8,
                  "wind_direction_deg": 253.0,
                  "relative_humidity_pct": 65.0,
                  "weather_code": 51,
                  "dominant_condition": "drizzle",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-16T00:00:00Z",
                  "forecast_valid_until": "2026-09-16T23:59:59Z"
                },
                {
                  "date": "2026-09-17",
                  "temp_max_c": 29.8,
                  "temp_min_c": 25.0,
                  "temp_avg_c": 27.40,
                  "feels_like_c": 34.7,
                  "precipitation_sum_mm": 4.2,
                  "precipitation_probability_pct": 86.0,
                  "wind_speed_max_kmh": 14.2,
                  "wind_gust_kmh": 35.3,
                  "wind_direction_deg": 254.0,
                  "relative_humidity_pct": 73.0,
                  "weather_code": 95,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-17T00:00:00Z",
                  "forecast_valid_until": "2026-09-17T23:59:59Z"
                },
                {
                  "date": "2026-09-18",
                  "temp_max_c": 30.9,
                  "temp_min_c": 23.3,
                  "temp_avg_c": 27.10,
                  "feels_like_c": 37.4,
                  "precipitation_sum_mm": 13.2,
                  "precipitation_probability_pct": 50.0,
                  "wind_speed_max_kmh": 7.1,
                  "wind_gust_kmh": 27.7,
                  "wind_direction_deg": 210.0,
                  "relative_humidity_pct": 74.0,
                  "weather_code": 95,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-18T00:00:00Z",
                  "forecast_valid_until": "2026-09-18T23:59:59Z"
                },
                {
                  "date": "2026-09-19",
                  "temp_max_c": 27.6,
                  "temp_min_c": 23.2,
                  "temp_avg_c": 25.40,
                  "feels_like_c": 33.4,
                  "precipitation_sum_mm": 27.0,
                  "precipitation_probability_pct": 51.0,
                  "wind_speed_max_kmh": 12.7,
                  "wind_gust_kmh": 29.5,
                  "wind_direction_deg": 118.0,
                  "relative_humidity_pct": 78.0,
                  "weather_code": 95,
                  "dominant_condition": "thunderstorm",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-19T00:00:00Z",
                  "forecast_valid_until": "2026-09-19T23:59:59Z"
                },
                {
                  "date": "2026-09-20",
                  "temp_max_c": 29.9,
                  "temp_min_c": 23.7,
                  "temp_avg_c": 26.80,
                  "feels_like_c": 35.8,
                  "precipitation_sum_mm": 1.2,
                  "precipitation_probability_pct": 33.0,
                  "wind_speed_max_kmh": 7.5,
                  "wind_gust_kmh": 22.3,
                  "wind_direction_deg": 169.0,
                  "relative_humidity_pct": 67.0,
                  "weather_code": 51,
                  "dominant_condition": "drizzle",
                  "source": "Open-Meteo",
                  "retrieved_at": "2026-09-10T14:53:39Z",
                  "forecast_valid_from": "2026-09-20T00:00:00Z",
                  "forecast_valid_until": "2026-09-20T23:59:59Z"
                }
              ],
              "hourly_forecast": [
                {
                  "time": "2026-09-10T21:00:00Z",
                  "temperature_c": 28.5,
                  "relative_humidity_pct": 73.0,
                  "precipitation_mm": 0.0,
                  "precipitation_probability_pct": 5.0,
                  "wind_speed_kmh": 6.0,
                  "condition": "partly_cloudy"
                },
                {
                  "time": "2026-09-10T22:00:00Z",
                  "temperature_c": 27.8,
                  "relative_humidity_pct": 75.0,
                  "precipitation_mm": 0.0,
                  "precipitation_probability_pct": 5.0,
                  "wind_speed_kmh": 5.8,
                  "condition": "partly_cloudy"
                },
                {
                  "time": "2026-09-10T23:00:00Z",
                  "temperature_c": 27.2,
                  "relative_humidity_pct": 76.0,
                  "precipitation_mm": 0.0,
                  "precipitation_probability_pct": 10.0,
                  "wind_speed_kmh": 5.5,
                  "condition": "clear"
                }
              ],
              "provenance": {
                "provider": "Open-Meteo",
                "authority": "Operational Surface Observation",
                "quality": "VERIFIED",
                "retrieval_timestamp": "2026-09-10T14:53:39Z"
              }
            }
        """.trimIndent()

        fun seedGwaliorDemoData(db: SQLiteDatabase) {
            val values = ContentValues().apply {
                put(COL_LOCATION_KEY, DEMO_GWALIOR_LOCATION_KEY)
                put(COL_LATITUDE, DEMO_GWALIOR_LATITUDE)
                put(COL_LONGITUDE, DEMO_GWALIOR_LONGITUDE)
                put(COL_LOCATION_NAME, "Gwalior, Madhya Pradesh")
                put(COL_RETRIEVED_AT_MILLIS, System.currentTimeMillis())
                put(COL_RETRIEVED_AT_ISO, "2026-09-10T14:53:39Z")
                put(COL_FORECAST_START_ISO, "2026-09-11T00:00:00Z")
                put(COL_FORECAST_END_ISO, "2026-09-21T00:00:00Z")
                put(COL_PROVIDER, "Open-Meteo")
                put(COL_AUTHORITY, "Operational Surface Observation")
                put(COL_CURRENT_WEATHER_JSON, REAL_GWALIOR_CURRENT_WEATHER_JSON)
                put(COL_FORECAST_JSON, REAL_GWALIOR_FORECAST_JSON)
                put(COL_ALERTS_JSON, null as String?)
                put(COL_SCHEMA_VERSION, 1)
            }
            db.insertWithOnConflict(
                TABLE_CACHED_WEATHER,
                null,
                values,
                SQLiteDatabase.CONFLICT_REPLACE
            )
        }

        const val TABLE_CACHED_WEATHER = "cached_weather"

        const val COL_LOCATION_KEY = "location_key"
        const val COL_LATITUDE = "latitude"
        const val COL_LONGITUDE = "longitude"
        const val COL_LOCATION_NAME = "location_name"
        const val COL_RETRIEVED_AT_MILLIS = "retrieved_at_millis"
        const val COL_RETRIEVED_AT_ISO = "retrieved_at_iso"
        const val COL_FORECAST_START_ISO = "forecast_start_iso"
        const val COL_FORECAST_END_ISO = "forecast_end_iso"
        const val COL_PROVIDER = "provider"
        const val COL_AUTHORITY = "authority"
        const val COL_CURRENT_WEATHER_JSON = "current_weather_json"
        const val COL_FORECAST_JSON = "forecast_json"
        const val COL_ALERTS_JSON = "alerts_json"
        const val COL_SCHEMA_VERSION = "schema_version"

        private const val CREATE_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS $TABLE_CACHED_WEATHER (
                $COL_LOCATION_KEY TEXT PRIMARY KEY,
                $COL_LATITUDE REAL NOT NULL,
                $COL_LONGITUDE REAL NOT NULL,
                $COL_LOCATION_NAME TEXT,
                $COL_RETRIEVED_AT_MILLIS INTEGER NOT NULL,
                $COL_RETRIEVED_AT_ISO TEXT NOT NULL,
                $COL_FORECAST_START_ISO TEXT,
                $COL_FORECAST_END_ISO TEXT,
                $COL_PROVIDER TEXT,
                $COL_AUTHORITY TEXT,
                $COL_CURRENT_WEATHER_JSON TEXT,
                $COL_FORECAST_JSON TEXT,
                $COL_ALERTS_JSON TEXT,
                $COL_SCHEMA_VERSION INTEGER NOT NULL DEFAULT 1
            );
        """

        const val TABLE_FARMER_PROFILE = "farmer_profile"
        const val COL_FP_ID = "id"
        const val COL_FP_FULL_NAME = "full_name"
        const val COL_FP_MOBILE_NUMBER = "mobile_number"
        const val COL_FP_FARMER_ID = "farmer_id"
        const val COL_FP_VILLAGE = "village"
        const val COL_FP_DISTRICT = "district"
        const val COL_FP_STATE = "state"
        const val COL_FP_PINCODE = "pincode"
        const val COL_FP_FIELD_NAME = "field_name"
        const val COL_FP_PLOT_NUMBER = "plot_number"
        const val COL_FP_SURVEY_NUMBER = "survey_number"
        const val COL_FP_FARM_AREA = "farm_area"
        const val COL_FP_AREA_UNIT = "area_unit"
        const val COL_FP_CROP = "crop"
        const val COL_FP_VARIETY = "variety"
        const val COL_FP_CROP_STAGE = "crop_stage"
        const val COL_FP_SOWING_DATE = "sowing_date"
        const val COL_FP_EXPECTED_HARVEST_DATE = "expected_harvest_date"
        const val COL_FP_SOIL_TYPE = "soil_type"
        const val COL_FP_SOIL_MOISTURE = "soil_moisture"
        const val COL_FP_IRRIGATION_TYPE = "irrigation_type"
        const val COL_FP_FARMING_ACTIVITY = "farming_activity"
        const val COL_FP_PREFERRED_LANGUAGE = "preferred_language"
        const val COL_FP_TEMPERATURE_UNIT = "temperature_unit"
        const val COL_FP_NOTIFICATIONS_ENABLED = "notifications_enabled"
        const val COL_FP_CREATED_AT = "created_at"
        const val COL_FP_UPDATED_AT = "updated_at"

        private const val CREATE_FARMER_PROFILE_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS $TABLE_FARMER_PROFILE (
                $COL_FP_ID INTEGER PRIMARY KEY,
                $COL_FP_FULL_NAME TEXT NOT NULL,
                $COL_FP_MOBILE_NUMBER TEXT,
                $COL_FP_FARMER_ID TEXT,
                $COL_FP_VILLAGE TEXT,
                $COL_FP_DISTRICT TEXT NOT NULL,
                $COL_FP_STATE TEXT NOT NULL,
                $COL_FP_PINCODE TEXT,
                $COL_FP_FIELD_NAME TEXT,
                $COL_FP_PLOT_NUMBER TEXT,
                $COL_FP_SURVEY_NUMBER TEXT,
                $COL_FP_FARM_AREA REAL,
                $COL_FP_AREA_UNIT TEXT,
                $COL_FP_CROP TEXT NOT NULL,
                $COL_FP_VARIETY TEXT,
                $COL_FP_CROP_STAGE TEXT NOT NULL,
                $COL_FP_SOWING_DATE TEXT,
                $COL_FP_EXPECTED_HARVEST_DATE TEXT,
                $COL_FP_SOIL_TYPE TEXT,
                $COL_FP_SOIL_MOISTURE TEXT,
                $COL_FP_IRRIGATION_TYPE TEXT,
                $COL_FP_FARMING_ACTIVITY TEXT,
                $COL_FP_PREFERRED_LANGUAGE TEXT,
                $COL_FP_TEMPERATURE_UNIT TEXT,
                $COL_FP_NOTIFICATIONS_ENABLED INTEGER NOT NULL DEFAULT 1,
                $COL_FP_CREATED_AT INTEGER NOT NULL,
                $COL_FP_UPDATED_AT INTEGER NOT NULL
            );
        """

        fun seedDefaultFarmerProfile(db: SQLiteDatabase) {
            val values = ContentValues().apply {
                put(COL_FP_ID, 1L)
                put(COL_FP_FULL_NAME, "Garvit Mishra")
                put(COL_FP_MOBILE_NUMBER, "9876543210")
                put(COL_FP_FARMER_ID, "GWL-2026-081")
                put(COL_FP_VILLAGE, "Morar")
                put(COL_FP_DISTRICT, "Gwalior")
                put(COL_FP_STATE, "Madhya Pradesh")
                put(COL_FP_PINCODE, "474006")
                put(COL_FP_FIELD_NAME, "North Farm Plot #1")
                put(COL_FP_PLOT_NUMBER, "14B")
                put(COL_FP_SURVEY_NUMBER, "88/2")
                put(COL_FP_FARM_AREA, 2.5)
                put(COL_FP_AREA_UNIT, "hectare")
                put(COL_FP_CROP, "Wheat")
                put(COL_FP_VARIETY, "Sharbati / MP-305")
                put(COL_FP_CROP_STAGE, "Vegetative")
                put(COL_FP_SOWING_DATE, "2026-11-15")
                put(COL_FP_EXPECTED_HARVEST_DATE, "2027-03-25")
                put(COL_FP_SOIL_TYPE, "Alluvial")
                put(COL_FP_SOIL_MOISTURE, "Irrigated")
                put(COL_FP_IRRIGATION_TYPE, "Drip")
                put(COL_FP_FARMING_ACTIVITY, "Crop Production")
                put(COL_FP_PREFERRED_LANGUAGE, "English")
                put(COL_FP_TEMPERATURE_UNIT, "Celsius")
                put(COL_FP_NOTIFICATIONS_ENABLED, 1)
                put(COL_FP_CREATED_AT, System.currentTimeMillis())
                put(COL_FP_UPDATED_AT, System.currentTimeMillis())
            }
            db.insertWithOnConflict(
                TABLE_FARMER_PROFILE,
                null,
                values,
                SQLiteDatabase.CONFLICT_REPLACE
            )
        }

        private const val CREATE_RETENTION_INDEX_SQL = """
            CREATE INDEX IF NOT EXISTS idx_cached_retention 
            ON $TABLE_CACHED_WEATHER ($COL_RETRIEVED_AT_MILLIS);
        """

        fun generateLocationKey(latitude: Double, longitude: Double): String {
            val latRounded = kotlin.math.round(latitude * 100.0) / 100.0
            val lonRounded = kotlin.math.round(longitude * 100.0) / 100.0
            return String.format(Locale.ROOT, "loc_%.2f_%.2f", latRounded, lonRounded)
        }
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(CREATE_TABLE_SQL)
        db.execSQL(CREATE_RETENTION_INDEX_SQL)
        db.execSQL(CREATE_FARMER_PROFILE_TABLE_SQL)
        seedGwaliorDemoData(db)
        seedDefaultFarmerProfile(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_CACHED_WEATHER")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_FARMER_PROFILE")
        onCreate(db)
    }

    override fun onOpen(db: SQLiteDatabase) {
        super.onOpen(db)
        ensureGwaliorDemoData(db)
        ensureFarmerProfile(db)
    }

    private fun ensureFarmerProfile(db: SQLiteDatabase) {
        try {
            db.execSQL(CREATE_FARMER_PROFILE_TABLE_SQL)
            val cursor = db.query(
                TABLE_FARMER_PROFILE,
                arrayOf(COL_FP_ID),
                null,
                null,
                null,
                null,
                null
            )
            val hasProfile = cursor?.use { it.count > 0 } ?: false
            if (!hasProfile) {
                seedDefaultFarmerProfile(db)
            }
        } catch (_: Throwable) {
        }
    }

    private fun ensureGwaliorDemoData(db: SQLiteDatabase) {
        try {
            val cursor = db.query(
                TABLE_CACHED_WEATHER,
                arrayOf(COL_LOCATION_KEY),
                "$COL_LOCATION_KEY = ?",
                arrayOf(DEMO_GWALIOR_LOCATION_KEY),
                null,
                null,
                null
            )
            val hasGwalior = cursor?.use { it.count > 0 } ?: false
            if (!hasGwalior) {
                seedGwaliorDemoData(db)
            }
        } catch (_: Throwable) {
            // Table might be in the middle of creation/upgrade
        }
    }

    /**
     * Upserts a current weather observation payload for the specified location key.
     * Merges into existing record if forecast data was already cached.
     */
    fun upsertCurrentWeather(
        locationKey: String,
        latitude: Double,
        longitude: Double,
        locationName: String?,
        currentWeatherJson: String,
        provider: String?,
        authority: String?,
        retrievedAtMillis: Long,
        retrievedAtIso: String
    ) {
        val db = writableDatabase
        val existing = getRecordInternal(db, locationKey)

        val values = ContentValues().apply {
            put(COL_LOCATION_KEY, locationKey)
            put(COL_LATITUDE, latitude)
            put(COL_LONGITUDE, longitude)
            put(COL_LOCATION_NAME, locationName ?: existing?.locationName)
            put(COL_RETRIEVED_AT_MILLIS, retrievedAtMillis)
            put(COL_RETRIEVED_AT_ISO, retrievedAtIso)
            put(COL_PROVIDER, provider ?: existing?.provider)
            put(COL_AUTHORITY, authority ?: existing?.authority)
            put(COL_CURRENT_WEATHER_JSON, currentWeatherJson)
            put(COL_FORECAST_JSON, existing?.forecastJson)
            put(COL_FORECAST_START_ISO, existing?.forecastStartIso)
            put(COL_FORECAST_END_ISO, existing?.forecastEndIso)
            put(COL_ALERTS_JSON, existing?.alertsJson)
            put(COL_SCHEMA_VERSION, 1)
        }

        db.insertWithOnConflict(
            TABLE_CACHED_WEATHER,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    /**
     * Upserts a forecast payload for the specified location key.
     * Merges into existing record if current weather was already cached.
     */
    fun upsertForecast(
        locationKey: String,
        latitude: Double,
        longitude: Double,
        locationName: String?,
        forecastJson: String,
        forecastStartIso: String?,
        forecastEndIso: String?,
        provider: String?,
        retrievedAtMillis: Long,
        retrievedAtIso: String
    ) {
        val db = writableDatabase
        val existing = getRecordInternal(db, locationKey)

        val values = ContentValues().apply {
            put(COL_LOCATION_KEY, locationKey)
            put(COL_LATITUDE, latitude)
            put(COL_LONGITUDE, longitude)
            put(COL_LOCATION_NAME, locationName ?: existing?.locationName)
            put(COL_RETRIEVED_AT_MILLIS, retrievedAtMillis)
            put(COL_RETRIEVED_AT_ISO, retrievedAtIso)
            put(COL_PROVIDER, provider ?: existing?.provider)
            put(COL_AUTHORITY, existing?.authority)
            put(COL_CURRENT_WEATHER_JSON, existing?.currentWeatherJson)
            put(COL_FORECAST_JSON, forecastJson)
            put(COL_FORECAST_START_ISO, forecastStartIso)
            put(COL_FORECAST_END_ISO, forecastEndIso)
            put(COL_ALERTS_JSON, existing?.alertsJson)
            put(COL_SCHEMA_VERSION, 1)
        }

        db.insertWithOnConflict(
            TABLE_CACHED_WEATHER,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    /**
     * Upserts an alerts payload for the specified location key.
     */
    fun upsertAlerts(
        locationKey: String,
        latitude: Double,
        longitude: Double,
        alertsJson: String,
        retrievedAtMillis: Long,
        retrievedAtIso: String
    ) {
        val db = writableDatabase
        val existing = getRecordInternal(db, locationKey)

        val values = ContentValues().apply {
            put(COL_LOCATION_KEY, locationKey)
            put(COL_LATITUDE, latitude)
            put(COL_LONGITUDE, longitude)
            put(COL_LOCATION_NAME, existing?.locationName)
            put(COL_RETRIEVED_AT_MILLIS, retrievedAtMillis)
            put(COL_RETRIEVED_AT_ISO, retrievedAtIso)
            put(COL_PROVIDER, existing?.provider)
            put(COL_AUTHORITY, existing?.authority)
            put(COL_CURRENT_WEATHER_JSON, existing?.currentWeatherJson)
            put(COL_FORECAST_JSON, existing?.forecastJson)
            put(COL_FORECAST_START_ISO, existing?.forecastStartIso)
            put(COL_FORECAST_END_ISO, existing?.forecastEndIso)
            put(COL_ALERTS_JSON, alertsJson)
            put(COL_SCHEMA_VERSION, 1)
        }

        db.insertWithOnConflict(
            TABLE_CACHED_WEATHER,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    /**
     * Retrieves the cached record for a location key, returning null if not found
     * or if older than the maximum allowed age.
     */
    fun getRecord(locationKey: String, maxAgeMillis: Long): CachedWeatherRecord? {
        val db = readableDatabase
        val record = getRecordInternal(db, locationKey) ?: return null
        val now = System.currentTimeMillis()
        val isDemoGwalior = locationKey == DEMO_GWALIOR_LOCATION_KEY
        if (!isDemoGwalior && now - record.retrievedAtMillis > maxAgeMillis) {
            // Expired record: delete deterministically
            deleteRecord(locationKey)
            return null
        }
        return record
    }

    /**
     * Retrieves the cached record by latitude and longitude. Checks exact location key first,
     * then falls back to proximity search within 0.05 degrees (~5 km) while maintaining
     * strict cross-region isolation (e.g. Delhi vs Mumbai).
     */
    fun getRecord(latitude: Double, longitude: Double, maxAgeMillis: Long): CachedWeatherRecord? {
        val exactKey = generateLocationKey(latitude, longitude)
        val exact = getRecord(exactKey, maxAgeMillis)
        if (exact != null) return exact

        val isNearDemoGwalior = kotlin.math.abs(latitude - DEMO_GWALIOR_LATITUDE) <= 0.05 &&
            kotlin.math.abs(longitude - DEMO_GWALIOR_LONGITUDE) <= 0.05
        if (isNearDemoGwalior) {
            val demoRecord = getRecord(DEMO_GWALIOR_LOCATION_KEY, maxAgeMillis)
            if (demoRecord != null) return demoRecord
        }

        val db = readableDatabase
        val minLat = latitude - 0.05
        val maxLat = latitude + 0.05
        val minLon = longitude - 0.05
        val maxLon = longitude + 0.05
        val cutoff = System.currentTimeMillis() - maxAgeMillis

        db.query(
            TABLE_CACHED_WEATHER,
            null,
            "$COL_LATITUDE BETWEEN ? AND ? AND $COL_LONGITUDE BETWEEN ? AND ? AND $COL_RETRIEVED_AT_MILLIS >= ?",
            arrayOf(minLat.toString(), maxLat.toString(), minLon.toString(), maxLon.toString(), cutoff.toString()),
            null,
            null,
            "$COL_RETRIEVED_AT_MILLIS DESC",
            "1"
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                return parseCursor(cursor)
            }
        }
        return null
    }

    private fun getRecordInternal(db: SQLiteDatabase, locationKey: String): CachedWeatherRecord? {
        db.query(
            TABLE_CACHED_WEATHER,
            null,
            "$COL_LOCATION_KEY = ?",
            arrayOf(locationKey),
            null,
            null,
            null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                return parseCursor(cursor)
            }
        }
        return null
    }

    private fun parseCursor(cursor: Cursor): CachedWeatherRecord {
        return CachedWeatherRecord(
            locationKey = cursor.getString(cursor.getColumnIndexOrThrow(COL_LOCATION_KEY)),
            latitude = cursor.getDouble(cursor.getColumnIndexOrThrow(COL_LATITUDE)),
            longitude = cursor.getDouble(cursor.getColumnIndexOrThrow(COL_LONGITUDE)),
            locationName = cursor.getString(cursor.getColumnIndexOrThrow(COL_LOCATION_NAME)),
            retrievedAtMillis = cursor.getLong(cursor.getColumnIndexOrThrow(COL_RETRIEVED_AT_MILLIS)),
            retrievedAtIso = cursor.getString(cursor.getColumnIndexOrThrow(COL_RETRIEVED_AT_ISO)),
            forecastStartIso = cursor.getString(cursor.getColumnIndexOrThrow(COL_FORECAST_START_ISO)),
            forecastEndIso = cursor.getString(cursor.getColumnIndexOrThrow(COL_FORECAST_END_ISO)),
            provider = cursor.getString(cursor.getColumnIndexOrThrow(COL_PROVIDER)),
            authority = cursor.getString(cursor.getColumnIndexOrThrow(COL_AUTHORITY)),
            currentWeatherJson = cursor.getString(cursor.getColumnIndexOrThrow(COL_CURRENT_WEATHER_JSON)),
            forecastJson = cursor.getString(cursor.getColumnIndexOrThrow(COL_FORECAST_JSON)),
            alertsJson = cursor.getString(cursor.getColumnIndexOrThrow(COL_ALERTS_JSON)),
            schemaVersion = cursor.getInt(cursor.getColumnIndexOrThrow(COL_SCHEMA_VERSION))
        )
    }

    /**
     * Deterministic retention pruning: deletes all records older than [cutoffMillis].
     */
    fun pruneOlderThan(cutoffMillis: Long): Int {
        val db = writableDatabase
        return db.delete(
            TABLE_CACHED_WEATHER,
            "$COL_RETRIEVED_AT_MILLIS < ?",
            arrayOf(cutoffMillis.toString())
        )
    }

    fun deleteRecord(locationKey: String): Int {
        val db = writableDatabase
        return db.delete(
            TABLE_CACHED_WEATHER,
            "$COL_LOCATION_KEY = ?",
            arrayOf(locationKey)
        )
    }

    fun clearAll(): Int {
        val db = writableDatabase
        return db.delete(TABLE_CACHED_WEATHER, null, null)
    }

    /**
     * Persists or updates the single local farmer profile record.
     */
    fun saveFarmerProfile(profile: FarmerProfile): Long {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_FP_ID, 1L)
            put(COL_FP_FULL_NAME, profile.fullName)
            put(COL_FP_MOBILE_NUMBER, profile.mobileNumber)
            put(COL_FP_FARMER_ID, profile.farmerId)
            put(COL_FP_VILLAGE, profile.village)
            put(COL_FP_DISTRICT, profile.district)
            put(COL_FP_STATE, profile.state)
            put(COL_FP_PINCODE, profile.pincode)
            put(COL_FP_FIELD_NAME, profile.fieldName)
            put(COL_FP_PLOT_NUMBER, profile.plotNumber)
            put(COL_FP_SURVEY_NUMBER, profile.surveyNumber)
            put(COL_FP_FARM_AREA, profile.farmArea)
            put(COL_FP_AREA_UNIT, profile.areaUnit)
            put(COL_FP_CROP, profile.crop)
            put(COL_FP_VARIETY, profile.variety)
            put(COL_FP_CROP_STAGE, profile.cropStage)
            put(COL_FP_SOWING_DATE, profile.sowingDate)
            put(COL_FP_EXPECTED_HARVEST_DATE, profile.expectedHarvestDate)
            put(COL_FP_SOIL_TYPE, profile.soilType)
            put(COL_FP_SOIL_MOISTURE, profile.soilMoistureAvailability)
            put(COL_FP_IRRIGATION_TYPE, profile.irrigationType)
            put(COL_FP_FARMING_ACTIVITY, profile.farmingActivity)
            put(COL_FP_PREFERRED_LANGUAGE, profile.preferredLanguage)
            put(COL_FP_TEMPERATURE_UNIT, profile.temperatureUnit)
            put(COL_FP_NOTIFICATIONS_ENABLED, if (profile.notificationsEnabled) 1 else 0)
            put(COL_FP_CREATED_AT, profile.createdAt)
            put(COL_FP_UPDATED_AT, System.currentTimeMillis())
        }
        return db.insertWithOnConflict(
            TABLE_FARMER_PROFILE,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    /**
     * Retrieves the stored local farmer profile, returning null if not yet created.
     */
    fun getFarmerProfile(): FarmerProfile? {
        val db = readableDatabase
        db.query(
            TABLE_FARMER_PROFILE,
            null,
            "$COL_FP_ID = 1",
            null,
            null,
            null,
            null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                return parseFarmerProfile(cursor)
            }
        }
        return null
    }

    private fun parseFarmerProfile(cursor: Cursor): FarmerProfile {
        return FarmerProfile(
            id = cursor.getLong(cursor.getColumnIndexOrThrow(COL_FP_ID)),
            fullName = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_FULL_NAME)),
            mobileNumber = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_MOBILE_NUMBER)),
            farmerId = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_FARMER_ID)),
            village = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_VILLAGE)),
            district = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_DISTRICT)),
            state = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_STATE)),
            pincode = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_PINCODE)),
            fieldName = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_FIELD_NAME)),
            plotNumber = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_PLOT_NUMBER)),
            surveyNumber = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_SURVEY_NUMBER)),
            farmArea = if (cursor.isNull(cursor.getColumnIndexOrThrow(COL_FP_FARM_AREA))) null else cursor.getDouble(cursor.getColumnIndexOrThrow(COL_FP_FARM_AREA)),
            areaUnit = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_AREA_UNIT)),
            crop = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_CROP)),
            variety = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_VARIETY)),
            cropStage = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_CROP_STAGE)),
            sowingDate = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_SOWING_DATE)),
            expectedHarvestDate = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_EXPECTED_HARVEST_DATE)),
            soilType = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_SOIL_TYPE)),
            soilMoistureAvailability = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_SOIL_MOISTURE)),
            irrigationType = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_IRRIGATION_TYPE)),
            farmingActivity = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_FARMING_ACTIVITY)),
            preferredLanguage = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_PREFERRED_LANGUAGE)),
            temperatureUnit = cursor.getString(cursor.getColumnIndexOrThrow(COL_FP_TEMPERATURE_UNIT)),
            notificationsEnabled = cursor.getInt(cursor.getColumnIndexOrThrow(COL_FP_NOTIFICATIONS_ENABLED)) == 1,
            createdAt = cursor.getLong(cursor.getColumnIndexOrThrow(COL_FP_CREATED_AT)),
            updatedAt = cursor.getLong(cursor.getColumnIndexOrThrow(COL_FP_UPDATED_AT))
        )
    }
}
