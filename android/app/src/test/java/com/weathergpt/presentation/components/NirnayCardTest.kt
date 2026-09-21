package com.weathergpt.presentation.components

import com.weathergpt.domain.model.decision.ActionWindow
import com.weathergpt.domain.model.decision.ActionWindowPeriod
import com.weathergpt.domain.model.decision.CandidateHourEvaluation
import com.weathergpt.domain.model.decision.DecisionConfidence
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionUncertainty
import com.weathergpt.domain.model.decision.DecisionVerdict
import com.weathergpt.domain.model.decision.EvidenceLedger
import com.weathergpt.domain.model.decision.LedgerRuleEvaluation
import com.weathergpt.domain.model.decision.NirnayCard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NirnayCardTest {

    @Test
    fun testNirnayCard_GoVerdictModelCreation() {
        val card = NirnayCard(
            question = "Should I spray my cotton today?",
            verdict = DecisionVerdict.GO,
            severity = DecisionSeverity.LOW,
            recommendedAction = "Conditions are optimal for chemical application.",
            actionWindow = ActionWindow(
                status = "available",
                isAvailable = true,
                bestWindow = ActionWindowPeriod(
                    windowId = "win_current",
                    startTimeIso = "2026-09-07T08:00:00+05:30",
                    endTimeIso = "2026-09-07T12:00:00+05:30",
                    durationHours = 4,
                    score = 92.5,
                    avgWindSpeedKmh = 6.2,
                    maxWindSpeedKmh = 8.0,
                    maxRainProbabilityPct = 5.0,
                    totalRainfallMm = 0.0,
                    summary = "Today 08:00 - 12:00 IST",
                    recommended = true
                ),
                fallbackWindows = emptyList(),
                score = 92.5,
                constraints = mapOf("max_wind" to "15.0 km/h"),
                confidence = DecisionConfidence.HIGH,
                reason = "All spray constraints satisfied.",
                hourlyEvaluations = null
            ),
            confidence = DecisionConfidence.HIGH,
            uncertainty = DecisionUncertainty(
                gfsConfidence = "high",
                wrfStatus = "unavailable",
                uncertaintyNote = "Guidance based on GFS numerical forecast; independent WRF comparison is unavailable",
                leadTimeHours = 4.0
            ),
            why = listOf("Wind speed (6.2 km/h) is well below 15.0 km/h threshold"),
            primaryRisk = "Minimal drift risk",
            lossPotential = "Low",
            alternatives = listOf("Proceed with nozzle calibration and standard PPE"),
            evidenceMetrics = mapOf("wind_speed" to "6.2 km/h"),
            ledger = null
        )

        assertEquals(DecisionVerdict.GO, card.verdict)
        assertEquals(DecisionSeverity.LOW, card.severity)
        assertTrue(card.actionWindow.isAvailable)
        assertEquals(92.5, card.actionWindow.bestWindow?.score ?: 0.0, 0.01)
        assertEquals("Today 08:00 - 12:00 IST", card.actionWindow.bestWindow?.summary)
    }

    @Test
    fun testNirnayCard_PostponeWithFallbackWindows() {
        val fallback1 = ActionWindowPeriod(
            windowId = "win_01",
            startTimeIso = "2026-09-08T06:00:00+05:30",
            endTimeIso = "2026-09-08T09:00:00+05:30",
            durationHours = 3,
            score = 65.0,
            avgWindSpeedKmh = 8.5,
            maxWindSpeedKmh = 10.0,
            maxRainProbabilityPct = 10.0,
            totalRainfallMm = 0.0,
            summary = "Tomorrow 06:00 - 09:00 IST",
            recommended = true
        )

        val fallback2 = ActionWindowPeriod(
            windowId = "win_02",
            startTimeIso = "2026-09-08T16:00:00+05:30",
            endTimeIso = "2026-09-08T18:00:00+05:30",
            durationHours = 2,
            score = 58.0,
            avgWindSpeedKmh = 11.0,
            maxWindSpeedKmh = 13.0,
            maxRainProbabilityPct = 15.0,
            totalRainfallMm = 0.0,
            summary = "Tomorrow 16:00 - 18:00 IST",
            recommended = false
        )

        val card = NirnayCard(
            question = "Should I spray my cotton tonight?",
            verdict = DecisionVerdict.POSTPONE,
            severity = DecisionSeverity.HIGH,
            recommendedAction = "Do not spray tonight. Wait for favorable weather window.",
            actionWindow = ActionWindow(
                status = "available",
                isAvailable = true,
                bestWindow = fallback1,
                fallbackWindows = listOf(fallback2),
                score = 65.0,
                constraints = mapOf("max_wind" to "15.0 km/h"),
                confidence = DecisionConfidence.HIGH,
                reason = "Favorable 3-hour window identified tomorrow morning.",
                hourlyEvaluations = listOf(
                    CandidateHourEvaluation(
                        timeIso = "2026-09-08T06:00:00+05:30",
                        windSpeedKmh = 8.0,
                        rainProbabilityPct = 10.0,
                        precipitationMm = 0.0,
                        temperatureC = 26.0,
                        passed = true,
                        failedReasons = emptyList()
                    )
                )
            ),
            confidence = DecisionConfidence.HIGH,
            uncertainty = DecisionUncertainty(
                gfsConfidence = "high",
                wrfStatus = "unavailable",
                uncertaintyNote = "Guidance based on GFS numerical forecast; independent WRF comparison is unavailable",
                leadTimeHours = 12.0
            ),
            why = listOf("Tonight's wind 18.0 km/h exceeds 15.0 km/h drift limit"),
            primaryRisk = "High chemical drift hazard",
            lossPotential = "High",
            alternatives = listOf("Spray tomorrow morning between 06:00 and 09:00 IST"),
            evidenceMetrics = mapOf("wind_speed_kmh" to "18.0"),
            ledger = EvidenceLedger(
                decisionId = "dec_postpone_1",
                timestamp = "2026-09-07T21:00:00Z",
                question = "Should I spray my cotton tonight?",
                rules = listOf(
                    LedgerRuleEvaluation(
                        ruleName = "wind_drift_threshold",
                        threshold = "15.0",
                        observedValue = "18.0",
                        unit = "km/h",
                        operator = "<=",
                        satisfied = false,
                        rationale = "Wind exceeds 15.0 km/h"
                    )
                ),
                inputs = mapOf("wind_speed" to "18.0"),
                sources = listOf("GFS 0.25° NWP")
            )
        )

        assertEquals(DecisionVerdict.POSTPONE, card.verdict)
        assertEquals(1, card.actionWindow.fallbackWindows.size)
        assertEquals("win_02", card.actionWindow.fallbackWindows.first().windowId)
        assertNotNull(card.ledger)
        assertFalse(card.ledger!!.rules.first().satisfied)
    }

    @Test
    fun testNirnayCard_UnavailableWindowHonesty() {
        val card = NirnayCard(
            question = "Should I spray my cotton tonight?",
            verdict = DecisionVerdict.NO_GO,
            severity = DecisionSeverity.CRITICAL,
            recommendedAction = "Do not spray. Active severe storm warning.",
            actionWindow = ActionWindow(
                status = "unavailable",
                isAvailable = false,
                bestWindow = null,
                fallbackWindows = emptyList(),
                score = null,
                constraints = emptyMap(),
                confidence = DecisionConfidence.HIGH,
                reason = "No valid operational window found across forecast horizon.",
                hourlyEvaluations = emptyList()
            ),
            confidence = DecisionConfidence.HIGH,
            uncertainty = DecisionUncertainty(
                gfsConfidence = "high",
                wrfStatus = "unavailable",
                uncertaintyNote = "Guidance based on GFS numerical forecast; independent WRF comparison is unavailable",
                leadTimeHours = 48.0
            ),
            why = listOf("Severe rain squalls persist"),
            primaryRisk = "Complete chemical wash-off",
            lossPotential = "Critical",
            alternatives = listOf("Monitor IMD bulletins"),
            evidenceMetrics = emptyMap(),
            ledger = null
        )

        assertFalse(card.actionWindow.isAvailable)
        assertEquals("unavailable", card.actionWindow.status)
        assertEquals(DecisionVerdict.NO_GO, card.verdict)
        assertEquals(DecisionSeverity.CRITICAL, card.severity)
        assertTrue(card.actionWindow.reason.contains("No valid operational window"))
    }
}
