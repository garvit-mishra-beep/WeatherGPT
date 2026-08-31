package com.weathergpt.data.mapper

import com.weathergpt.data.mapper.Mappers.toDomain
import com.weathergpt.data.remote.dto.chat.ChatResponseDto
import com.weathergpt.data.remote.dto.chat.WeatherAlertDto
import com.weathergpt.data.remote.dto.farmer.CropWaterMetricsDto
import com.weathergpt.data.remote.dto.farmer.FarmerProvenanceDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryResponseDto
import com.weathergpt.data.remote.dto.gis.BoundaryUnitDto
import com.weathergpt.data.remote.dto.gis.LocationResolutionResponseDto
import com.weathergpt.data.remote.dto.map.MapSpecificationDto
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.LocationCoordDto
import com.weathergpt.domain.model.chat.DomainBrain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MappersTest {

    @Test
    fun `chat response mapping preserves brain enum and immutable alert severity`() {
        val dto = ChatResponseDto(
            responseId = "resp_1",
            sessionId = "sess_1",
            brain = "analyst",
            language = "en",
            createdAt = "2026-08-30T10:00:00Z",
            summary = "Heavy rain risk in South Gujarat.",
            answer = "Detailed analysis.",
            alert = WeatherAlertDto(
                source = "IMD",
                level = "Red",
                hazardType = "Flash Flood",
                headline = "Red Alert",
                description = "Severe flooding warning.",
                validUntil = "2026-08-31T00:00:00Z"
            )
        )

        val domain = dto.toDomain()
        assertEquals(DomainBrain.ANALYST, domain.brain)
        assertNotNull(domain.alert)
        assertEquals("Red", domain.alert?.level)
        assertEquals("Flash Flood", domain.alert?.hazardType)
    }

    @Test
    fun `weather mapping preserves numeric precision and location`() {
        val dto = CurrentWeatherResponseDto(
            location = LocationCoordDto(21.1702, 72.8311),
            observationTime = "2026-08-30T10:00:00Z",
            temperatureC = 32.45,
            feelsLikeC = 37.89,
            relativeHumidityPct = 81.2,
            precipitationMm = 4.25,
            rainIntensityCategory = "moderate",
            windSpeedKmh = 18.7,
            windDirectionDeg = 230.0,
            surfacePressureHpa = 1007.8,
            weatherCondition = "Rain Showers"
        )

        val domain = dto.toDomain()
        assertEquals(21.1702, domain.location.latitude, 0.00001)
        assertEquals(72.8311, domain.location.longitude, 0.00001)
        assertEquals(32.45, domain.temperatureC, 0.001)
        assertEquals(4.25, domain.precipitationMm, 0.001)
    }

    @Test
    fun `farmer mapping preserves exact water balance metrics`() {
        val dto = IrrigationAdvisoryResponseDto(
            action = "WAIT_RAIN_EXPECTED",
            urgency = "low",
            metrics = CropWaterMetricsDto(
                referenceEt0MmDay = 5.2,
                cropKc = 1.15,
                dailyWaterDemandMm = 5.98,
                forecastRainfall48hMm = 28.0,
                netDeficitMm = -22.02,
                finalDepletionMm = 0.0
            ),
            rationale = "Rainfall exceeds water demand.",
            provenance = FarmerProvenanceDto("FAO-56 Penman-Monteith")
        )

        val domain = dto.toDomain()
        assertEquals("WAIT_RAIN_EXPECTED", domain.action)
        assertEquals(5.2, domain.metrics.referenceEt0MmDay, 0.01)
        assertEquals(28.0, domain.metrics.forecastRainfall48hMm, 0.01)
    }

    @Test
    fun `map specification mapping correctly extracts coordinates from lon-lat array`() {
        val dto = MapSpecificationDto(
            mapId = "map_1",
            title = "Test Map",
            center = listOf(72.8311, 21.1702), // [longitude, latitude]
            zoom = 10.0
        )

        val domain = dto.toDomain()
        assertEquals(72.8311, domain.centerLongitude, 0.0001)
        assertEquals(21.1702, domain.centerLatitude, 0.0001)
    }

    @Test
    fun `location mapping preserves hierarchy`() {
        val dto = LocationResolutionResponseDto(
            latitude = 21.1702,
            longitude = 72.8311,
            isResolved = true,
            district = BoundaryUnitDto("IN-GJ-24", "Surat", "district")
        )

        val domain = dto.toDomain()
        assertTrue(domain.isResolved)
        assertEquals("Surat", domain.district?.name)
        assertEquals("district", domain.district?.level)
    }
}
