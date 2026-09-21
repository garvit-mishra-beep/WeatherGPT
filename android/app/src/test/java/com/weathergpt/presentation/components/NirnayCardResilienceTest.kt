package com.weathergpt.presentation.components

import com.weathergpt.domain.model.decision.ActionWindow
import com.weathergpt.domain.model.decision.DecisionConfidence
import com.weathergpt.domain.model.decision.DecisionSeverity
import com.weathergpt.domain.model.decision.DecisionUncertainty
import com.weathergpt.domain.model.decision.DecisionVerdict
import com.weathergpt.domain.model.decision.NirnayCard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit test verifying NirnayCard evidence freshness and data status attributes.
 * (Section 17 of Master Prompt).
 */
class NirnayCardResilienceTest {

    private fun createCard(
        sourceStatus: String = "LIVE",
        lastVerifiedAt: String? = "10:41 AM"
    ): NirnayCard {
        return NirnayCard(
            question = "Can fertilizer be safely sprayed in Pune today?",
            verdict = DecisionVerdict.GO,
            severity = DecisionSeverity.LOW,
            recommendedAction = "Favorable weather window available.",
            actionWindow = ActionWindow(
                status = "available",
                isAvailable = true,
                bestWindow = null,
                fallbackWindows = emptyList(),
                score = 88.0,
                constraints = emptyMap(),
                confidence = DecisionConfidence.HIGH,
                reason = "Dry calm conditions",
                hourlyEvaluations = null
            ),
            confidence = DecisionConfidence.HIGH,
            uncertainty = DecisionUncertainty(
                gfsConfidence = "HIGH",
                wrfStatus = "CONVERGENT",
                uncertaintyNote = "High confidence across deterministic NWP ensemble.",
                leadTimeHours = 6.0
            ),
            why = listOf("Low wind speed", "No precipitation forecast"),
            primaryRisk = "None",
            lossPotential = "Minimal",
            alternatives = emptyList(),
            evidenceMetrics = mapOf("precipitation_mm" to "0.0", "wind_speed_kmh" to "8.0"),
            ledger = null,
            sourceStatus = sourceStatus,
            lastVerifiedAt = lastVerifiedAt
        )
    }

    @Test
    fun test_nirnayCard_liveEvidenceState() {
        val card = createCard(sourceStatus = "LIVE", lastVerifiedAt = "10:41 AM")
        assertEquals("LIVE", card.sourceStatus)
        assertEquals("10:41 AM", card.lastVerifiedAt)
        assertTrue(card.sourceStatus.equals("LIVE", ignoreCase = true))
    }

    @Test
    fun test_nirnayCard_staleEvidenceState() {
        val card = createCard(sourceStatus = "STALE", lastVerifiedAt = "10:32 AM")
        assertEquals("STALE", card.sourceStatus)
        assertEquals("10:32 AM", card.lastVerifiedAt)
        assertFalse(card.sourceStatus.equals("LIVE", ignoreCase = true))
    }

    @Test
    fun test_nirnayCard_fallbackEvidenceState() {
        val card = createCard(sourceStatus = "FALLBACK", lastVerifiedAt = "11:00 AM")
        assertEquals("FALLBACK", card.sourceStatus)
        assertNotNull(card.lastVerifiedAt)
        assertFalse(card.sourceStatus.equals("LIVE", ignoreCase = true))
    }

    @Test
    fun test_nirnayCard_cachedEvidenceState() {
        val card = createCard(sourceStatus = "CACHED", lastVerifiedAt = "09:15 AM")
        assertEquals("CACHED", card.sourceStatus)
        assertFalse(card.sourceStatus.equals("LIVE", ignoreCase = true))
    }
}
