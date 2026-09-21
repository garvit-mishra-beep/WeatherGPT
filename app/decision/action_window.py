"""Action Window Engine for Vayubodhak (USP Phase 2).

Provides deterministic forward-scanning of hourly forecast data to identify,
score, and rank contiguous operational action windows (e.g. chemical spraying).

Core Invariant: Zero LLM dependency, 100% deterministic Python mathematics,
strictly preserves WRF honesty (never fabricates unconfigured models).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.analytics.water_balance import (
    SPRAY_MAX_POST_RAIN_MM,
    SPRAY_MAX_RAIN_PROBABILITY_PCT,
    SPRAY_MAX_WIND_SPEED_KMH,
    evaluate_spray_window,
)
from app.decision.alert_impact import AlertImpactEngine
from app.decision.models import (
    ActionWindow,
    ActionWindowPeriod,
    CandidateHourEvaluation,
    ConfidenceLevel,
    EvidenceBundle,
    ExposureState,
)

logger = logging.getLogger(__name__)

# Default minimum continuous operational duration (hours) for field operations.
# For chemical spraying, 1 isolated hour is operationally insufficient for tank
# preparation, calibration, and travel across Indian cotton fields.
DEFAULT_MIN_SPRAY_WINDOW_HOURS: int = 2


class ActionWindowEngine:
    """Deterministic Operational Action Window Search and Ranking Engine."""

    def __init__(self, min_spray_window_hours: int = DEFAULT_MIN_SPRAY_WINDOW_HOURS) -> None:
        self.min_spray_window_hours = max(1, min_spray_window_hours)
        self.alert_impact_engine = AlertImpactEngine()

    def find_action_window(
        self,
        evidence: EvidenceBundle,
        action_type: str = "cotton_spray",
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionWindow:
        """Scan hourly forecast data to compute the optimal contiguous operational window."""
        ctx = context or {}
        crop_name = ctx.get("crop_name", "Cotton")
        min_hours = ctx.get("min_window_hours", self.min_spray_window_hours)

        hourly_records: List[Dict[str, Any]] = evidence.forecast.get("hourly", [])

        # 1. Evaluate Active Official Alerts for Spatial Exposure & Safety
        alert_evals, _ = self.alert_impact_engine.evaluate_alerts(
            alerts=evidence.alerts,
            location=evidence.location,
            query_time_iso=evidence.requested_time,
        )

        # Check for Active Red Alert inside location (Total Action Window Suppression)
        active_red_inside = next(
            (
                a for a in alert_evals
                if a.warning_level.upper() == "RED"
                and a.exposure_state == ExposureState.INSIDE
                and a.is_active
            ),
            None,
        )
        if active_red_inside:
            logger.info("ActionWindowEngine: Suppressing action window due to active official Red Alert.")
            return ActionWindow(
                status="unavailable",
                best_window=None,
                fallback_windows=[],
                score=None,
                constraints={
                    "max_wind_speed_kmh": SPRAY_MAX_WIND_SPEED_KMH,
                    "max_rain_probability_pct": SPRAY_MAX_RAIN_PROBABILITY_PCT,
                    "max_post_rain_mm": SPRAY_MAX_POST_RAIN_MM,
                    "min_window_hours": min_hours,
                    "active_official_alert": "Red",
                },
                confidence=ConfidenceLevel.HIGH,
                reason=(
                    f"Action windows are completely suppressed during active official Red Alert bulletins "
                    f"({active_red_inside.event_title or active_red_inside.hazard_type}). Emergency public safety directives "
                    f"override all field scheduling."
                ),
                evidence={
                    "alert_id": active_red_inside.alert_id,
                    "warning_level": active_red_inside.warning_level,
                    "hazard_type": active_red_inside.hazard_type,
                    "exposure_state": active_red_inside.exposure_state.value,
                    "composite_impact_score": active_red_inside.composite_impact_score,
                },
                hourly_evaluations=[],
            )

        # Active Orange alerts inside location will block hours until alert expiration
        active_orange_inside = [
            a for a in alert_evals
            if a.warning_level.upper() in ("ORANGE", "AMBER")
            and a.exposure_state == ExposureState.INSIDE
            and a.is_active
            and a.expires_time_iso
        ]
        
        # 2. Handle Missing / Incomplete Hourly Forecast
        if not hourly_records:
            logger.info("ActionWindowEngine: No hourly forecast records found in evidence bundle.")
            return ActionWindow(
                status="unavailable",
                best_window=None,
                fallback_windows=[],
                score=None,
                constraints={
                    "max_wind_speed_kmh": SPRAY_MAX_WIND_SPEED_KMH,
                    "max_rain_probability_pct": SPRAY_MAX_RAIN_PROBABILITY_PCT,
                    "max_post_rain_mm": SPRAY_MAX_POST_RAIN_MM,
                    "min_window_hours": min_hours,
                },
                confidence=ConfidenceLevel.LOW,
                reason="Hourly numerical forecast is unavailable; forward action window cannot be scanned.",
                evidence={
                    "wrf_regional_available": False,
                    "hourly_points_count": 0,
                },
                hourly_evaluations=[],
            )

        # 3. Evaluate Each Candidate Hour Deterministically
        candidate_evals: List[CandidateHourEvaluation] = []
        for h in hourly_records:
            time_iso = str(h.get("time_iso", ""))
            wind_kmh = float(h.get("wind_speed_kmh", 0.0))
            rain_prob = float(h.get("rain_probability_pct", 0.0))
            precip_mm = float(h.get("precipitation_mm", 0.0))
            temp_c = float(h.get("temperature_c")) if h.get("temperature_c") is not None else None

            # Evaluate against canonical agronomic and safety thresholds
            failed_reasons: List[str] = []

            # Check if hour is blocked by an active Orange alert
            for oa in active_orange_inside:
                if oa.expires_time_iso and time_iso <= oa.expires_time_iso:
                    failed_reasons.append(f"Official Orange Alert active until {oa.expires_time_iso} ({oa.hazard_type})")
                    break

            if wind_kmh > SPRAY_MAX_WIND_SPEED_KMH:
                failed_reasons.append(f"Wind ({wind_kmh:.1f} km/h > {SPRAY_MAX_WIND_SPEED_KMH:.1f} km/h drift limit)")
            if rain_prob > SPRAY_MAX_RAIN_PROBABILITY_PCT:
                failed_reasons.append(f"Rain probability ({rain_prob:.0f}% > {SPRAY_MAX_RAIN_PROBABILITY_PCT:.0f}%)")
            if precip_mm > SPRAY_MAX_POST_RAIN_MM:
                failed_reasons.append(f"Rain volume ({precip_mm:.1f} mm > {SPRAY_MAX_POST_RAIN_MM:.1f} mm washoff limit)")

            passed = len(failed_reasons) == 0
            candidate_evals.append(
                CandidateHourEvaluation(
                    time_iso=time_iso,
                    wind_speed_kmh=wind_kmh,
                    rain_probability_pct=rain_prob,
                    precipitation_mm=precip_mm,
                    temperature_c=temp_c,
                    passed=passed,
                    failed_reasons=failed_reasons,
                )
            )

        # 3. Group Contiguous Passing Hours into Candidate Windows
        raw_windows: List[List[CandidateHourEvaluation]] = []
        current_streak: List[CandidateHourEvaluation] = []

        for c in candidate_evals:
            if c.passed:
                current_streak.append(c)
            else:
                if len(current_streak) >= min_hours:
                    raw_windows.append(current_streak)
                current_streak = []

        # Flush final streak if valid
        if len(current_streak) >= min_hours:
            raw_windows.append(current_streak)

        # 4. Handle No Valid Windows Found
        if not raw_windows:
            wrf_info = evidence.model_information.get("wrf", {})
            wrf_avail = wrf_info.get("status") == "available"
            return ActionWindow(
                status="unavailable",
                best_window=None,
                fallback_windows=[],
                score=None,
                constraints={
                    "max_wind_speed_kmh": SPRAY_MAX_WIND_SPEED_KMH,
                    "max_rain_probability_pct": SPRAY_MAX_RAIN_PROBABILITY_PCT,
                    "max_post_rain_mm": SPRAY_MAX_POST_RAIN_MM,
                    "min_window_hours": min_hours,
                },
                confidence=ConfidenceLevel.HIGH,
                reason=(
                    f"No contiguous valid spray window of at least {min_hours} hours exists in the current forecast horizon. "
                    f"Persistent high winds or elevated rain probabilities prevent safe application."
                ),
                evidence={
                    "total_hours_evaluated": len(candidate_evals),
                    "valid_hours_count": sum(1 for c in candidate_evals if c.passed),
                    "min_window_hours": min_hours,
                    "wrf_regional_available": wrf_avail,
                },
                hourly_evaluations=candidate_evals,
            )

        # 5. Score and Rank Valid Candidate Windows
        scored_windows: List[ActionWindowPeriod] = []
        now_iso = evidence.requested_time

        for idx, win in enumerate(raw_windows):
            window_period = self._build_scored_period(
                window_id=f"win_{idx + 1:02d}",
                hours=win,
                query_time_iso=now_iso,
            )
            scored_windows.append(window_period)

        # Sort descending by score; break ties by earlier start time
        scored_windows.sort(key=lambda w: (w.score, -w.duration_hours), reverse=True)

        best_window = scored_windows[0].model_copy(update={"recommended": True})
        fallback_windows = scored_windows[1:4]  # Up to 3 alternatives

        # Check WRF status for honest uncertainty reporting
        wrf_info = evidence.model_information.get("wrf", {})
        wrf_avail = wrf_info.get("status") == "available"

        if active_orange_inside:
            summary_reason = (
                f"Safe operational window identified AFTER official Orange Alert expiration: {best_window.summary} "
                f"(Score: {best_window.score:.1f}/100, average wind: {best_window.avg_wind_speed_kmh:.1f} km/h, "
                f"peak rain chance: {best_window.max_rain_probability_pct:.0f}%)."
            )
        else:
            summary_reason = (
                f"Optimal chemical spray window identified for {crop_name}: {best_window.summary} "
                f"(Score: {best_window.score:.1f}/100, average wind: {best_window.avg_wind_speed_kmh:.1f} km/h, "
                f"peak rain chance: {best_window.max_rain_probability_pct:.0f}%)."
            )
        if not wrf_avail:
            summary_reason += " Guidance derived from GFS 0.25° NWP; independent regional WRF comparison is unconfigured."

        return ActionWindow(
            status="available",
            best_window=best_window,
            fallback_windows=fallback_windows,
            score=best_window.score,
            constraints={
                "max_wind_speed_kmh": SPRAY_MAX_WIND_SPEED_KMH,
                "max_rain_probability_pct": SPRAY_MAX_RAIN_PROBABILITY_PCT,
                "max_post_rain_mm": SPRAY_MAX_POST_RAIN_MM,
                "min_window_hours": min_hours,
            },
            confidence=ConfidenceLevel.HIGH if len(candidate_evals) >= 24 else ConfidenceLevel.MEDIUM,
            reason=summary_reason,
            evidence={
                "best_window_score": best_window.score,
                "best_window_start": best_window.start_time_iso,
                "best_window_end": best_window.end_time_iso,
                "best_window_duration_hours": best_window.duration_hours,
                "avg_wind_speed_kmh": best_window.avg_wind_speed_kmh,
                "max_wind_speed_kmh": best_window.max_wind_speed_kmh,
                "max_rain_probability_pct": best_window.max_rain_probability_pct,
                "total_rainfall_mm": best_window.total_rainfall_mm,
                "total_candidate_hours_evaluated": len(candidate_evals),
                "valid_hours_count": sum(1 for c in candidate_evals if c.passed),
                "total_valid_windows_found": len(scored_windows),
                "wrf_regional_available": wrf_avail,
            },
            hourly_evaluations=candidate_evals,
        )

    def _build_scored_period(
        self,
        window_id: str,
        hours: List[CandidateHourEvaluation],
        query_time_iso: str,
    ) -> ActionWindowPeriod:
        """Calculate aggregate physical properties and deterministic multi-criteria score."""
        start_iso = hours[0].time_iso
        # The end boundary is the end of the last passing hour (1 hour past start of last hour)
        last_hour_dt = self._parse_iso(hours[-1].time_iso)
        end_dt = last_hour_dt + timedelta(hours=1) if last_hour_dt else None
        end_iso = end_dt.isoformat() if end_dt else hours[-1].time_iso

        duration = len(hours)
        wind_speeds = [h.wind_speed_kmh for h in hours]
        rain_probs = [h.rain_probability_pct for h in hours]
        rains = [h.precipitation_mm for h in hours]

        avg_wind = sum(wind_speeds) / duration if duration > 0 else 0.0
        max_wind = max(wind_speeds) if wind_speeds else 0.0
        max_rain_prob = max(rain_probs) if rain_probs else 0.0
        total_rain = sum(rains)

        # -------------------------------------------------------------
        # Deterministic Multi-Criteria Score Calculation S in [0.0, 100.0]
        # 1. Wind Calmness Score (40 pts): lower wind reduces drift
        # 2. Rain Probability Safety Score (30 pts): lower rain chance
        # 3. Operational Duration Score (20 pts): longer continuous window
        # 4. Proximity Score (10 pts): sooner window is prioritized for pests
        # -------------------------------------------------------------
        s_wind = 40.0 * max(0.0, (SPRAY_MAX_WIND_SPEED_KMH - avg_wind) / SPRAY_MAX_WIND_SPEED_KMH)
        s_rain = 30.0 * max(0.0, (SPRAY_MAX_RAIN_PROBABILITY_PCT - max_rain_prob) / SPRAY_MAX_RAIN_PROBABILITY_PCT)
        s_duration = min(20.0, duration * 5.0)

        # Lead time calculation
        lead_hours = 0.0
        q_dt = self._parse_iso(query_time_iso)
        s_dt = self._parse_iso(start_iso)
        if q_dt and s_dt:
            delta = (s_dt - q_dt).total_seconds() / 3600.0
            lead_hours = max(0.0, delta)

        s_proximity = max(0.0, 10.0 - (0.2 * lead_hours))
        total_score = round(s_wind + s_rain + s_duration + s_proximity, 2)

        # Format human-readable summary
        summary = self._format_window_summary(s_dt, end_dt, duration)

        return ActionWindowPeriod(
            window_id=window_id,
            start_time_iso=start_iso,
            end_time_iso=end_iso,
            duration_hours=duration,
            score=total_score,
            avg_wind_speed_kmh=round(avg_wind, 1),
            max_wind_speed_kmh=round(max_wind, 1),
            max_rain_probability_pct=round(max_rain_prob, 1),
            total_rainfall_mm=round(total_rain, 1),
            summary=summary,
            recommended=False,
        )

    def _parse_iso(self, iso_str: str) -> Optional[datetime]:
        """Safely parse ISO timestamp."""
        if not iso_str:
            return None
        try:
            # Handle trailing 'Z' or offset
            cleaned = iso_str.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except Exception:
            return None

    def _format_window_summary(
        self,
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
        duration: int,
    ) -> str:
        """Create human-readable operational window string (e.g. 'Tomorrow 06:00 - 09:00 IST (3h)')."""
        if not start_dt or not end_dt:
            return f"Upcoming Window ({duration} hours)"
        start_fmt = start_dt.strftime("%d %b %H:%M")
        end_fmt = end_dt.strftime("%H:%M")
        return f"{start_fmt} - {end_fmt} ({duration}h continuous)"
