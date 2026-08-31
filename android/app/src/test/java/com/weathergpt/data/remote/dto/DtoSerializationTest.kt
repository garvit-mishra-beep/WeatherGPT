package com.weathergpt.data.remote.dto

import com.weathergpt.core.network.networkJson
import com.weathergpt.data.remote.dto.chat.ChatRequestDto
import com.weathergpt.data.remote.dto.chat.ChatResponseDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryRequestDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryResponseDto
import com.weathergpt.data.remote.dto.farmer.SprayWindowResponseDto
import com.weathergpt.data.remote.dto.gis.BoundaryResponseDto
import com.weathergpt.data.remote.dto.gis.GISAnalysisResponseDto
import com.weathergpt.data.remote.dto.gis.HazardIntersectionResponseDto
import com.weathergpt.data.remote.dto.gis.LocationResolutionResponseDto
import com.weathergpt.data.remote.dto.gis.RiskAssessmentResponseDto
import com.weathergpt.data.remote.dto.map.MapSpecificationDto
import com.weathergpt.data.remote.dto.nwp.GFSGridPointResponseDto
import com.weathergpt.data.remote.dto.nwp.NWPModelComparisonResponseDto
import com.weathergpt.data.remote.dto.system.HealthResponseDto
import com.weathergpt.data.remote.dto.system.ReadyResponseDto
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherAlertsResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DtoSerializationTest {

    @Test
    fun `deserializes health response payload`() {
        val json = """
            {
                "status": "healthy",
                "app_name": "WeatherGPT",
                "environment": "development",
                "version": "v1",
                "timestamp": "2026-08-30T10:00:00Z"
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<HealthResponseDto>(json)
        assertEquals("healthy", dto.status)
        assertEquals("development", dto.environment)
    }

    @Test
    fun `deserializes readiness response payload`() {
        val json = """
            {
                "status": "ready",
                "ready": true,
                "environment": "production",
                "dependencies": {
                    "database": {"status": "healthy", "latency_ms": 1.2, "postgis": "3.4"}
                },
                "timestamp": "2026-08-30T10:00:00Z"
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<ReadyResponseDto>(json)
        assertTrue(dto.ready)
        assertEquals("healthy", dto.dependencies?.get("database")?.status)
    }

    @Test
    fun `deserializes chat response payload with recommendation and alert`() {
        val json = """
            {
                "response_id": "resp_12345",
                "session_id": "sess_abc",
                "brain": "farmer",
                "language": "hi",
                "created_at": "2026-08-30T10:00:00Z",
                "summary": "सिंचाई स्थगित करें।",
                "answer": "आगामी 48 घंटों में 35 मिमी वर्षा की संभावना है।",
                "recommendation": {
                    "primary_action": "WAIT_RAIN_EXPECTED",
                    "urgency": "medium",
                    "actions": ["सिंचाई न करें", "जल निकासी सुनिश्चित करें"]
                },
                "alert": {
                    "source": "IMD",
                    "level": "Orange",
                    "hazard_type": "Heavy Rain",
                    "headline": "भारी वर्षा की चेतावनी",
                    "description": "सूरत में भारी वर्षा का पूर्वानुमान।",
                    "valid_until": "2026-08-31T12:00:00Z"
                },
                "visualizations": [
                    {
                        "type": "weather_card",
                        "id": "card_01",
                        "title": "Weather Outlook"
                    }
                ],
                "sources": [
                    {
                        "authority": "IMD",
                        "dataset": "CAP Alerts",
                        "retrieved_at": "2026-08-30T09:55:00Z",
                        "is_official": true
                    }
                ],
                "confidence": {
                    "evidence_level": "high",
                    "data_freshness_status": "fresh"
                },
                "limitations": []
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<ChatResponseDto>(json)
        assertEquals("resp_12345", dto.responseId)
        assertEquals("farmer", dto.brain)
        assertEquals("Orange", dto.alert?.level)
        assertEquals("WAIT_RAIN_EXPECTED", dto.recommendation?.primaryAction)
        assertEquals(1, dto.sources.size)
        assertTrue(dto.sources[0].isOfficial)
    }

    @Test
    fun `deserializes current weather observation payload`() {
        val json = """
            {
                "location": {"latitude": 21.1702, "longitude": 72.8311},
                "observation_time": "2026-08-30T10:00:00Z",
                "temperature_c": 31.5,
                "feels_like_c": 36.2,
                "relative_humidity_pct": 78.0,
                "precipitation_mm": 0.0,
                "rain_intensity_category": "none",
                "wind_speed_kmh": 14.5,
                "wind_direction_deg": 240.0,
                "surface_pressure_hpa": 1008.2,
                "weather_condition": "Partly Cloudy",
                "provenance": {
                    "provider": "open_meteo",
                    "authority": "WMO / Open-Meteo",
                    "quality": "high"
                }
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<CurrentWeatherResponseDto>(json)
        assertEquals(21.1702, dto.location.latitude, 0.0001)
        assertEquals(31.5, dto.temperatureC, 0.01)
        assertEquals("Partly Cloudy", dto.weatherCondition)
    }

    @Test
    fun `deserializes weather forecast payload`() {
        val json = """
            {
                "location": {"latitude": 21.1702, "longitude": 72.8311},
                "generated_at": "2026-08-30T10:00:00Z",
                "forecast_start": "2026-08-30T00:00:00Z",
                "forecast_end": "2026-09-02T00:00:00Z",
                "daily_forecast": [
                    {
                        "date": "2026-08-30",
                        "temp_max_c": 33.0,
                        "temp_min_c": 26.0,
                        "precipitation_sum_mm": 12.5,
                        "precipitation_probability_pct": 80.0,
                        "wind_speed_max_kmh": 22.0,
                        "dominant_condition": "Rain"
                    }
                ]
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<WeatherForecastResponseDto>(json)
        assertEquals(1, dto.dailyForecast.size)
        assertEquals(12.5, dto.dailyForecast[0].precipitationSumMm, 0.01)
    }

    @Test
    fun `deserializes official weather alerts payload`() {
        val json = """
            {
                "authority": "India Meteorological Department (IMD)",
                "retrieved_at": "2026-08-30T10:00:00Z",
                "active_alerts_count": 1,
                "alerts": [
                    {
                        "alert_id": "IMD-WARN-2026-08-30-01",
                        "warning_color": "Red",
                        "hazard": "Heavy Rainfall",
                        "severity": "Extreme",
                        "area_description": "South Gujarat Coastal Belt",
                        "headline": "Extremely Heavy Rainfall Warning",
                        "description": "Very heavy rainfall expected over Surat and Navsari.",
                        "effective_from": "2026-08-30T10:00:00Z",
                        "expires_at": "2026-08-31T10:00:00Z"
                    }
                ]
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<WeatherAlertsResponseDto>(json)
        assertEquals(1, dto.activeAlertsCount)
        assertEquals("Red", dto.alerts[0].warningColor)
    }

    @Test
    fun `deserializes irrigation advisory payload`() {
        val json = """
            {
                "action": "IRRIGATE",
                "urgency": "high",
                "metrics": {
                    "reference_et0_mm_day": 5.4,
                    "crop_kc": 1.15,
                    "daily_water_demand_mm": 6.21,
                    "forecast_rainfall_48h_mm": 0.0,
                    "net_deficit_mm": 6.21,
                    "final_depletion_mm": 45.0
                },
                "rationale": "Soil moisture has depleted past MAD threshold.",
                "provenance": {
                    "calculation_method": "FAO-56 Penman-Monteith (Deterministic Engine)",
                    "engine_version": "1.0.0"
                }
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<IrrigationAdvisoryResponseDto>(json)
        assertEquals("IRRIGATE", dto.action)
        assertEquals(5.4, dto.metrics.referenceEt0MmDay, 0.01)
    }

    @Test
    fun `deserializes spray window payload`() {
        val json = """
            {
                "is_suitable": true,
                "condition_level": "optimal",
                "recommendation": "Optimal spray window available for the next 4 hours.",
                "wind_suitable": true,
                "rain_probability_suitable": true
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<SprayWindowResponseDto>(json)
        assertTrue(dto.isSuitable)
        assertEquals("optimal", dto.conditionLevel)
    }

    @Test
    fun `deserializes location reverse geocoding payload`() {
        val json = """
            {
                "latitude": 21.1702,
                "longitude": 72.8311,
                "is_resolved": true,
                "country": {"code": "IN", "name": "India", "level": "country"},
                "state": {"code": "IN-GJ", "name": "Gujarat", "level": "state"},
                "district": {"code": "IN-GJ-24", "name": "Surat", "level": "district"},
                "subdistrict": {"code": "IN-GJ-24-01", "name": "Chorasi", "level": "subdistrict"}
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<LocationResolutionResponseDto>(json)
        assertTrue(dto.isResolved)
        assertEquals("Surat", dto.district?.name)
        assertEquals("Gujarat", dto.state?.name)
    }

    @Test
    fun `deserializes GFS NWP grid point payload`() {
        val json = """
            {
                "model": "GFS_0p25",
                "grid_resolution_deg": 0.25,
                "location": {"latitude": 21.25, "longitude": 72.75},
                "forecast_lead_hours": 24,
                "valid_time": "2026-08-31T00:00:00Z",
                "atmospheric_variables": {
                    "temperature_2m_c": 29.4,
                    "relative_humidity_2m_pct": 82.0,
                    "accumulated_precip_mm": 18.5,
                    "wind_speed_kmh": 16.2,
                    "wind_direction_deg": 235.0,
                    "pressure_msl_hpa": 1007.5,
                    "total_cloud_cover_pct": 75.0
                }
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<GFSGridPointResponseDto>(json)
        assertEquals("GFS_0p25", dto.model)
        assertEquals(18.5, dto.atmosphericVariables.accumulatedPrecipMm, 0.01)
    }

    @Test
    fun `deserializes map specification payload`() {
        val json = """
            {
                "map_id": "map_weather_point_2117_7283",
                "title": "Weather Observation - Surat",
                "center": [72.8311, 21.1702],
                "zoom": 10.0,
                "layers": [
                    {
                        "id": "layer_point_marker",
                        "type": "circle",
                        "title": "Surat Station",
                        "visible": true
                    }
                ],
                "legend": [
                    {"label": "Active AWS", "color": "#0284C7"}
                ]
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<MapSpecificationDto>(json)
        assertEquals("map_weather_point_2117_7283", dto.mapId)
        assertEquals(72.8311, dto.center!![0], 0.0001) // Longitude first
        assertEquals(21.1702, dto.center!![1], 0.0001) // Latitude second
        assertEquals(1, dto.layers.size)
        assertEquals(1, dto.legend.size)
    }
}
