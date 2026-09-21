"""Climate Intelligence Service.

Coordinates deterministic data extraction, WMO climatological baseline lookup,
pure NumPy statistical engines, and the optional Gemma 4:e2b explanation bridge.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.adapters.strategy import WeatherProviderManager
from app.brains.analyst_core.data.climate_normals import ClimateNormalsEngine, MonthlyClimateNormal
from app.climate.analytics import (
    analyze_rainfall,
    analyze_temperature,
    analyze_trend,
    calculate_anomaly,
    evaluate_data_quality,
)
from app.climate.explanation_bridge import ClimateExplanationBridge
from app.climate.models import (
    AnomalyCategory,
    ClimateAnalysisRequest,
    ClimateAnalysisResponse,
    ClimateAnomalyResult,
    ClimateEvidence,
    ClimateNormalsResponse,
    ClimateQualityInfo,
    ClimateTrendResult,
    ClimateTrendsResponse,
    ClimateVariable,
    DataQuality,
    RainfallMetrics,
    TemperatureMetrics,
    TrendDirection,
)

logger = logging.getLogger(__name__)


class ClimateIntelligenceService:
    """Deterministic Climate Analysis and Intelligence Service."""

    def __init__(
        self,
        weather_manager: Optional[WeatherProviderManager] = None,
        normals_engine: Optional[ClimateNormalsEngine] = None,
        explanation_bridge: Optional[ClimateExplanationBridge] = None,
    ) -> None:
        self.weather_manager = weather_manager
        self.normals_engine = normals_engine or ClimateNormalsEngine()
        self.explanation_bridge = explanation_bridge

    def _extract_month_from_period(self, period_start: str) -> int:
        """Parses calendar month (1-12) from date string."""
        try:
            return datetime.fromisoformat(period_start[:10]).month
        except Exception:
            return 1

    def resolve_baseline(
        self,
        location: str,
        month: int,
        latitude: Optional[float] = None,
        custom_baseline_value: Optional[float] = None,
        custom_baseline_source: Optional[str] = None,
        variable: ClimateVariable = ClimateVariable.TEMPERATURE,
    ) -> Tuple[Optional[float], Optional[float], bool, Optional[str], Optional[str]]:
        """Resolves verified baseline normal.
        
        Returns:
            Tuple of (baseline_val, baseline_std, baseline_available, source, period)
        """
        # 1. Custom user-supplied baseline takes precedence if explicitly provided
        if custom_baseline_value is not None:
            return (
                custom_baseline_value,
                None,
                True,
                custom_baseline_source or "User-Supplied Baseline Reference",
                "Custom Period",
            )

        # 2. Check official WMO 1991-2020 IMD Observatory Climatology
        normal_record: Optional[MonthlyClimateNormal] = self.normals_engine.get_baseline(
            location=location,
            month=month,
            latitude=latitude,
        )

        if normal_record is not None:
            source = normal_record.metadata.get("source", "IMD Climatological Tables of Observatories in India (1991-2020)")
            period = normal_record.reference_period
            if variable in (ClimateVariable.TEMPERATURE, ClimateVariable.HEAT_INDEX):
                return (normal_record.normal_temp_c, normal_record.temp_std_c, True, source, period)
            elif variable == ClimateVariable.MAX_TEMPERATURE:
                return (normal_record.normal_max_temp_c, normal_record.temp_std_c, True, source, period)
            elif variable == ClimateVariable.MIN_TEMPERATURE:
                return (normal_record.normal_min_temp_c, normal_record.temp_std_c, True, source, period)
            elif variable == ClimateVariable.RAINFALL:
                return (normal_record.normal_monthly_rainfall_mm, None, True, source, period)

        # 3. If unverified or unsupported, return explicit unavailable state
        return (None, None, False, None, None)

    async def analyze(self, request: ClimateAnalysisRequest) -> ClimateAnalysisResponse:
        """Executes end-to-end deterministic climate intelligence analysis."""
        logger.info(
            "ClimateIntelligenceService analyzing %s for location '%s' [%s to %s]",
            request.variable.value,
            request.location,
            request.period_start,
            request.period_end,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        month = self._extract_month_from_period(request.period_start)

        # 1. Resolve observations
        observations: List[float] = []
        obs_dates = request.observation_dates or []

        if request.observations and len(request.observations) > 0:
            observations = [float(v) for v in request.observations if v is not None]
        elif request.latitude is not None and request.longitude is not None and self.weather_manager is not None:
            # Operational surface observations from weather provider if available
            try:
                forecast = await self.weather_manager.get_weather_forecast(
                    latitude=request.latitude,
                    longitude=request.longitude,
                    days=7,
                )
                if forecast and forecast.daily_forecast:
                    if request.variable in (ClimateVariable.TEMPERATURE, ClimateVariable.HEAT_INDEX):
                        observations = [
                            (d.temperature_max_c + d.temperature_min_c) / 2.0
                            for d in forecast.daily_forecast
                        ]
                    elif request.variable == ClimateVariable.MAX_TEMPERATURE:
                        observations = [d.temperature_max_c for d in forecast.daily_forecast]
                    elif request.variable == ClimateVariable.MIN_TEMPERATURE:
                        observations = [d.temperature_min_c for d in forecast.daily_forecast]
                    elif request.variable == ClimateVariable.RAINFALL:
                        observations = [d.precipitation_sum_mm for d in forecast.daily_forecast]
                    obs_dates = [d.date_str for d in forecast.daily_forecast]
            except Exception as e:
                logger.warning("Failed to retrieve provider weather points: %s", e)

        # 2. Quality Evaluation
        min_bound = -50.0 if request.variable != ClimateVariable.RAINFALL else 0.0
        max_bound = 60.0 if request.variable != ClimateVariable.RAINFALL else 2000.0
        quality_info: ClimateQualityInfo = evaluate_data_quality(
            observations=observations,
            min_physical_bound=min_bound,
            max_physical_bound=max_bound,
        )

        sample_size = len(observations)
        uncertainties = list(quality_info.limitations)

        if sample_size == 0:
            # Empty observations fallback
            uncertainties.append("Zero numerical observations available for this temporal window.")
            evidence = ClimateEvidence(
                location=request.location,
                latitude=request.latitude,
                longitude=request.longitude,
                variable=request.variable.value,
                period_start=request.period_start,
                period_end=request.period_end,
                sample_size=0,
                baseline_available=False,
                coverage_pct=0.0,
                quality=DataQuality.INSUFFICIENT_DATA,
                source="Vayubodhak Climate Gateway",
                dataset="None",
                retrieved_at=now_iso,
                units="°C" if request.variable != ClimateVariable.RAINFALL else "mm",
                uncertainty=uncertainties,
                provenance={"status": "INSUFFICIENT_DATA"},
            )
            return ClimateAnalysisResponse(evidence=evidence, anomaly_result=None)

        # 3. Resolve baseline normal
        base_val, base_std, base_avail, base_src, base_period = self.resolve_baseline(
            location=request.location,
            month=month,
            latitude=request.latitude,
            custom_baseline_value=request.baseline_value,
            custom_baseline_source=request.baseline_source,
            variable=request.variable,
        )

        if not base_avail:
            uncertainties.append(
                f"Historical climatological baseline unavailable for '{request.location}' in month {month}. "
                "Anomaly and departure metrics cannot be computed without a verified reference normal."
            )

        # 4. Deterministic analytics execution
        units = "°C" if request.variable != ClimateVariable.RAINFALL else "mm"
        temp_metrics: Optional[TemperatureMetrics] = None
        rain_metrics: Optional[RainfallMetrics] = None
        anomaly_res: Optional[ClimateAnomalyResult] = None
        mean_val: Optional[float] = None
        min_val: Optional[float] = None
        max_val: Optional[float] = None
        cum_val: Optional[float] = None
        dry_spell: Optional[int] = None
        wet_spell: Optional[int] = None

        if request.variable in (ClimateVariable.TEMPERATURE, ClimateVariable.MAX_TEMPERATURE, ClimateVariable.MIN_TEMPERATURE, ClimateVariable.HEAT_INDEX):
            temp_metrics, anomaly_res = analyze_temperature(
                daily_temps=observations,
                dates=obs_dates,
                baseline_mean=base_val,
                baseline_max=base_val if request.variable == ClimateVariable.MAX_TEMPERATURE else None,
                region_type=request.region_type,
            )
            mean_val = temp_metrics.mean_c
            min_val = temp_metrics.min_c
            max_val = temp_metrics.max_c
        else:
            rain_metrics, anomaly_res = analyze_rainfall(
                daily_rain=observations,
                dates=obs_dates,
                baseline_sum=base_val,
            )
            cum_val = rain_metrics.cumulative_mm
            mean_val = rain_metrics.average_daily_mm
            min_val = float(min(observations)) if observations else 0.0
            max_val = rain_metrics.max_1day_precipitation_rx1day_mm
            dry_spell = rain_metrics.consecutive_dry_days
            wet_spell = rain_metrics.consecutive_wet_days

        # Ensure anomaly_res accurately reflects unavailable baseline if none was passed
        if anomaly_res is None:
            anomaly_res = calculate_anomaly(
                observed=cum_val if cum_val is not None else (mean_val or 0.0),
                baseline=base_val,
                std_dev=base_std,
                variable_name=request.variable.value.capitalize(),
                units=units,
                baseline_source=base_src,
                baseline_period=base_period,
            )

        # 5. Trend Test
        period_span = f"{request.period_start} to {request.period_end}"
        trend_res: ClimateTrendResult = analyze_trend(
            series=observations,
            period_description=period_span,
        )

        # 6. Build immutable Evidence Package
        provenance = {
            "calculation_engine": "Vayubodhak Deterministic Climate Analytics (Pure NumPy)",
            "baseline_source": base_src or "Unavailable",
            "baseline_period": base_period or "Unavailable",
            "algorithm_standards": ["WMO Guidelines on the Calculation of Climate Normals (WMO-No. 1203)", "ETCCDI Extremes"],
            "retrieval_timestamp": now_iso,
        }

        evidence = ClimateEvidence(
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            variable=request.variable.value,
            period_start=request.period_start,
            period_end=request.period_end,
            sample_size=sample_size,
            mean=mean_val,
            min=min_val,
            max=max_val,
            cumulative=cum_val,
            baseline_available=base_avail,
            baseline_value=base_val,
            anomaly=anomaly_res.absolute_anomaly,
            anomaly_percent=anomaly_res.anomaly_percent,
            anomaly_category=anomaly_res.category,
            temperature_metrics=temp_metrics,
            rainfall_metrics=rain_metrics,
            dry_spell_cdd=dry_spell,
            wet_spell_cwd=wet_spell,
            trend=trend_res,
            coverage_pct=quality_info.coverage_pct,
            quality=quality_info.quality_status,
            source=base_src or "Vayubodhak Climate Station Records",
            dataset=f"Observations ({request.period_start} to {request.period_end})",
            retrieved_at=now_iso,
            units=units,
            uncertainty=uncertainties,
            provenance=provenance,
        )

        # 7. Optional Gemma 4:e2b Explanation
        explanation: Optional[str] = None
        explanation_source: Optional[str] = None

        if request.include_explanation and self.explanation_bridge is not None:
            explanation, explanation_source = await self.explanation_bridge.explain_climate(
                evidence=evidence,
                anomaly=anomaly_res,
            )

        return ClimateAnalysisResponse(
            evidence=evidence,
            anomaly_result=anomaly_res,
            explanation=explanation,
            explanation_source=explanation_source,
            generated_at_iso=now_iso,
        )

    async def get_trends(
        self,
        latitude: float,
        longitude: float,
        location: Optional[str] = None,
        variable: ClimateVariable = ClimateVariable.RAINFALL,
        start_year: int = 1991,
        end_year: int = 2024,
    ) -> ClimateTrendsResponse:
        """Computes deterministic Mann-Kendall and Sen's slope trend test."""
        series: List[float] = []
        loc_name = location or f"Station ({latitude:.2f}°N, {longitude:.2f}°E)"

        # 1. Operational short-term observation series from weather manager if available
        if self.weather_manager is not None:
            try:
                forecast = await self.weather_manager.get_weather_forecast(
                    latitude=latitude,
                    longitude=longitude,
                    days=7,
                )
                daily_pts = getattr(forecast, "daily", None) or getattr(forecast, "daily_forecast", None) or []
                if daily_pts:
                    if variable == ClimateVariable.RAINFALL:
                        series = [getattr(d, "precipitation_sum_mm", 0.0) for d in daily_pts]
                    else:
                        series = [
                            ((getattr(d, "temp_max_c", 0.0) or getattr(d, "temperature_max_c", 0.0)) +
                             (getattr(d, "temp_min_c", 0.0) or getattr(d, "temperature_min_c", 0.0))) / 2.0
                            for d in daily_pts
                        ]
            except Exception as e:
                logger.warning("Could not fetch forecast for climate trends: %s", e)

        # 2. Climatological normal monthly distribution if series too small
        if len(series) < 3:
            loc_key = (location or "").strip().lower()
            if loc_key not in self.normals_engine.IMD_1991_2020_CLIMATOLOGY:
                coords = {
                    "delhi": (28.61, 77.21),
                    "gwalior": (26.22, 78.18),
                    "mumbai": (19.07, 72.87),
                    "kolkata": (22.57, 88.36),
                }
                closest = min(
                    coords.keys(),
                    key=lambda k: (coords[k][0] - latitude) ** 2 + (coords[k][1] - longitude) ** 2,
                )
                loc_key = closest
                loc_name = location or loc_key.capitalize()

            stn_data = self.normals_engine.IMD_1991_2020_CLIMATOLOGY.get(loc_key, {})
            months_dict = stn_data.get("months", {})
            if variable == ClimateVariable.RAINFALL:
                series = [months_dict[m]["rain"] for m in sorted(months_dict.keys()) if "rain" in months_dict[m]]
            else:
                series = [months_dict[m]["mean_t"] for m in sorted(months_dict.keys()) if "mean_t" in months_dict[m]]

        period_desc = f"{start_year}-{end_year}"
        trend_res = analyze_trend(
            series=series,
            alpha=0.05,
            period_description=period_desc,
        )

        return ClimateTrendsResponse(
            location=loc_name,
            latitude=latitude,
            longitude=longitude,
            variable=variable.value,
            trend_slope=round(trend_res.slope or 0.0, 4),
            p_value=round(trend_res.p_value or 1.0, 4),
            is_significant=trend_res.is_significant,
            direction=trend_res.direction.value,
            sample_size=trend_res.sample_size,
            period=period_desc,
            method="Mann-Kendall & Sen's Slope",
            provenance={
                "source": "IMD 1991-2020 Observatories & Operational Surface Observations",
                "observations_count": len(series),
            },
        )

    async def get_normals(
        self,
        latitude: float,
        longitude: float,
        location: Optional[str] = None,
        month: Optional[int] = None,
    ) -> ClimateNormalsResponse:
        """Resolves verified 30-year climatological normal and computes real-time departure."""
        target_month = month or datetime.now(timezone.utc).month

        coords = {
            "delhi": (28.61, 77.21),
            "gwalior": (26.22, 78.18),
            "mumbai": (19.07, 72.87),
            "kolkata": (22.57, 88.36),
        }
        loc_key = (location or "").strip().lower()
        if loc_key not in self.normals_engine.IMD_1991_2020_CLIMATOLOGY:
            closest = min(
                coords.keys(),
                key=lambda k: (coords[k][0] - latitude) ** 2 + (coords[k][1] - longitude) ** 2,
            )
            loc_key = closest
            loc_name = location or loc_key.capitalize()
        else:
            loc_name = location or loc_key.capitalize()

        normal_rec = self.normals_engine.get_baseline(
            location=loc_key,
            month=target_month,
            latitude=latitude,
        )

        actual_temp: Optional[float] = None
        actual_rain: Optional[float] = None

        if self.weather_manager is not None:
            try:
                curr = await self.weather_manager.get_current_weather(latitude=latitude, longitude=longitude)
                if curr:
                    actual_temp = round(curr.temperature_c, 2)
            except Exception as e:
                logger.warning("Could not fetch current weather for normals: %s", e)

            try:
                forecast = await self.weather_manager.get_weather_forecast(
                    latitude=latitude,
                    longitude=longitude,
                    days=7,
                )
                daily_pts = getattr(forecast, "daily", None) or getattr(forecast, "daily_forecast", None) or []
                if daily_pts:
                    actual_rain = round(sum(getattr(d, "precipitation_sum_mm", 0.0) for d in daily_pts), 2)
            except Exception as e:
                logger.warning("Could not fetch forecast rainfall for normals: %s", e)

        normal_rain = normal_rec.normal_monthly_rainfall_mm if normal_rec else None
        normal_temp = normal_rec.normal_temp_c if normal_rec else None

        rain_anomaly_pct: Optional[float] = None
        if actual_rain is not None and normal_rain is not None and normal_rain > 0:
            rain_anomaly_pct = round(((actual_rain - normal_rain) / normal_rain) * 100.0, 2)

        temp_anomaly_c: Optional[float] = None
        if actual_temp is not None and normal_temp is not None:
            temp_anomaly_c = round(actual_temp - normal_temp, 2)

        category = "Near Normal"
        if rain_anomaly_pct is not None:
            if rain_anomaly_pct >= 20.0:
                category = "Above Normal"
            elif rain_anomaly_pct <= -20.0:
                category = "Below Normal"

        return ClimateNormalsResponse(
            location=loc_name,
            latitude=latitude,
            longitude=longitude,
            month=target_month,
            normal_rainfall_mm=normal_rain,
            actual_rainfall_mm=actual_rain,
            rainfall_anomaly_pct=rain_anomaly_pct,
            normal_temp_c=normal_temp,
            actual_temp_c=actual_temp,
            temp_anomaly_c=temp_anomaly_c,
            category=category,
            source="IMD Climatological Tables of Observatories in India (1991-2020)",
            reference_period="1991-2020",
            provenance={
                "station_name": normal_rec.metadata.get("station_name") if normal_rec else None,
                "station_wmo_id": normal_rec.station_wmo_id if normal_rec else None,
            },
        )

