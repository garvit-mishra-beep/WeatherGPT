"""Data Fusion Engine: Synthesizes observations, model analyses, and forecasts into CanonicalWeatherState."""

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

from app.brains.analyst_core.models.schemas import DataType
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
)
from app.brains.analyst_core.models.canonical_state import (
    CanonicalWeatherVariable,
    CanonicalWeatherState,
)


class DataFusionEngine:
    """Fuses multi-sensor and NWP data streams into a single coherent CanonicalWeatherState."""

    def fuse(
        self,
        location: str,
        observations: List[WeatherObservation],
        forecasts: List[ForecastPoint],
        alerts: List[OfficialAlert],
        target_time: datetime,
        time_window_label: str = "current",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> CanonicalWeatherState:
        """Synthesizes observations and forecast streams with optimal weighting and uncertainty."""
        self._active_target_time = target_time
        is_forecast = time_window_label in {"tomorrow", "next_12_hours", "next_24_hours"}

        # 1. Temperature Fusion
        temp_var = self._fuse_scalar(
            name="temperature",
            unit="°C",
            obs_values=[(o.temperature_c, o.source, o.data_type, o.timestamp) for o in observations if o.temperature_c is not None],
            fc_values=[(f.temperature_c, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.temperature_c is not None],
            is_forecast=is_forecast,
            default_obs_std=0.5,
            default_fc_std=1.5,
        )

        # 2. Rainfall Fusion
        rain_var = self._fuse_accumulated(
            name="rainfall",
            unit="mm",
            obs_values=[(o.rainfall_mm, o.source, o.data_type, o.timestamp) for o in observations if o.rainfall_mm is not None],
            fc_values=[(f.rainfall_mm, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.rainfall_mm is not None],
            is_forecast=is_forecast,
            default_obs_std=1.0,
            default_fc_std=5.0,
        )

        # 3. Wind Speed Fusion
        wind_var = self._fuse_scalar(
            name="wind_speed",
            unit="km/h",
            obs_values=[(o.wind_speed_kmh, o.source, o.data_type, o.timestamp) for o in observations if o.wind_speed_kmh is not None],
            fc_values=[(f.wind_speed_kmh, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.wind_speed_kmh is not None],
            is_forecast=is_forecast,
            default_obs_std=2.0,
            default_fc_std=4.0,
        )

        # 4. Wind Gust Fusion
        gust_var = self._fuse_scalar(
            name="wind_gust",
            unit="km/h",
            obs_values=[(o.wind_gust_kmh, o.source, o.data_type, o.timestamp) for o in observations if o.wind_gust_kmh is not None],
            fc_values=[(f.wind_gust_kmh, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.wind_gust_kmh is not None],
            is_forecast=is_forecast,
            default_obs_std=3.0,
            default_fc_std=6.0,
        )

        # 5. Humidity Fusion
        humidity_var = self._fuse_scalar(
            name="humidity",
            unit="%",
            obs_values=[(o.humidity_pct, o.source, o.data_type, o.timestamp) for o in observations if o.humidity_pct is not None],
            fc_values=[(f.humidity_pct, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.humidity_pct is not None],
            is_forecast=is_forecast,
            default_obs_std=2.0,
            default_fc_std=5.0,
        )

        # 6. Pressure Fusion
        pressure_var = self._fuse_scalar(
            name="pressure",
            unit="hPa",
            obs_values=[(o.pressure_hpa, o.source, o.data_type, o.timestamp) for o in observations if o.pressure_hpa is not None],
            fc_values=[(f.pressure_hpa, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.pressure_hpa is not None],
            is_forecast=is_forecast,
            default_obs_std=0.5,
            default_fc_std=1.5,
        )

        # 7. CAPE Fusion
        cape_var = self._fuse_scalar(
            name="cape",
            unit="J/kg",
            obs_values=[],
            fc_values=[(f.cape_jkg, f.model_name, f.data_type, f.valid_time) for f in forecasts if f.cape_jkg is not None],
            is_forecast=is_forecast,
            default_obs_std=50.0,
            default_fc_std=150.0,
        )

        # 8. Visibility Fusion
        vis_var = self._fuse_scalar(
            name="visibility",
            unit="m",
            obs_values=[(o.visibility_m, o.source, o.data_type, o.timestamp) for o in observations if o.visibility_m is not None],
            fc_values=[],
            is_forecast=is_forecast,
            default_obs_std=100.0,
            default_fc_std=500.0,
        )

        # Determine overall state metadata
        is_synthetic = any(o.is_synthetic for o in observations) or any(f.is_synthetic for f in forecasts)
        
        self._active_target_time = target_time
        # Calculate freshness based on observation closest to target_time
        freshness_age = 0.0
        if observations:
            closest_obs = min(observations, key=lambda o: abs((target_time - o.timestamp).total_seconds()))
            freshness_age = max(0.0, (target_time - closest_obs.timestamp).total_seconds() / 3600.0)

        # Calculate completeness across standard variables
        core_vars = [temp_var, rain_var, wind_var, humidity_var, pressure_var]
        available_vars = [v for v in core_vars if v and v.value is not None]
        completeness = round((len(available_vars) / max(1, len(core_vars))) * 100.0, 1)

        return CanonicalWeatherState(
            location=location,
            latitude=latitude,
            longitude=longitude,
            target_time=target_time,
            time_window_label=time_window_label,
            temperature=temp_var,
            rainfall=rain_var,
            wind_speed=wind_var,
            wind_gust=gust_var,
            humidity=humidity_var,
            pressure=pressure_var,
            visibility=vis_var,
            cape=cape_var,
            active_alerts=alerts,
            data_freshness_age_hours=round(freshness_age, 2),
            data_completeness_pct=completeness,
            is_synthetic=is_synthetic,
        )

    def _fuse_scalar(
        self,
        name: str,
        unit: str,
        obs_values: List[Tuple[float, str, DataType, datetime]],
        fc_values: List[Tuple[float, str, DataType, datetime]],
        is_forecast: bool,
        default_obs_std: float,
        default_fc_std: float,
    ) -> Optional[CanonicalWeatherVariable]:
        """Fuses scalar measurements using source provenance weighting."""
        if is_forecast and fc_values:
            # For forecast window, evaluate NWP values
            vals = [v[0] for v in fc_values]
            mean_val = float(np.mean(vals))
            spread = float(np.std(vals)) if len(vals) > 1 else default_fc_std
            source_name = fc_values[0][1]
            data_type = fc_values[0][2]
            ts = fc_values[0][3]
            ci_95 = (round(mean_val - 1.96 * spread, 1), round(mean_val + 1.96 * spread, 1))
            return CanonicalWeatherVariable(
                name=name,
                value=round(mean_val, 1),
                unit=unit,
                uncertainty_std=round(spread, 2),
                confidence_interval_95=ci_95,
                origin_type=data_type,
                source_name=source_name,
                timestamp=ts,
            )

        t_target = getattr(self, "_active_target_time", datetime.utcnow())
        if obs_values:
            # Ground observations/analysis temporally aligned to target_time
            lead_val = min(obs_values, key=lambda item: abs((item[3] - t_target).total_seconds()))
            val = lead_val[0]
            ci_95 = (round(val - 1.96 * default_obs_std, 1), round(val + 1.96 * default_obs_std, 1))
            return CanonicalWeatherVariable(
                name=name,
                value=round(val, 1),
                unit=unit,
                uncertainty_std=default_obs_std,
                confidence_interval_95=ci_95,
                origin_type=lead_val[2],
                source_name=lead_val[1],
                timestamp=lead_val[3],
            )

        if fc_values:
            # Fallback to model forecast temporally aligned to target_time
            lead_fc = min(fc_values, key=lambda item: abs((item[3] - t_target).total_seconds()))
            val = lead_fc[0]
            ci_95 = (round(val - 1.96 * default_fc_std, 1), round(val + 1.96 * default_fc_std, 1))
            return CanonicalWeatherVariable(
                name=name,
                value=round(val, 1),
                unit=unit,
                uncertainty_std=default_fc_std,
                confidence_interval_95=ci_95,
                origin_type=lead_fc[2],
                source_name=lead_fc[1],
                timestamp=lead_fc[3],
            )

        return None

    def _fuse_accumulated(
        self,
        name: str,
        unit: str,
        obs_values: List[Tuple[float, str, DataType, datetime]],
        fc_values: List[Tuple[float, str, DataType, datetime]],
        is_forecast: bool,
        default_obs_std: float,
        default_fc_std: float,
    ) -> Optional[CanonicalWeatherVariable]:
        """Fuses accumulated precipitation."""
        if is_forecast and fc_values:
            total_rain = sum(v[0] for v in fc_values)
            source_name = fc_values[0][1]
            data_type = fc_values[0][2]
            ts = fc_values[0][3]
            ci_95 = (round(max(0.0, total_rain - 1.96 * default_fc_std), 1), round(total_rain + 1.96 * default_fc_std, 1))
            return CanonicalWeatherVariable(
                name=name,
                value=round(total_rain, 1),
                unit=unit,
                uncertainty_std=default_fc_std,
                confidence_interval_95=ci_95,
                origin_type=data_type,
                source_name=source_name,
                timestamp=ts,
            )

        if obs_values:
            total_rain = sum(v[0] for v in obs_values)
            t_target = getattr(self, "_active_target_time", datetime.utcnow())
            lead = min(obs_values, key=lambda item: abs((item[3] - t_target).total_seconds()))
            ci_95 = (round(max(0.0, total_rain - 1.96 * default_obs_std), 1), round(total_rain + 1.96 * default_obs_std, 1))
            return CanonicalWeatherVariable(
                name=name,
                value=round(total_rain, 1),
                unit=unit,
                uncertainty_std=default_obs_std,
                confidence_interval_95=ci_95,
                origin_type=lead[2],
                source_name=lead[1],
                timestamp=lead[3],
            )

        return None
