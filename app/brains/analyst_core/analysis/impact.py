"""Translation of physical weather conditions into sector-specific operational impacts."""

from typing import List
from app.brains.analyst_core.models.schemas import HazardType
from app.brains.analyst_core.models.analyst_result import SectorImpact
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint


class ImpactAnalyzer:
    """Translates meteorological conditions into domain and sector impacts.
    
    CRITICAL:
    - Distinguishes physical condition from potential impact.
    - verified_actual is False by default; never claims an impact actually occurred without field reports.
    """

    def assess_impacts(
        self,
        hazards: List[HazardType],
        observations: List[WeatherObservation],
        forecasts: List[ForecastPoint],
        requested_sector: str = None,
    ) -> List[SectorImpact]:
        """Maps detected meteorological hazards to potential sectoral impacts."""
        impacts: List[SectorImpact] = []

        # Track max values
        max_rain = 0.0
        max_temp = -999.0
        max_wind = 0.0
        min_vis = 999999.0

        for obs in observations:
            if obs.rainfall_mm is not None:
                max_rain = max(max_rain, obs.rainfall_mm)
            if obs.temperature_c is not None:
                max_temp = max(max_temp, obs.temperature_c)
            if obs.wind_speed_kmh is not None:
                max_wind = max(max_wind, obs.wind_speed_kmh)
            if obs.visibility_m is not None:
                min_vis = min(min_vis, obs.visibility_m)

        for fc in forecasts:
            if fc.rainfall_mm is not None:
                max_rain = max(max_rain, fc.rainfall_mm)
            if fc.temperature_c is not None:
                max_temp = max(max_temp, fc.temperature_c)
            if fc.wind_speed_kmh is not None:
                max_wind = max(max_wind, fc.wind_speed_kmh)

        # 1. Transportation Sector
        if max_rain >= 64.5:
            impacts.append(
                SectorImpact(
                    sector="transportation",
                    potential_impact="Waterlogging on arterial roads, reduced vehicular speeds, and potential rail track submergence in low-lying zones.",
                    severity="SEVERE" if max_rain >= 115.6 else "MODERATE",
                    verified_actual=False,
                )
            )
        elif max_rain >= 20.0:
            impacts.append(
                SectorImpact(
                    sector="transportation",
                    potential_impact="Slick road surfaces and localized urban traffic slowdowns.",
                    severity="LOW",
                    verified_actual=False,
                )
            )

        if min_vis < 1000.0:
            impacts.append(
                SectorImpact(
                    sector="transportation",
                    potential_impact="Flight delays/diversions under low-visibility procedures and road traffic speed restrictions.",
                    severity="SEVERE" if min_vis < 200.0 else "MODERATE",
                    verified_actual=False,
                )
            )

        if max_wind >= 62.0:
            impacts.append(
                SectorImpact(
                    sector="transportation",
                    potential_impact="High-profile vehicle instability on bridges/highways and ferry service suspensions.",
                    severity="SEVERE" if max_wind >= 89.0 else "MODERATE",
                    verified_actual=False,
                )
            )

        # 2. Infrastructure & Drainage
        if max_rain >= 64.5 or HazardType.FLOODING in hazards:
            impacts.append(
                SectorImpact(
                    sector="drainage_infrastructure",
                    potential_impact="Municipal stormwater drainage capacity exceedance and localized basement inundation.",
                    severity="SEVERE" if max_rain >= 115.6 else "MODERATE",
                    verified_actual=False,
                )
            )

        # 3. Energy & Utilities
        if max_temp >= 40.0:
            impacts.append(
                SectorImpact(
                    sector="energy",
                    potential_impact="Substantial cooling electrical load surge, transformer thermal stress, and elevated grid peak demand.",
                    severity="SEVERE" if max_temp >= 45.0 else "MODERATE",
                    verified_actual=False,
                )
            )

        if max_wind >= 62.0 or HazardType.THUNDERSTORM in hazards:
            impacts.append(
                SectorImpact(
                    sector="energy",
                    potential_impact="Overhead power distribution line snapping and feeder tripping due to falling branches.",
                    severity="MODERATE",
                    verified_actual=False,
                )
            )

        # 4. Public Safety & Outdoor Activities
        if max_temp >= 40.0:
            impacts.append(
                SectorImpact(
                    sector="outdoor_activities",
                    potential_impact="Elevated risk of heat exhaustion and heatstroke among outdoor personnel and festival attendees.",
                    severity="SEVERE" if max_temp >= 45.0 else "MODERATE",
                    verified_actual=False,
                )
            )

        if HazardType.LIGHTNING in hazards or HazardType.THUNDERSTORM in hazards:
            impacts.append(
                SectorImpact(
                    sector="public_safety",
                    potential_impact="Direct cloud-to-ground lightning hazard in open areas and structural hazard from sudden wind gusts.",
                    severity="SEVERE",
                    verified_actual=False,
                )
            )

        # Filter by requested sector if specified
        if requested_sector:
            matched = [i for i in impacts if requested_sector.lower() in i.sector.lower()]
            if matched:
                return matched

        return impacts
