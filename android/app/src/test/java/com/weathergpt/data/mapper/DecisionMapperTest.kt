package com.weathergpt.data.mapper

import com.weathergpt.data.mapper.Mappers.toDomain
import com.weathergpt.data.remote.dto.decision.ActionWindowDto
import com.weathergpt.data.remote.dto.decision.ActionWindowPeriodDto
import com.weathergpt.data.remote.dto.decision.CandidateHourEvaluationDto
import com.weathergpt.data.remote.dto.decision.EvidenceLedgerDto
import com.weathergpt.data.remote.dto.decision.LedgerRuleEvaluationDto
import com.weathergpt.data.remote.dto.decision.NirnayCardDto
import com.weathergpt.domain.model.decision.DecisionConfidence
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionVerdict
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DecisionMapperTest {

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    @Test
    fun testNirnayCardDtoMapping_AvailableActionWindow() {
        val dto = NirnayCardDto(
            question = "Should I spray my cotton tonight?",
            verdict = "POSTPONE",
            severity = "high",
            recommendedAction = "Do not spray tonight. Wait for favorable morning window.",
            actionWindow = ActionWindowDto(
                status = "available",
                bestWindow = ActionWindowPeriodDto(
                    windowId = "win_01",
                    startTimeIso = "2026-09-08T06:00:00+05:30",
                    endTimeIso = "2026-09-08T09:00:00+05:30",
                    durationHours = 3,
                    score = 63.89,
                    avgWindSpeedKmh = 9.33,
                    maxWindSpeedKmh = 11.0,
                    maxRainProbabilityPct = 15.0,
                    totalRainfallMm = 0.0,
                    summary = "Tomorrow 06:00 - 09:00 IST",
                    recommended = true
                ),
                fallbackWindows = listOf(
                    ActionWindowPeriodDto(
                        windowId = "win_02",
                        startTimeIso = "2026-09-08T16:00:00+05:30",
                        endTimeIso = "2026-09-08T18:00:00+05:30",
                        durationHours = 2,
                        score = 55.4,
                        avgWindSpeedKmh = 12.0,
                        maxWindSpeedKmh = 14.0,
                        maxRainProbabilityPct = 20.0,
                        totalRainfallMm = 0.0,
                        summary = "Tomorrow 16:00 - 18:00 IST",
                        recommended = false
                    )
                ),
                score = 63.89,
                reason = "Optimal 3-hour spray window identified from 06:00 to 09:00",
                hourlyEvaluations = listOf(
                    CandidateHourEvaluationDto(
                        timeIso = "2026-09-08T06:00:00+05:30",
                        windSpeedKmh = 8.0,
                        rainProbabilityPct = 10.0,
                        precipitationMm = 0.0,
                        passed = true
                    ),
                    CandidateHourEvaluationDto(
                        timeIso = "2026-09-08T10:00:00+05:30",
                        windSpeedKmh = 18.0,
                        rainProbabilityPct = 20.0,
                        precipitationMm = 0.0,
                        passed = false,
                        failedReasons = listOf("Wind speed 18.0 km/h > 15.0 km/h")
                    )
                )
            ),
            confidence = "high",
            why = listOf("High wind speed (18.0 km/h) exceeds safe threshold (15.0 km/h)"),
            alternatives = listOf("Wait until tomorrow morning 06:00 - 09:00 IST"),
            ledger = EvidenceLedgerDto(
                decisionId = "dec_test123",
                timestamp = "2026-09-07T21:00:00Z",
                question = "Should I spray my cotton tonight?",
                rules = listOf(
                    LedgerRuleEvaluationDto(
                        ruleName = "wind_drift_threshold",
                        threshold = JsonPrimitive(15.0),
                        observedValue = JsonPrimitive(18.0),
                        unit = "km/h",
                        operator = "<=",
                        satisfied = false,
                        rationale = "Wind exceeds safe spray threshold"
                    )
                )
            )
        )

        val domain = dto.toDomain()

        assertEquals("Should I spray my cotton tonight?", domain.question)
        assertEquals(DecisionVerdict.POSTPONE, domain.verdict)
        assertEquals(DecisionSeverity.HIGH, domain.severity)
        assertEquals(DecisionConfidence.HIGH, domain.confidence)
        assertTrue(domain.actionWindow.isAvailable)
        assertNotNull(domain.actionWindow.bestWindow)
        assertEquals("win_01", domain.actionWindow.bestWindow?.windowId)
        assertEquals(3, domain.actionWindow.bestWindow?.durationHours)
        assertEquals(1, domain.actionWindow.fallbackWindows.size)
        assertEquals(2, domain.actionWindow.hourlyEvaluations?.size)
        assertFalse(domain.actionWindow.hourlyEvaluations?.get(1)?.passed ?: true)

        assertNotNull(domain.ledger)
        assertEquals("dec_test123", domain.ledger?.decisionId)
        assertEquals(1, domain.ledger?.rules?.size)
        assertFalse(domain.ledger?.rules?.first()?.satisfied ?: true)
        assertEquals("18.0", domain.ledger?.rules?.first()?.observedValue)
    }

    @Test
    fun testNirnayCardDtoMapping_UnavailableActionWindow() {
        val dto = NirnayCardDto(
            question = "Should I spray my cotton tonight?",
            verdict = "NO_GO",
            severity = "critical",
            recommendedAction = "Do not spray. Severe wind and rain hazard.",
            actionWindow = ActionWindowDto(
                status = "unavailable",
                bestWindow = null,
                fallbackWindows = emptyList(),
                reason = "No valid operational window found across forecast horizon due to persistent storm activity."
            ),
            confidence = "high",
            why = listOf("Rain probability 85% exceeds threshold 30%"),
            alternatives = listOf("Review forecast in 24 hours")
        )

        val domain = dto.toDomain()

        assertEquals(DecisionVerdict.NO_GO, domain.verdict)
        assertEquals(DecisionSeverity.CRITICAL, domain.severity)
        assertFalse(domain.actionWindow.isAvailable)
        assertNull(domain.actionWindow.bestWindow)
        assertTrue(domain.actionWindow.fallbackWindows.isEmpty())
        assertTrue(domain.actionWindow.reason.contains("persistent storm activity"))
    }

    // ========================================================================
    // Phase 3.5 Alert-to-Impact Intelligence Tests
    // ========================================================================

    @Test
    fun testAlertImpact_RedInside_DirectlyAffected() {
        val dto = NirnayCardDto(
            question = "There is a red rainfall warning near me. What should I do?",
            verdict = "NO_GO",
            severity = "critical",
            recommendedAction = "EMERGENCY: Suspend all outdoor operations immediately. Seek reinforced shelter.",
            actionWindow = ActionWindowDto(
                status = "unavailable",
                reason = "Action windows completely suppressed during active Red Alert."
            ),
            confidence = "high",
            uncertainty = kotlinx.serialization.json.buildJsonObject {
                put("statement", JsonPrimitive("Guidance based on NOAA GFS 0.25° NWP."))
            },
            why = listOf(
                "Official NDMA_SACHET Red Alert is active until 2026-09-08T23:59:59+05:30.",
                "Spatial exposure verified as INSIDE warning perimeter."
            ),
            impact = kotlinx.serialization.json.buildJsonObject {
                put("primary_risk", JsonPrimitive("Catastrophic flooding hazard requiring immediate operational cessation."))
                put("loss_potential", JsonPrimitive("Total destruction of chemical residue and severe canopy damage."))
                put("composite_impact_score", JsonPrimitive("8.5/10.0"))
                put("risk_category", JsonPrimitive("critical"))
                put("exposed_area_sqkm", JsonPrimitive(1250.0))
                put("exposure_state", JsonPrimitive("INSIDE"))
            },
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-NDMA-RED-001"))
                put("hazard_type", JsonPrimitive("Extremely Heavy Rainfall & Localized Inundation"))
                put("issuing_office", JsonPrimitive("NDMA_SACHET"))
                put("is_official", JsonPrimitive(true))
                put("primary_warning_level", JsonPrimitive("Red"))
                put("exposure_state", JsonPrimitive("INSIDE"))
                put("composite_impact_score", JsonPrimitive(8.5))
                put("affected_area_name", JsonPrimitive("Gwalior district and adjoining Chambal belt"))
            }
        )

        val domain = dto.toDomain()

        assertEquals(DecisionVerdict.NO_GO, domain.verdict)
        assertEquals(DecisionSeverity.CRITICAL, domain.severity)
        assertNotNull(domain.alertImpact)
        val impact = domain.alertImpact!!
        assertEquals("ALERT-NDMA-RED-001", impact.alertId)
        assertEquals("Extremely Heavy Rainfall & Localized Inundation", impact.hazard)
        assertEquals("NDMA_SACHET", impact.issuingOffice)
        assertTrue(impact.isOfficial)
        assertEquals("Red", impact.alertSeverity)
        assertEquals(com.weathergpt.domain.model.decision.ExposureState.INSIDE, impact.affectedAreaStatus)
        assertEquals("AVAILABLE", impact.exposureStatus)
        assertEquals("Directly inside active warning area", impact.exposureSummary)
        assertEquals("Gwalior district and adjoining Chambal belt", impact.affectedAreaName)
        assertEquals(1250.0, impact.exposedAreaSqkm ?: 0.0, 0.01)
        assertEquals(8.5, impact.compositeImpactScore ?: 0.0, 0.01)
        assertEquals("critical", impact.riskCategory)
        assertTrue(domain.uncertainty.exposureDataAvailable)
    }

    @Test
    fun testAlertImpact_OrangeInside_PostponesAndShift() {
        val dto = NirnayCardDto(
            question = "Should I spray pesticide on cotton today?",
            verdict = "POSTPONE",
            severity = "high",
            recommendedAction = "Postpone application until active Orange Alert expires.",
            actionWindow = ActionWindowDto(
                status = "available",
                reason = "Action window shifted post alert expiration."
            ),
            confidence = "high",
            impact = kotlinx.serialization.json.buildJsonObject {
                put("primary_risk", JsonPrimitive("Severe convective squall risk."))
                put("composite_impact_score", JsonPrimitive("6.2/10.0"))
                put("risk_category", JsonPrimitive("high"))
                put("exposure_state", JsonPrimitive("INSIDE"))
            },
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-NDMA-ORG-002"))
                put("hazard_type", JsonPrimitive("Heavy Rain & Wind Squalls"))
                put("issuing_office", JsonPrimitive("NDMA_SACHET"))
                put("is_official", JsonPrimitive(true))
                put("primary_warning_level", JsonPrimitive("Orange"))
                put("exposure_state", JsonPrimitive("INSIDE"))
                put("composite_impact_score", JsonPrimitive(6.2))
            }
        )

        val domain = dto.toDomain()

        assertEquals(DecisionVerdict.POSTPONE, domain.verdict)
        assertEquals(DecisionSeverity.HIGH, domain.severity)
        assertNotNull(domain.alertImpact)
        assertEquals(com.weathergpt.domain.model.decision.ExposureState.INSIDE, domain.alertImpact?.affectedAreaStatus)
        assertEquals("Orange", domain.alertImpact?.alertSeverity)
        assertEquals(6.2, domain.alertImpact?.compositeImpactScore ?: 0.0, 0.01)
    }

    @Test
    fun testAlertImpact_RedOutside_LocationOutsideActiveWarning() {
        val dto = NirnayCardDto(
            question = "Is it safe for outdoor field work?",
            verdict = "PROCEED_WITH_CAUTION",
            severity = "moderate",
            recommendedAction = "Proceed with caution; location is outside active warning boundary.",
            actionWindow = ActionWindowDto(status = "available", reason = "Local window valid"),
            confidence = "high",
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-REGIONAL-RED-003"))
                put("hazard_type", JsonPrimitive("Regional Severe Cyclone Warning"))
                put("issuing_office", JsonPrimitive("NDMA_SACHET"))
                put("is_official", JsonPrimitive(true))
                put("primary_warning_level", JsonPrimitive("Red"))
                put("exposure_state", JsonPrimitive("OUTSIDE"))
                put("affected_area_name", JsonPrimitive("Coastal Saurashtra belt"))
            }
        )

        val domain = dto.toDomain()

        assertNotNull(domain.alertImpact)
        assertEquals(com.weathergpt.domain.model.decision.ExposureState.OUTSIDE, domain.alertImpact?.affectedAreaStatus)
        assertEquals("Outside active warning area", domain.alertImpact?.exposureSummary)
        assertEquals("AVAILABLE", domain.alertImpact?.exposureStatus)
        assertEquals(DecisionVerdict.PROCEED_WITH_CAUTION, domain.verdict)
    }

    @Test
    fun testAlertImpact_Buffer_NearWarningBoundary() {
        val dto = NirnayCardDto(
            question = "Is the storm approaching my farm?",
            verdict = "PROCEED_WITH_CAUTION",
            severity = "moderate",
            recommendedAction = "Maintain active weather watch. Location is adjacent to alert boundary.",
            actionWindow = ActionWindowDto(status = "available", reason = "Window active"),
            confidence = "medium",
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-BUF-004"))
                put("hazard_type", JsonPrimitive("Thunderstorm & Hail"))
                put("issuing_office", JsonPrimitive("NDMA"))
                put("is_official", JsonPrimitive(true))
                put("primary_warning_level", JsonPrimitive("Orange"))
                put("exposure_state", JsonPrimitive("BUFFER"))
                put("affected_area_name", JsonPrimitive("Northern border zone"))
            }
        )

        val domain = dto.toDomain()

        assertNotNull(domain.alertImpact)
        assertEquals(com.weathergpt.domain.model.decision.ExposureState.BUFFER, domain.alertImpact?.affectedAreaStatus)
        assertEquals("Near warning boundary (within 25 km buffer)", domain.alertImpact?.exposureSummary)
        assertEquals("AVAILABLE", domain.alertImpact?.exposureStatus)
    }

    @Test
    fun testAlertImpact_Unknown_AffectedAreaUnverified() {
        val dto = NirnayCardDto(
            question = "What is the status of the alert?",
            verdict = "MONITOR",
            severity = "moderate",
            recommendedAction = "Monitor local advisories. Geometry unavailable.",
            actionWindow = ActionWindowDto(status = "unavailable", reason = "Cannot verify window"),
            confidence = "low",
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-UNK-005"))
                put("hazard_type", JsonPrimitive("Flash Flood Warning"))
                put("issuing_office", JsonPrimitive("NDMA_SACHET"))
                put("is_official", JsonPrimitive(true))
                put("exposure_state", JsonPrimitive("UNKNOWN"))
            }
        )

        val domain = dto.toDomain()

        assertNotNull(domain.alertImpact)
        assertEquals(com.weathergpt.domain.model.decision.ExposureState.UNKNOWN, domain.alertImpact?.affectedAreaStatus)
        assertEquals("UNAVAILABLE", domain.alertImpact?.exposureStatus)
        assertEquals("Affected area could not be verified", domain.alertImpact?.exposureSummary)
        assertFalse(domain.uncertainty.exposureDataAvailable)
    }

    @Test
    fun testAlertImpact_MandatoryProvenance_DynamicIssuingOffice() {
        // MANDATORY PROVENANCE TEST: issuing_office = "NDMA_SACHET", is_official = true
        val dto = NirnayCardDto(
            question = "Should I spray today?",
            verdict = "NO_GO",
            severity = "critical",
            recommendedAction = "Follow official safety guidance.",
            actionWindow = ActionWindowDto(status = "unavailable", reason = "Suppressed"),
            confidence = "high",
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-PROV-006"))
                put("issuing_office", JsonPrimitive("NDMA_SACHET"))
                put("is_official", JsonPrimitive(true))
                put("hazard_type", JsonPrimitive("Extremely Heavy Rain"))
                put("exposure_state", JsonPrimitive("INSIDE"))
            }
        )

        val domain = dto.toDomain()

        assertNotNull(domain.alertImpact)
        // Must preserve the EXACT backend authority without forcing or hardcoding
        assertEquals("NDMA_SACHET", domain.alertImpact?.issuingOffice)
        assertTrue(domain.alertImpact?.isOfficial ?: false)
    }

    @Test
    fun testAlertImpact_UnofficialAlert_FlagPreserved() {
        val dto = NirnayCardDto(
            question = "General weather query",
            verdict = "GO",
            severity = "low",
            recommendedAction = "Normal activities feasible.",
            actionWindow = ActionWindowDto(status = "available", reason = "Clear"),
            confidence = "high",
            evidence = kotlinx.serialization.json.buildJsonObject {
                put("primary_alert_id", JsonPrimitive("ALERT-COMM-007"))
                put("issuing_office", JsonPrimitive("CommercialWeatherFeed"))
                put("is_official", JsonPrimitive(false))
                put("hazard_type", JsonPrimitive("Light showers"))
                put("exposure_state", JsonPrimitive("INSIDE"))
            }
        )

        val domain = dto.toDomain()

        assertNotNull(domain.alertImpact)
        assertEquals("CommercialWeatherFeed", domain.alertImpact?.issuingOffice)
        assertFalse(domain.alertImpact?.isOfficial ?: true)
    }
}
