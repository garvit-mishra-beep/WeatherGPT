package com.weathergpt.data.local

import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.DailyForecastDto
import com.weathergpt.data.remote.dto.weather.HourlyForecastDto
import com.weathergpt.data.remote.dto.weather.LocationCoordDto
import com.weathergpt.data.remote.dto.weather.OfficialAlertItemDto
import com.weathergpt.data.remote.dto.weather.WeatherAlertsResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherProvenanceDto
import com.weathergpt.domain.model.weather.WeatherDataSourceMode
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LocalWeatherDataSourceTest {

    private var currentTimeMillis = 1789036800000L // Baseline timestamp (e.g. 10 Sep 2026 12:00 UTC)
    private lateinit var dataSource: InMemoryLocalWeatherDataSource

    @Before
    fun setup() {
        currentTimeMillis = 1789036800000L
        dataSource = InMemoryLocalWeatherDataSource(timeProvider = { currentTimeMillis })
    }

    private fun sampleCurrentDto(lat: Double, lon: Double, temp: Double = 32.5): CurrentWeatherResponseDto {
        return CurrentWeatherResponseDto(
            location = LocationCoordDto(latitude = lat, longitude = lon),
            observationTime = "2026-09-10T12:00:00Z",
            temperatureC = temp,
            feelsLikeC = temp + 2.0,
            relativeHumidityPct = 65.0,
            precipitationMm = 0.0,
            rainIntensityCategory = "None",
            windSpeedKmh = 14.0,
            windDirectionDeg = 180.0,
            surfacePressureHpa = 1012.0,
            weatherCondition = "Partly Cloudy",
            provenance = WeatherProvenanceDto(
                provider = "Open-Meteo",
                authority = "Operational Surface Ingestion",
                quality = "VERIFIED",
                retrievalTimestamp = "2026-09-10T12:00:00Z"
            )
        )
    }

    private fun sampleForecastDto(lat: Double, lon: Double): WeatherForecastResponseDto {
        return WeatherForecastResponseDto(
            location = LocationCoordDto(latitude = lat, longitude = lon),
            generatedAt = "2026-09-10T12:00:00Z",
            forecastStart = "2026-09-10T00:00:00Z",
            forecastEnd = "2026-09-13T00:00:00Z",
            dailyForecast = listOf(
                DailyForecastDto(
                    date = "2026-09-10",
                    tempMaxC = 34.0,
                    tempMinC = 26.0,
                    precipitationSumMm = 1.2,
                    precipitationProbabilityPct = 30.0,
                    windSpeedMaxKmh = 18.0,
                    dominantCondition = "Partly Cloudy"
                )
            ),
            hourlyForecast = listOf(
                HourlyForecastDto(
                    time = "2026-09-10T13:00:00Z",
                    temperatureC = 33.0,
                    relativeHumidityPct = 62.0,
                    precipitationMm = 0.0,
                    precipitationProbabilityPct = 20.0,
                    windSpeedKmh = 12.0,
                    condition = "Partly Cloudy"
                )
            ),
            provenance = WeatherProvenanceDto(
                provider = "Open-Meteo",
                authority = "Numerical Weather Prediction",
                quality = "VERIFIED"
            )
        )
    }

    @Test
    fun `save and retrieve current weather returns DEMO_MODE with preserved provenance`() = runTest {
        val lat = 25.4484
        val lon = 78.5685
        val dto = sampleCurrentDto(lat, lon, temp = 31.8)

        dataSource.saveCurrentWeather(lat, lon, dto, locationName = "Jhansi")
        val cached = dataSource.getCachedCurrentWeather(lat, lon)

        assertNotNull("Cached record must exist", cached)
        assertEquals(WeatherDataSourceMode.DEMO_MODE, cached!!.sourceMode)
        assertEquals("Open-Meteo", cached.provider)
        assertEquals(31.8, cached.temperatureC, 0.01)
        assertNotNull("retrievedAt must be preserved", cached.retrievedAt)
    }

    @Test
    fun `location isolation ensures Delhi cache is never returned for Mumbai`() = runTest {
        val delhiLat = 28.6139
        val delhiLon = 77.2090
        val mumbaiLat = 19.0760
        val mumbaiLon = 72.8777

        dataSource.saveCurrentWeather(delhiLat, delhiLon, sampleCurrentDto(delhiLat, delhiLon, temp = 38.0))

        val delhiCached = dataSource.getCachedCurrentWeather(delhiLat, delhiLon)
        val mumbaiCached = dataSource.getCachedCurrentWeather(mumbaiLat, mumbaiLon)

        assertNotNull("Delhi weather must exist", delhiCached)
        assertEquals(38.0, delhiCached!!.temperatureC, 0.01)
        assertNull("Mumbai weather must be null since it was never cached", mumbaiCached)
    }

    @Test
    fun `three-day retention prunes entries older than 72 hours`() = runTest {
        val lat = 26.2183
        val lon = 78.1828

        // Day 1: Save weather at baseline
        dataSource.saveCurrentWeather(lat, lon, sampleCurrentDto(lat, lon, temp = 30.0))
        assertNotNull(dataSource.getCachedCurrentWeather(lat, lon))

        // Advance clock by 2 days (48 hours) -> Should still survive
        currentTimeMillis += 48L * 60 * 60 * 1000L
        assertNotNull("Should survive 48 hours", dataSource.getCachedCurrentWeather(lat, lon))

        // Advance clock past 72 hours (73 hours total from baseline)
        currentTimeMillis += 25L * 60 * 60 * 1000L // 48 + 25 = 73 hours
        val expired = dataSource.getCachedCurrentWeather(lat, lon)
        assertNull("Entries older than 72 hours must be pruned and return null", expired)
    }

    @Test
    fun `repeated writes for same location update data without creating duplicate entries`() = runTest {
        val lat = 25.4484
        val lon = 78.5685

        // First write
        dataSource.saveCurrentWeather(lat, lon, sampleCurrentDto(lat, lon, temp = 31.0))
        var cached = dataSource.getCachedCurrentWeather(lat, lon)
        assertEquals(31.0, cached!!.temperatureC, 0.01)

        // Second write 1 hour later
        currentTimeMillis += 3600_000L
        dataSource.saveCurrentWeather(lat, lon, sampleCurrentDto(lat, lon, temp = 33.5))
        cached = dataSource.getCachedCurrentWeather(lat, lon)

        assertEquals(33.5, cached!!.temperatureC, 0.01)
    }

    @Test
    fun `cached alerts filter out expired warnings deterministically`() = runTest {
        val lat = 25.4484
        val lon = 78.5685

        val alertsDto = WeatherAlertsResponseDto(
            authority = "India Meteorological Department (IMD)",
            retrievedAt = "2026-09-10T12:00:00Z",
            activeAlertsCount = 2,
            alerts = listOf(
                OfficialAlertItemDto(
                    alertId = "alert_active",
                    warningColor = "Orange",
                    hazard = "Heavy Rainfall",
                    severity = "Severe",
                    areaDescription = "Jhansi District",
                    headline = "Heavy rain expected",
                    description = "Heavy rainfall of 70mm expected",
                    effectiveFrom = "2026-09-10T10:00:00Z",
                    expiresAt = "2026-09-10T20:00:00Z" // Future expiry (now is 12:00)
                ),
                OfficialAlertItemDto(
                    alertId = "alert_expired",
                    warningColor = "Yellow",
                    hazard = "Thunderstorm",
                    severity = "Moderate",
                    areaDescription = "Jhansi District",
                    headline = "Past thunderstorm",
                    description = "Thunderstorm passed",
                    effectiveFrom = "2026-09-10T06:00:00Z",
                    expiresAt = "2026-09-10T10:00:00Z" // Past expiry
                )
            )
        )

        dataSource.saveAlerts(lat, lon, alertsDto)
        val report = dataSource.getCachedAlerts(lat, lon)

        assertNotNull("Alerts report must exist", report)
        assertTrue("Report must be marked isCached = true", report!!.isCached)
        assertEquals("Expired alert must be filtered out", 1, report.alerts.size)
        assertEquals("alert_active", report.alerts.first().alertId)
    }

    @Test
    fun `save and retrieve forecast preserves forecast valid times and hourly items`() = runTest {
        val lat = 25.4484
        val lon = 78.5685
        val dto = sampleForecastDto(lat, lon)

        dataSource.saveForecast(lat, lon, dto, locationName = "Jhansi")
        val cached = dataSource.getCachedForecast(lat, lon)

        assertNotNull(cached)
        assertEquals(WeatherDataSourceMode.DEMO_MODE, cached!!.sourceMode)
        assertEquals("2026-09-10T00:00:00Z", cached.forecastStart)
        assertEquals("2026-09-13T00:00:00Z", cached.forecastEnd)
        assertEquals(1, cached.dailyForecast.size)
        assertEquals(1, cached.hourlyForecast?.size)
    }
}
