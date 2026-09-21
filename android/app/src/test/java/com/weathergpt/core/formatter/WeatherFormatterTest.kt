package com.weathergpt.core.formatter

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WeatherFormatterTest {

    @Test
    fun testFormatCondition_mapsKnownMachineIdentifiers() {
        assertEquals("Light drizzle", WeatherFormatter.formatCondition("light_drizzle"))
        assertEquals("Clear sky", WeatherFormatter.formatCondition("clear_sky"))
        assertEquals("Partly cloudy", WeatherFormatter.formatCondition("partly_cloudy"))
        assertEquals("Thunderstorm with hail", WeatherFormatter.formatCondition("thunderstorm_with_hail"))
        assertEquals("Overcast", WeatherFormatter.formatCondition("overcast"))
        assertEquals("Rime fog", WeatherFormatter.formatCondition("depositing_rime_fog"))
    }

    @Test
    fun testFormatCondition_fallbackFormatsUnknownSnakeCase() {
        assertEquals("Custom storm event", WeatherFormatter.formatCondition("custom_storm_event"))
        assertEquals("Heavy wind squall", WeatherFormatter.formatCondition("heavy-wind-squall"))
    }

    @Test
    fun testFormatCondition_handlesNullOrBlankSafely() {
        assertEquals("Partly cloudy", WeatherFormatter.formatCondition(null))
        assertEquals("Partly cloudy", WeatherFormatter.formatCondition(""))
        assertEquals("Partly cloudy", WeatherFormatter.formatCondition("   "))
    }

    @Test
    fun testDegreesToCardinal_convertsDegreesCorrectly() {
        assertEquals("N", WeatherFormatter.degreesToCardinal(0.0))
        assertEquals("N", WeatherFormatter.degreesToCardinal(360.0))
        assertEquals("E", WeatherFormatter.degreesToCardinal(90.0))
        assertEquals("S", WeatherFormatter.degreesToCardinal(180.0))
        assertEquals("W", WeatherFormatter.degreesToCardinal(270.0))
        assertEquals("SW", WeatherFormatter.degreesToCardinal(225.0))
        assertEquals("NE", WeatherFormatter.degreesToCardinal(45.0))
    }

    @Test
    fun testFormatWind_formatsSpeedAndDirection() {
        assertEquals("2 km/h SW", WeatherFormatter.formatWind(2.0, 225.0))
        assertEquals("15 km/h N", WeatherFormatter.formatWind(15.4, 0.0))
        assertEquals("2 km/h SW", WeatherFormatter.formatWind(null, null))
    }

    @Test
    fun testFormatObservationDateTime_formatsIsoTimestampWithoutRawIso() {
        val iso = "2026-09-07T15:00:00+00:00"
        val formatted = WeatherFormatter.formatObservationDateTime(iso)

        // Must never expose raw ISO timestamp with 'T' and '+00:00'
        assertFalse(formatted.contains("T15:00:00"))
        assertTrue(formatted.contains("2026"))
        assertTrue(formatted.contains("Sep"))
    }

    @Test
    fun testFormatObservationDateTime_handlesNullSafely() {
        assertEquals("Just now", WeatherFormatter.formatObservationDateTime(null))
        assertEquals("Just now", WeatherFormatter.formatObservationDateTime(""))
    }
}
