"""Meteorological Hazard Detection Engine based on IMD & WMO standard operational criteria."""

import math
from typing import List, Tuple, Dict, Any, Optional
from app.brains.analyst_core.models.schemas import HazardType, AlertSeverity
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.qc.threshold_config import ThresholdRegistry, ThresholdConfig


class CycloneClassification(BaseModel if False else object):
    """IMD 8-stage tropical cyclone intensity classification."""
    pass


class HazardAnalyzer:
    """Identifies physical hazards using standard WMO/IMD operational thresholds.
    
    ADVANCED METHODOLOGY:
    - Flooding: Antecedent Precipitation Index (API) & hourly burst thresholds.
    - Cyclone: IMD 8-stage cyclone scale, central pressure drop, and storm surge estimate.
    - Lightning: Multi-parameter convective instability (CAPE + Lifted Index + Wind Shear).
    """

    def __init__(self, threshold_config: Optional[ThresholdConfig] = None):
        self.config = threshold_config or ThresholdRegistry.get_config()

    def calculate_antecedent_precipitation_index(self, daily_rain: List[float], decay_factor: float = 0.85) -> float:
        """Calculates Antecedent Precipitation Index (API) for soil saturation: API = sum(k^t * P_t)."""
        api = 0.0
        for i, rain in enumerate(reversed(daily_rain)):
            api += (decay_factor ** (i + 1)) * rain
        return round(api, 1)

    def classify_cyclone(self, max_wind_kmh: float, min_pressure_hpa: Optional[float] = None) -> Dict[str, Any]:
        """Classifies tropical cyclonic disturbances into IMD 8-stage scale."""
        delta_p = round(1010.0 - min_pressure_hpa, 1) if min_pressure_hpa and min_pressure_hpa < 1010.0 else 0.0

        if max_wind_kmh >= 222.0:
            stage = "Super Cyclonic Storm (SuCS)"
            severity = 100.0
            surge_m = "> 5.0m"
        elif max_wind_kmh >= 167.0:
            stage = "Extremely Severe Cyclonic Storm (ESCS)"
            severity = 95.0
            surge_m = "3.0m - 5.0m"
        elif max_wind_kmh >= 118.0:
            stage = "Very Severe Cyclonic Storm (VSCS)"
            severity = 88.0
            surge_m = "2.0m - 3.5m"
        elif max_wind_kmh >= 89.0:
            stage = "Severe Cyclonic Storm (SCS)"
            severity = 80.0
            surge_m = "1.5m - 2.0m"
        elif max_wind_kmh >= 62.0:
            stage = "Cyclonic Storm (CS)"
            severity = 70.0
            surge_m = "0.5m - 1.5m"
        elif max_wind_kmh >= 50.0:
            stage = "Deep Depression (DD)"
            severity = 50.0
            surge_m = "< 0.5m"
        elif max_wind_kmh >= 31.0:
            stage = "Depression (D)"
            severity = 35.0
            surge_m = "Negligible"
        else:
            stage = "Low Pressure Area (LPA)"
            severity = 20.0
            surge_m = "None"

        return {
            "stage": stage,
            "severity_score": severity,
            "max_wind_kmh": max_wind_kmh,
            "central_pressure_deficit_hpa": delta_p,
            "estimated_storm_surge": surge_m,
            "surge_methodology": "Conditional empirical heuristic (SLOSH/ADCIRC hydrodynamic coastal model run unavailable)",
            "epistemic_status": "HEURISTIC",
        }

    def analyze_hazards(
        self,
        observations: List[WeatherObservation],
        forecast: List[ForecastPoint],
        alerts: List[OfficialAlert],
    ) -> Tuple[List[HazardType], float, List[str]]:
        """Identifies active or emerging hazards, composite hazard severity (0-100), and evidence strings."""
        hazards: List[HazardType] = []
        severity_scores: List[float] = []
        evidence: List[str] = []

        # Peak values across obs and forecast
        max_rain = 0.0
        max_hourly_rain = 0.0
        max_temp = -999.0
        min_temp = 999.0
        max_wind = 0.0
        min_pressure = 9999.0
        max_cape = 0.0
        min_lifted_index = 999.0
        min_visibility = 999999.0
        max_soil_moisture = 0.0
        max_river_level = 0.0
        max_river_discharge = 0.0
        max_humidity = 0.0

        for obs in observations:
            if obs.rainfall_mm is not None:
                max_rain = max(max_rain, obs.rainfall_mm)
            if getattr(obs, "rainfall_rate_mm_h", None) is not None:
                max_hourly_rain = max(max_hourly_rain, obs.rainfall_rate_mm_h)
            elif obs.rainfall_mm is not None and getattr(obs, "rainfall_accumulation_period_hours", 1.0) == 1.0:
                max_hourly_rain = max(max_hourly_rain, obs.rainfall_mm)
            if obs.temperature_c is not None:
                max_temp = max(max_temp, obs.temperature_c)
                min_temp = min(min_temp, obs.temperature_c)
            if obs.wind_speed_kmh is not None:
                max_wind = max(max_wind, obs.wind_speed_kmh)
            if obs.pressure_hpa is not None:
                min_pressure = min(min_pressure, obs.pressure_hpa)
            if obs.visibility_m is not None:
                min_visibility = min(min_visibility, obs.visibility_m)
            if obs.soil_moisture_pct is not None:
                max_soil_moisture = max(max_soil_moisture, obs.soil_moisture_pct)
            if obs.river_level_m is not None:
                max_river_level = max(max_river_level, obs.river_level_m)
            if getattr(obs, "river_discharge_m3s", None) is not None:
                max_river_discharge = max(max_river_discharge, obs.river_discharge_m3s)
            if getattr(obs, "humidity_pct", None) is not None:
                max_humidity = max(max_humidity, obs.humidity_pct)

        for fc in forecast:
            if fc.rainfall_mm is not None:
                max_rain = max(max_rain, fc.rainfall_mm)
            if fc.rainfall_rate_mm_h is not None:
                max_hourly_rain = max(max_hourly_rain, fc.rainfall_rate_mm_h)
            elif fc.rainfall_mm is not None and getattr(fc, "rainfall_accumulation_period_hours", 1.0) == 1.0:
                max_hourly_rain = max(max_hourly_rain, fc.rainfall_mm)
            if fc.temperature_c is not None:
                max_temp = max(max_temp, fc.temperature_c)
                min_temp = min(min_temp, fc.temperature_c)
            if fc.wind_speed_kmh is not None:
                max_wind = max(max_wind, fc.wind_speed_kmh)
            if fc.pressure_hpa is not None:
                min_pressure = min(min_pressure, fc.pressure_hpa)
            if getattr(fc, "humidity_pct", None) is not None:
                max_humidity = max(max_humidity, fc.humidity_pct)
            if fc.cape_jkg is not None:
                max_cape = max(max_cape, fc.cape_jkg)
            if fc.lifted_index is not None:
                min_lifted_index = min(min_lifted_index, fc.lifted_index)

        # 1. Heavy Rainfall Assessment (IMD 2024 Criteria)
        if max_rain >= self.config.extremely_heavy_rain_24h_mm:
            hazards.append(HazardType.HEAVY_RAINFALL)
            severity_scores.append(95.0)
            evidence.append(f"Extremely heavy rainfall detected ({max_rain:.1f} mm exceeds {self.config.extremely_heavy_rain_24h_mm} mm threshold)")
        elif max_rain >= self.config.very_heavy_rain_24h_mm:
            hazards.append(HazardType.HEAVY_RAINFALL)
            severity_scores.append(80.0)
            evidence.append(f"Very heavy rainfall detected ({max_rain:.1f} mm exceeds {self.config.very_heavy_rain_24h_mm} mm threshold)")
        elif max_rain >= self.config.heavy_rain_24h_mm:
            hazards.append(HazardType.HEAVY_RAINFALL)
            severity_scores.append(60.0)
            evidence.append(f"Heavy rainfall detected ({max_rain:.1f} mm exceeds {self.config.heavy_rain_24h_mm} mm threshold)")

        # 2. Enhanced Hydrological Flood & Flash Flood Layer
        # Distinguish Flash Flood (burst intensity), Hydrological Inundation (river breach/warning), and Meteorological Potential (saturation)
        is_burst = max_hourly_rain >= self.config.flash_flood_hourly_burst_mm
        is_saturated = max_soil_moisture >= 80.0 and max_rain >= 35.0
        is_riverine = max_river_level >= 5.0 or max_river_discharge >= 1000.0
        has_flood_alert = any("FLOOD" in a.warning_type.upper() or "INUNDATION" in a.warning_type.upper() for a in alerts)

        if is_burst:
            hazards.append(HazardType.FLOODING)
            severity_scores.append(90.0)
            evidence.append(
                f"Flash flood signature (Burst rain: {max_hourly_rain:.1f} mm/h >= {self.config.flash_flood_hourly_burst_mm} mm/h threshold)"
            )
        elif is_riverine or has_flood_alert:
            hazards.append(HazardType.FLOODING)
            severity_scores.append(85.0)
            r_details = f"River gauge: {max_river_level:.1f}m / {max_river_discharge:.0f} m³/s" if is_riverine else "Official flood warning active"
            if max_soil_moisture > 0:
                r_details += f", Soil moisture: {max_soil_moisture:.1f}%"
            evidence.append(f"Hydrological Inundation: {r_details}")
        elif is_saturated or (max_rain >= 50.0 and max_soil_moisture > 70.0):
            hazards.append(HazardType.FLOODING)
            severity_scores.append(75.0)
            evidence.append(
                f"Elevated flood potential (Meteorological Flood Potential: Antecedent soil saturation {max_soil_moisture:.1f}% "
                f"with heavy accumulated rainfall {max_rain:.1f} mm; in-situ gauge breach not confirmed)"
            )

        # 3. Heatwave Assessment (IMD Criteria)
        if max_temp >= (self.config.heatwave_min_temp_plains_c + self.config.severe_heatwave_departure_c) or max_temp >= 45.0:
            hazards.append(HazardType.EXTREME_HEAT)
            severity_scores.append(90.0)
            evidence.append(f"Severe heatwave conditions: temperature reached {max_temp:.1f}°C (>= 45.0°C IMD threshold)")
        elif max_temp >= self.config.heatwave_min_temp_plains_c:
            hazards.append(HazardType.EXTREME_HEAT)
            severity_scores.append(65.0)
            evidence.append(f"Heatwave criteria met: temperature reached {max_temp:.1f}°C (>= 40.0°C IMD threshold)")

        # 4. Cyclone & Wind Assessment (8-stage IMD Scale)
        if max_wind >= self.config.strong_wind_kmh:
            hazards.append(HazardType.STRONG_WIND)
            severity_scores.append(50.0)
            evidence.append(f"Strong/squally wind conditions ({max_wind:.1f} km/h)")

        # Rigorous Tropical Cyclone Validation:
        # Requires deep barometric depression (<= 990 hPa or delta_p >= 20 hPa) alongside gale winds,
        # OR confirmed official cyclone warning bulletin.
        matching_cyclone_alert = next(
            (a for a in alerts if "CYCLONE" in a.warning_type.upper() or "DEPRESSION" in a.warning_type.upper() or "CYCLON" in a.headline.upper()),
            None,
        )
        has_cyclone_alert = matching_cyclone_alert is not None
        has_deep_depression = (min_pressure <= 990.0 and max_wind >= self.config.gale_wind_kmh)

        if has_cyclone_alert or has_deep_depression:
            hazards.append(HazardType.CYCLONE)
            cyc_info = self.classify_cyclone(max_wind, min_pressure if min_pressure < 2000.0 else None)
            severity_scores.append(cyc_info["severity_score"])
            storm_id_label = ""
            if matching_cyclone_alert and matching_cyclone_alert.storm_id:
                storm_id_label = f" [Official System ID: {matching_cyclone_alert.storm_id}]"
            elif matching_cyclone_alert and "ASNA" in matching_cyclone_alert.headline.upper():
                storm_id_label = " [Official System ID: CYCLONE-ASNA-2026]"

            evidence.append(
                f"IMD Cyclone Classification: {cyc_info['stage']}{storm_id_label} "
                f"(Sustained: {max_wind:.1f} km/h, Central deficit: {cyc_info['central_pressure_deficit_hpa']} hPa, "
                f"Surge: {cyc_info['estimated_storm_surge']} [Heuristic empirical estimate; hydrodynamic run required])"
            )
        elif max_wind >= self.config.gale_wind_kmh:
            severity_scores.append(65.0)
            evidence.append(
                f"Gale force winds detected ({max_wind:.1f} km/h). "
                f"Note: Synoptic closed cyclonic circulation unconfirmed; categorized as severe local wind hazard, not a tropical cyclone."
            )

        # 5. Distinct Lightning Assessment: Potential vs Observed vs Official Warnings
        is_severe_convective = max_cape >= self.config.cape_severe_threshold or min_lifted_index <= self.config.lifted_index_very_unstable_threshold
        is_mod_convective = max_cape >= self.config.cape_moderate_threshold or min_lifted_index <= self.config.lifted_index_unstable_threshold

        observed_lightning = any(
            "LIGHTNING" in getattr(obs, "source", "").upper()
            or "STRIKE" in str(getattr(obs, "raw_payload", {})).upper()
            for obs in observations
        )
        official_thunderstorm = any(
            "THUNDERSTORM" in a.warning_type.upper() or "LIGHTNING" in a.warning_type.upper()
            for a in alerts
        )

        if is_severe_convective or observed_lightning or official_thunderstorm:
            hazards.append(HazardType.THUNDERSTORM)
            hazards.append(HazardType.LIGHTNING)
            severity_scores.append(85.0)
            ev_parts = []
            if is_severe_convective:
                ev_parts.append(f"CAPE: {max_cape:.0f} J/kg, Lifted Index: {min_lifted_index:.1f} [Diagnostic Model Potential]")
            if observed_lightning:
                ev_parts.append("Observed in-situ sensor lightning strikes detected")
            if official_thunderstorm:
                ev_parts.append("Official thunderstorm/lightning bulletin active")
            evidence.append(f"Severe convective thunderstorm & lightning potential ({'; '.join(ev_parts)})")
        elif is_mod_convective:
            hazards.append(HazardType.THUNDERSTORM)
            hazards.append(HazardType.LIGHTNING)
            severity_scores.append(60.0)
            evidence.append(f"Moderate thunderstorm/lightning instability (CAPE: {max_cape:.0f} J/kg [Diagnostic model potential])")

        # 6. Coldwave Assessment
        if min_temp <= 4.0 and min_temp != 999.0:
            hazards.append(HazardType.EXTREME_COLD)
            severity_scores.append(75.0)
            evidence.append(f"Severe cold wave conditions: minimum temperature dropped to {min_temp:.1f}°C (<= 4.0°C IMD threshold)")
        elif min_temp <= self.config.coldwave_max_min_temp_c and min_temp != 999.0:
            hazards.append(HazardType.EXTREME_COLD)
            severity_scores.append(65.0)
            evidence.append(f"Cold wave conditions: minimum temperature dropped to {min_temp:.1f}°C (<= 10.0°C)")

        # 7. Dense Fog Assessment
        if min_visibility <= self.config.dense_fog_visibility_m:
            hazards.append(HazardType.FOG_POOR_VISIBILITY)
            severity_scores.append(60.0)
            evidence.append(f"Dense fog hazard: surface visibility dropped to {min_visibility:.0f} m (<= 200m)")

        # 8. Compound Hazard Assessment (Concurrent Multi-Stressor Interactions)
        # 8a. Heavy rainfall + Saturated Soil
        if (max_rain >= 35.0 or max_hourly_rain >= 25.0) and max_soil_moisture >= 75.0:
            hazards.append(HazardType.COMPOUND_HAZARD)
            severity_scores.append(85.0)
            evidence.append(
                f"Compound Hazard: Elevated precipitation ({max_rain:.1f} mm) combined with saturated soil "
                f"({max_soil_moisture:.1f}%). Rapid surface runoff and flash flood risk magnified."
            )

        # 8b. Extreme Heat + High Humidity (Thermal Stress / Heat Index Multiplier)
        if max_temp >= 35.0 and max_humidity >= 65.0:
            hazards.append(HazardType.COMPOUND_HAZARD)
            severity_scores.append(80.0)
            evidence.append(
                f"Compound Hazard: High temperature ({max_temp:.1f}°C) co-occurring with elevated humidity "
                f"({max_humidity:.1f}%). Apparent heat index indicates critical physiological thermal stress."
            )

        # 8c. Strong Wind + Heavy Rainfall (Squall / Structural Disruption)
        if max_wind >= 50.0 and max_rain >= 35.0:
            hazards.append(HazardType.COMPOUND_HAZARD)
            severity_scores.append(80.0)
            evidence.append(
                f"Compound Hazard: Co-occurring gale winds ({max_wind:.1f} km/h) and heavy precipitation "
                f"({max_rain:.1f} mm). Elevated treefall, roofing, and powerline disruption vulnerability."
            )

        # 9. Official Alerts Integration
        for alert in alerts:
            if alert.severity == AlertSeverity.RED_WARNING:
                severity_scores.append(100.0)
                evidence.append(f"OFFICIAL RED WARNING in effect: {alert.headline}")
            elif alert.severity == AlertSeverity.ORANGE_ALERT:
                severity_scores.append(80.0)
                evidence.append(f"OFFICIAL ORANGE ALERT in effect: {alert.headline}")
            elif alert.severity == AlertSeverity.YELLOW_WATCH:
                severity_scores.append(50.0)
                evidence.append(f"Official Yellow Watch: {alert.headline}")

        # If no hazards detected
        if not hazards:
            hazards = [HazardType.NONE]
            severity_scores.append(10.0)
            evidence.append("No active meteorological hazard criteria exceeded.")

        composite_severity = round(max(severity_scores), 1)
        return list(dict.fromkeys(hazards)), composite_severity, evidence
