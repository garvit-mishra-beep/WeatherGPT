package com.weathergpt.data.local

import android.content.Context
import com.weathergpt.data.mapper.Mappers.toDomain
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherAlertsResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.domain.model.farmer.FarmerProfile
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import com.weathergpt.domain.model.weather.WeatherForecast
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.ConcurrentHashMap

/**
 * Contract for persistent local storage of verified REAL weather responses.
 */
interface LocalWeatherDataSource {
    fun toLocationKey(latitude: Double, longitude: Double): String

    suspend fun saveCurrentWeather(
        latitude: Double,
        longitude: Double,
        dto: CurrentWeatherResponseDto,
        locationName: String? = null
    )

    suspend fun saveForecast(
        latitude: Double,
        longitude: Double,
        dto: WeatherForecastResponseDto,
        locationName: String? = null
    )

    suspend fun saveAlerts(
        latitude: Double,
        longitude: Double,
        dto: WeatherAlertsResponseDto
    )

    suspend fun getCachedCurrentWeather(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long = RETENTION_PERIOD_MILLIS
    ): CurrentWeather?

    suspend fun getCachedForecast(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long = RETENTION_PERIOD_MILLIS
    ): WeatherForecast?

    suspend fun getCachedAlerts(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long = RETENTION_PERIOD_MILLIS
    ): WeatherAlertsReport?

    suspend fun pruneOldEntries(retentionPeriodMillis: Long = RETENTION_PERIOD_MILLIS): Int

    suspend fun clear()

    suspend fun getFarmerProfile(): FarmerProfile?

    suspend fun saveFarmerProfile(profile: FarmerProfile): Long

    companion object {
        const val RETENTION_PERIOD_MILLIS = 3L * 24 * 60 * 60 * 1000L // 3 days (72 hours)
        const val SPRAY_FRESHNESS_MAX_AGE_MILLIS = 12L * 60 * 60 * 1000L // 12 hours for spray safety
    }
}

/**
 * Standard production implementation of [LocalWeatherDataSource] backed by SQLite.
 */
class SQLiteLocalWeatherDataSource(
    context: Context,
    dbName: String = WeatherDatabaseHelper.DATABASE_NAME,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) : LocalWeatherDataSource {

    private val dbHelper = WeatherDatabaseHelper(context.applicationContext, dbName)
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    override fun toLocationKey(latitude: Double, longitude: Double): String {
        return WeatherDatabaseHelper.generateLocationKey(latitude, longitude)
    }

    override suspend fun saveCurrentWeather(
        latitude: Double,
        longitude: Double,
        dto: CurrentWeatherResponseDto,
        locationName: String?
    ) = withContext(ioDispatcher) {
        val locationKey = toLocationKey(latitude, longitude)
        val nowMillis = System.currentTimeMillis()
        val nowIso = dto.provenance?.retrievalTimestamp ?: formatIsoUtc(nowMillis)
        val jsonString = json.encodeToString(CurrentWeatherResponseDto.serializer(), dto)

        dbHelper.upsertCurrentWeather(
            locationKey = locationKey,
            latitude = latitude,
            longitude = longitude,
            locationName = locationName,
            currentWeatherJson = jsonString,
            provider = dto.provenance?.provider ?: "Open-Meteo",
            authority = dto.provenance?.authority ?: "Operational Surface Ingestion",
            retrievedAtMillis = nowMillis,
            retrievedAtIso = nowIso
        )

        // Automatic opportunistic 3-day retention prune on write
        pruneOldEntriesInternal(nowMillis)
    }

    override suspend fun saveForecast(
        latitude: Double,
        longitude: Double,
        dto: WeatherForecastResponseDto,
        locationName: String?
    ) = withContext(ioDispatcher) {
        val locationKey = toLocationKey(latitude, longitude)
        val nowMillis = System.currentTimeMillis()
        val nowIso = dto.provenance?.retrievalTimestamp ?: formatIsoUtc(nowMillis)
        val jsonString = json.encodeToString(WeatherForecastResponseDto.serializer(), dto)

        dbHelper.upsertForecast(
            locationKey = locationKey,
            latitude = latitude,
            longitude = longitude,
            locationName = locationName,
            forecastJson = jsonString,
            forecastStartIso = dto.forecastStart,
            forecastEndIso = dto.forecastEnd,
            provider = dto.provenance?.provider ?: "Open-Meteo",
            retrievedAtMillis = nowMillis,
            retrievedAtIso = nowIso
        )

        pruneOldEntriesInternal(nowMillis)
    }

    override suspend fun saveAlerts(
        latitude: Double,
        longitude: Double,
        dto: WeatherAlertsResponseDto
    ) = withContext(ioDispatcher) {
        val locationKey = toLocationKey(latitude, longitude)
        val nowMillis = System.currentTimeMillis()
        val nowIso = formatIsoUtc(nowMillis)
        val jsonString = json.encodeToString(WeatherAlertsResponseDto.serializer(), dto)

        dbHelper.upsertAlerts(
            locationKey = locationKey,
            latitude = latitude,
            longitude = longitude,
            alertsJson = jsonString,
            retrievedAtMillis = nowMillis,
            retrievedAtIso = nowIso
        )
    }

    override suspend fun getCachedCurrentWeather(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long
    ): CurrentWeather? = withContext(ioDispatcher) {
        val record = dbHelper.getRecord(latitude, longitude, maxAgeMillis) ?: return@withContext null
        val currentWeatherJson = record.currentWeatherJson ?: return@withContext null

        try {
            val dto = json.decodeFromString(CurrentWeatherResponseDto.serializer(), currentWeatherJson)
            val domain = dto.toDomain()
            domain.copy(
                sourceMode = WeatherDataSourceMode.DEMO_MODE,
                retrievedAt = record.retrievedAtIso
            )
        } catch (_: Throwable) {
            null
        }
    }

    override suspend fun getCachedForecast(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long
    ): WeatherForecast? = withContext(ioDispatcher) {
        val record = dbHelper.getRecord(latitude, longitude, maxAgeMillis) ?: return@withContext null
        val forecastJson = record.forecastJson ?: return@withContext null

        try {
            val dto = json.decodeFromString(WeatherForecastResponseDto.serializer(), forecastJson)
            val domain = dto.toDomain()
            domain.copy(
                sourceMode = WeatherDataSourceMode.DEMO_MODE,
                retrievedAt = record.retrievedAtIso
            )
        } catch (_: Throwable) {
            null
        }
    }

    override suspend fun getCachedAlerts(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long
    ): WeatherAlertsReport? = withContext(ioDispatcher) {
        val locationKey = toLocationKey(latitude, longitude)
        val record = dbHelper.getRecord(locationKey, maxAgeMillis) ?: return@withContext null
        val alertsJson = record.alertsJson ?: return@withContext null

        try {
            val dto = json.decodeFromString(WeatherAlertsResponseDto.serializer(), alertsJson)
            val domain = dto.toDomain()
            // Phase 13: Filter out any alerts that have expired
            val nowMillis = System.currentTimeMillis()
            val activeAlerts = filterActiveAlerts(domain.alerts, nowMillis)

            domain.copy(
                alerts = activeAlerts,
                activeAlertsCount = activeAlerts.size,
                isCached = true
            )
        } catch (_: Throwable) {
            null
        }
    }

    override suspend fun pruneOldEntries(retentionPeriodMillis: Long): Int = withContext(ioDispatcher) {
        val cutoff = System.currentTimeMillis() - retentionPeriodMillis
        dbHelper.pruneOlderThan(cutoff)
    }

    private fun pruneOldEntriesInternal(nowMillis: Long) {
        val cutoff = nowMillis - LocalWeatherDataSource.RETENTION_PERIOD_MILLIS
        dbHelper.pruneOlderThan(cutoff)
    }

    override suspend fun clear() = withContext(ioDispatcher) {
        dbHelper.clearAll()
        Unit
    }

    override suspend fun getFarmerProfile(): FarmerProfile? = withContext(ioDispatcher) {
        dbHelper.getFarmerProfile()
    }

    override suspend fun saveFarmerProfile(profile: FarmerProfile): Long = withContext(ioDispatcher) {
        dbHelper.saveFarmerProfile(profile)
    }

    companion object {
        fun formatIsoUtc(millis: Long): String {
            val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
            sdf.timeZone = TimeZone.getTimeZone("UTC")
            return sdf.format(Date(millis))
        }

        fun filterActiveAlerts(alerts: List<OfficialAlert>, nowMillis: Long): List<OfficialAlert> {
            val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
            sdf.timeZone = TimeZone.getTimeZone("UTC")

            return alerts.filter { alert ->
                try {
                    val cleanExpiry = alert.expiresAt.substringBefore("Z").substringBefore("+")
                    val date = sdf.parse(cleanExpiry)
                    if (date != null) {
                        date.time >= nowMillis
                    } else {
                        true
                    }
                } catch (_: Throwable) {
                    true
                }
            }
        }
    }
}

/**
 * Lightweight, in-memory implementation of [LocalWeatherDataSource] useful for unit tests
 * or environments without Android Context.
 */
class InMemoryLocalWeatherDataSource(
    private val timeProvider: () -> Long = { System.currentTimeMillis() }
) : LocalWeatherDataSource {

    data class MemoryRecord(
        val locationKey: String,
        val latitude: Double,
        val longitude: Double,
        val locationName: String?,
        val retrievedAtMillis: Long,
        val retrievedAtIso: String,
        val currentWeather: CurrentWeather?,
        val forecast: WeatherForecast?,
        val alerts: WeatherAlertsReport?
    )

    private val cache = ConcurrentHashMap<String, MemoryRecord>()

    override fun toLocationKey(latitude: Double, longitude: Double): String {
        return WeatherDatabaseHelper.generateLocationKey(latitude, longitude)
    }

    override suspend fun saveCurrentWeather(
        latitude: Double,
        longitude: Double,
        dto: CurrentWeatherResponseDto,
        locationName: String?
    ) {
        val key = toLocationKey(latitude, longitude)
        val nowMillis = timeProvider()
        val nowIso = dto.provenance?.retrievalTimestamp ?: SQLiteLocalWeatherDataSource.formatIsoUtc(nowMillis)
        val domain = dto.toDomain()
        val existing = cache[key]

        cache[key] = MemoryRecord(
            locationKey = key,
            latitude = latitude,
            longitude = longitude,
            locationName = locationName ?: existing?.locationName,
            retrievedAtMillis = nowMillis,
            retrievedAtIso = nowIso,
            currentWeather = domain,
            forecast = existing?.forecast,
            alerts = existing?.alerts
        )
        pruneOldEntries()
    }

    override suspend fun saveForecast(
        latitude: Double,
        longitude: Double,
        dto: WeatherForecastResponseDto,
        locationName: String?
    ) {
        val key = toLocationKey(latitude, longitude)
        val nowMillis = timeProvider()
        val nowIso = dto.provenance?.retrievalTimestamp ?: SQLiteLocalWeatherDataSource.formatIsoUtc(nowMillis)
        val domain = dto.toDomain()
        val existing = cache[key]

        cache[key] = MemoryRecord(
            locationKey = key,
            latitude = latitude,
            longitude = longitude,
            locationName = locationName ?: existing?.locationName,
            retrievedAtMillis = nowMillis,
            retrievedAtIso = nowIso,
            currentWeather = existing?.currentWeather,
            forecast = domain,
            alerts = existing?.alerts
        )
        pruneOldEntries()
    }

    override suspend fun saveAlerts(
        latitude: Double,
        longitude: Double,
        dto: WeatherAlertsResponseDto
    ) {
        val key = toLocationKey(latitude, longitude)
        val nowMillis = timeProvider()
        val nowIso = SQLiteLocalWeatherDataSource.formatIsoUtc(nowMillis)
        val domain = dto.toDomain()
        val existing = cache[key]

        cache[key] = MemoryRecord(
            locationKey = key,
            latitude = latitude,
            longitude = longitude,
            locationName = existing?.locationName,
            retrievedAtMillis = nowMillis,
            retrievedAtIso = nowIso,
            currentWeather = existing?.currentWeather,
            forecast = existing?.forecast,
            alerts = domain
        )
    }

    override suspend fun getCachedCurrentWeather(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long
    ): CurrentWeather? {
        val key = toLocationKey(latitude, longitude)
        val rec = cache[key] ?: cache.values.firstOrNull {
            kotlin.math.abs(it.latitude - latitude) <= 0.05 &&
            kotlin.math.abs(it.longitude - longitude) <= 0.05
        } ?: return null
        val now = timeProvider()
        if (now - rec.retrievedAtMillis > maxAgeMillis) {
            cache.remove(rec.locationKey)
            return null
        }
        return rec.currentWeather?.copy(
            sourceMode = WeatherDataSourceMode.DEMO_MODE,
            retrievedAt = rec.retrievedAtIso
        )
    }

    override suspend fun getCachedForecast(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long
    ): WeatherForecast? {
        val key = toLocationKey(latitude, longitude)
        val rec = cache[key] ?: cache.values.firstOrNull {
            kotlin.math.abs(it.latitude - latitude) <= 0.05 &&
            kotlin.math.abs(it.longitude - longitude) <= 0.05
        } ?: return null
        val now = timeProvider()
        if (now - rec.retrievedAtMillis > maxAgeMillis) {
            cache.remove(rec.locationKey)
            return null
        }
        return rec.forecast?.copy(
            sourceMode = WeatherDataSourceMode.DEMO_MODE,
            retrievedAt = rec.retrievedAtIso
        )
    }

    override suspend fun getCachedAlerts(
        latitude: Double,
        longitude: Double,
        maxAgeMillis: Long
    ): WeatherAlertsReport? {
        val key = toLocationKey(latitude, longitude)
        val rec = cache[key] ?: return null
        val now = timeProvider()
        if (now - rec.retrievedAtMillis > maxAgeMillis) {
            cache.remove(key)
            return null
        }
        val rep = rec.alerts ?: return null
        val active = SQLiteLocalWeatherDataSource.filterActiveAlerts(rep.alerts, now)
        return rep.copy(
            alerts = active,
            activeAlertsCount = active.size,
            isCached = true
        )
    }

    override suspend fun pruneOldEntries(retentionPeriodMillis: Long): Int {
        val now = timeProvider()
        val cutoff = now - retentionPeriodMillis
        var count = 0
        val it = cache.entries.iterator()
        while (it.hasNext()) {
            val entry = it.next()
            if (entry.value.retrievedAtMillis < cutoff) {
                it.remove()
                count++
            }
        }
        return count
    }

    override suspend fun clear() {
        cache.clear()
    }

    private var inMemoryFarmerProfile: FarmerProfile? = FarmerProfile()

    override suspend fun getFarmerProfile(): FarmerProfile? = inMemoryFarmerProfile

    override suspend fun saveFarmerProfile(profile: FarmerProfile): Long {
        inMemoryFarmerProfile = profile
        return 1L
    }
}
