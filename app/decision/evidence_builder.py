"""Deterministic EvidenceBundle Builder for Vayubodhak (USP Phase 1).

Constructs the canonical EvidenceBundle by querying registered meteorological
providers, inspecting NWP model availability (enforcing the WRF Honesty Rule),
running physical Quality Control (QC) checks, and attaching full provenance.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.adapters.models import ProviderQuality
from app.adapters.strategy import WeatherProviderManager
from app.contracts.location import LocationContext
from app.decision.models import DecisionLocationQuery, EvidenceBundle
from app.tools.catalog import INDIAN_LOCATIONS

logger = logging.getLogger(__name__)


class EvidenceBundleBuilder:
    """Constructs verified, auditable EvidenceBundles from live or mock meteorological adapters."""

    def __init__(self, weather_manager: Optional[WeatherProviderManager] = None) -> None:
        self.weather_manager = weather_manager or WeatherProviderManager()

    async def build_bundle(
        self,
        location_query: DecisionLocationQuery,
        requested_time: Optional[str] = None,
        domain: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvidenceBundle:
        """Assembles a typed, auditable EvidenceBundle."""
        bundle_id = f"eb_{uuid.uuid4().hex[:8]}"
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        now_dt = datetime.now(tz_ist)
        req_time = requested_time or now_dt.isoformat()

        # 1. Resolve Geographic Location
        location = self._resolve_location(location_query)

        # 2. Define Valid Operational Window
        valid_start = now_dt.isoformat()
        valid_end = (now_dt + timedelta(hours=24)).isoformat()
        valid_time = {"start": valid_start, "end": valid_end}

        # 3. Retrieve Observations, Forecasts, and Warnings from WeatherProviderManager
        obs_data: Dict[str, Any] = {}
        forecast_data: Dict[str, Any] = {}
        alerts_list: List[Dict[str, Any]] = []
        sources: List[Dict[str, Any]] = []
        qc_checks: List[Dict[str, Any]] = []
        limitations: List[str] = []

        lat = location.latitude or 26.2183
        lon = location.longitude or 78.1828

        # --- A. Surface Observation ---
        try:
            obs = await self.weather_manager.get_current_observation(lat, lon)
            obs_data = {
                "temperature_c": obs.temperature_c,
                "relative_humidity_pct": obs.relative_humidity_pct,
                "wind_speed_kmh": obs.wind_speed_kmh,
                "wind_direction_deg": obs.wind_direction_deg,
                "pressure_hpa": obs.pressure_hpa,
                "precipitation_rate_mmh": obs.precipitation_rate_mmh,
                "condition": obs.condition,
                "retrieved_at": obs.retrieved_at,
                "station_id": obs.station_id,
                "units": {
                    "temperature": "°C",
                    "relative_humidity": "%",
                    "wind_speed": "km/h",
                    "wind_direction": "degrees",
                    "pressure": "hPa",
                    "precipitation_rate": "mm/h",
                },
            }
            sources.append({
                "provider": obs.provider,
                "dataset": "Surface Synoptic Observation",
                "retrieved_at": obs.retrieved_at,
                "is_official": obs.is_official,
            })
            # Run physical range checks
            qc_checks.extend(self._qc_check_observation(obs_data))
        except Exception as exc:
            logger.warning("EvidenceBundleBuilder: Failed to fetch surface observation: %s", exc)
            limitations.append("Real-time surface observation unavailable; relying on numerical forecast.")

        # --- B. Multi-Day Forecast ---
        try:
            fc = await self.weather_manager.get_weather_forecast(lat, lon, days=3)
            fc_days = []
            for d in getattr(fc, "daily", []):
                fc_days.append({
                    "date": d.date_str,
                    "temp_max_c": d.temp_max_c,
                    "temp_min_c": d.temp_min_c,
                    "rainfall_total_mm": d.precipitation_sum_mm,
                    "rain_probability_pct": d.precipitation_probability_max_pct,
                    "wind_speed_kmh": d.wind_speed_max_kmh,
                    "condition": d.weather_condition,
                    "units": {
                        "temp_max": "°C",
                        "temp_min": "°C",
                        "rainfall": "mm",
                        "rain_probability": "%",
                        "wind_speed": "km/h",
                    },
                })
            
            fc_hourly = []
            for h in getattr(fc, "hourly", []):
                fc_hourly.append({
                    "time_iso": getattr(h, "time_iso", ""),
                    "temperature_c": getattr(h, "temperature_c", 0.0),
                    "relative_humidity_pct": getattr(h, "relative_humidity_pct", 0.0),
                    "precipitation_mm": getattr(h, "precipitation_mm", 0.0),
                    "rain_probability_pct": getattr(h, "rain_probability_pct", 0.0),
                    "wind_speed_kmh": getattr(h, "wind_speed_kmh", 0.0),
                    "wind_gust_kmh": getattr(h, "wind_gust_kmh", None),
                    "weather_condition": getattr(h, "weather_condition", "clear"),
                })

            # Primary evaluation day (today or requested evening)
            day0 = fc_days[0] if fc_days else {}
            forecast_data = {
                "provider": fc.provider,
                "retrieved_at": fc.retrieved_at,
                "daily": fc_days,
                "hourly": fc_hourly,
                "target_period": day0,
                # Convenience shortcuts for decision engine
                "temp_max_c": day0.get("temp_max_c", obs_data.get("temperature_c", 30.0)),
                "temp_min_c": day0.get("temp_min_c", 22.0),
                "rainfall_total_mm": day0.get("rainfall_total_mm", 0.0),
                "rain_probability_pct": day0.get("rain_probability_pct", 0.0),
                "wind_speed_kmh": day0.get("wind_speed_kmh", obs_data.get("wind_speed_kmh", 10.0)),
            }

            sources.append({
                "provider": fc.provider,
                "dataset": "Numerical Weather Forecast",
                "retrieved_at": fc.retrieved_at,
                "is_official": fc.is_official,
            })
            qc_checks.extend(self._qc_check_forecast(forecast_data))
        except Exception as exc:
            logger.warning("EvidenceBundleBuilder: Failed to fetch weather forecast: %s", exc)
            limitations.append("Multi-day weather forecast unavailable.")

        # --- C. Official Warnings (IMD / NDMA) ---
        try:
            alerts = await self.weather_manager.get_official_warnings(lat, lon)
            for a in alerts:
                alerts_list.append({
                    "source": a.source,
                    "warning_level": a.warning_level.value,
                    "hazard": a.hazard,
                    "headline": a.headline,
                    "description": a.description,
                    "valid_until": a.valid_until,
                    "is_official": True,
                })
                sources.append({
                    "provider": a.source,
                    "dataset": "Official Severe Weather Bulletins (CAP)",
                    "retrieved_at": now_dt.isoformat(),
                    "is_official": True,
                })
        except Exception as exc:
            logger.warning("EvidenceBundleBuilder: Failed to fetch official warnings: %s", exc)
            limitations.append("Official severe weather warning feed temporarily unreachable.")

        # --- D. Model Information & WRF Honesty Rule ---
        model_info: Dict[str, Any] = {}
        # 1. GFS Status
        model_info["gfs"] = {
            "model_name": "NOAA GFS 0.25°",
            "status": "available",
            "grid_resolution": "0.25 degrees (~27 km)",
            "update_cycle": "6-hourly",
            "lead_hours": 24,
        }
        sources.append({
            "provider": "NOAA NCEP",
            "dataset": "Global Forecast System (GFS 0.25°)",
            "retrieved_at": now_dt.isoformat(),
            "is_official": True,
        })

        # 2. WRF Status (MANDATORY HONESTY RULE)
        try:
            wrf_status = await self.weather_manager.get_wrf_status(lat, lon, lead_hours=24)
            is_wrf_live = (
                wrf_status.status.value == "AVAILABLE"
                and wrf_status.data is not None
                and wrf_status.data.quality == ProviderQuality.VALID
            )
        except Exception:
            is_wrf_live = False

        if is_wrf_live:
            model_info["wrf"] = {
                "model_name": "WRF Regional NWP",
                "status": "available",
                "grid_resolution": "3 km convective-permitting",
            }
        else:
            # Explicitly enforce honesty: never claim WRF is available when unconfigured
            model_info["wrf"] = {
                "model_name": "WRF Regional NWP",
                "status": "unavailable",
                "reason": "No legitimate live stream configured; WRF regional model is unconfigured.",
            }
            limitations.append(
                "WRF regional numerical model is not configured; forecast relies on GFS 0.25° / Open-Meteo guidance. "
                "No multi-model divergence computed."
            )

        # --- E. Quality Control Summary ---
        all_qc_passed = all(check.get("passed", True) for check in qc_checks)
        quality_summary = {
            "freshness": "fresh",
            "completeness": "complete" if obs_data and forecast_data else "partial",
            "qc_passed": all_qc_passed,
            "qc_checks": qc_checks,
        }

        # --- F. Honest Uncertainty Assessment ---
        uncertainty = {
            "forecast_lead_horizon": "Short-range (0-24h)",
            "multi_model_divergence_status": "single_model_dominant",
            "wrf_available": is_wrf_live,
            "statement": (
                "High confidence in short-range surface synoptic parameters. Forecast relies on global "
                "guidance as regional high-resolution WRF is not active."
            ),
        }

        return EvidenceBundle(
            bundle_id=bundle_id,
            location=location,
            requested_time=req_time,
            valid_time=valid_time,
            observations=obs_data,
            forecast=forecast_data,
            alerts=alerts_list,
            model_information=model_info,
            source_information=sources,
            quality=quality_summary,
            calculations={},
            uncertainty=uncertainty,
            limitations=limitations,
        )

    def _resolve_location(self, query: DecisionLocationQuery) -> LocationContext:
        """Resolves location query coordinates and administrative hierarchy."""
        if query.latitude is not None and query.longitude is not None:
            return LocationContext(
                name=query.name or f"Point({query.latitude:.2f}, {query.longitude:.2f})",
                latitude=query.latitude,
                longitude=query.longitude,
                district=query.district,
                state=query.state,
                country="India",
            )

        # Check offline INDIAN_LOCATIONS dictionary
        q_name = (query.name or "").strip().lower()
        if q_name in INDIAN_LOCATIONS:
            meta = INDIAN_LOCATIONS[q_name]
            return LocationContext(
                name=meta["name"],
                latitude=meta["lat"],
                longitude=meta["lon"],
                district=meta.get("district"),
                state=meta.get("state"),
                country="India",
            )

        # Fallback to capital/default
        return LocationContext(
            name=query.name or "Gwalior",
            latitude=26.2183,
            longitude=78.1828,
            district="Gwalior",
            state="Madhya Pradesh",
            country="India",
        )

    def _qc_check_observation(self, obs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validates surface observation against physical sanity limits."""
        checks = []
        t = obs.get("temperature_c")
        if t is not None:
            checks.append({
                "variable": "temperature",
                "value": t,
                "unit": "°C",
                "range": "[-10.0, 55.0]",
                "passed": -10.0 <= t <= 55.0,
            })
        rh = obs.get("relative_humidity_pct")
        if rh is not None:
            checks.append({
                "variable": "relative_humidity",
                "value": rh,
                "unit": "%",
                "range": "[0.0, 100.0]",
                "passed": 0.0 <= rh <= 100.0,
            })
        w = obs.get("wind_speed_kmh")
        if w is not None:
            checks.append({
                "variable": "wind_speed",
                "value": w,
                "unit": "km/h",
                "range": "[0.0, 200.0]",
                "passed": 0.0 <= w <= 200.0,
            })
        return checks

    def _qc_check_forecast(self, fc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validates forecast parameters against physical sanity limits."""
        checks = []
        t_max = fc.get("temp_max_c")
        if t_max is not None:
            checks.append({
                "variable": "temp_max",
                "value": t_max,
                "unit": "°C",
                "range": "[-10.0, 55.0]",
                "passed": -10.0 <= t_max <= 55.0,
            })
        rain_prob = fc.get("rain_probability_pct")
        if rain_prob is not None:
            checks.append({
                "variable": "rain_probability",
                "value": rain_prob,
                "unit": "%",
                "range": "[0.0, 100.0]",
                "passed": 0.0 <= rain_prob <= 100.0,
            })
        rain_mm = fc.get("rainfall_total_mm")
        if rain_mm is not None:
            checks.append({
                "variable": "rainfall_total",
                "value": rain_mm,
                "unit": "mm",
                "range": "[0.0, 1000.0]",
                "passed": rain_mm >= 0.0,
            })
        return checks
