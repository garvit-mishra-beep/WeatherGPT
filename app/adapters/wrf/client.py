"""WRF (Weather Research and Forecasting) Regional NWP Provider Client."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import httpx

from app.adapters.base import BaseNWPProvider
from app.adapters.circuit_breaker import CircuitBreaker
from app.adapters.errors import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.adapters.http_executor import ResilientHTTPExecutor
from app.adapters.models import (
    NormalizedNWPGridPoint,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.wrf.models import WRFGridPointResponse, WRFStatus
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class WRFProvider(BaseNWPProvider):
    """WRF Regional Numerical Weather Prediction data adapter.
    
    Provides high-resolution (3-9 km) regional atmospheric prognostic fields over
    the Indian subcontinent when a partner data stream or local NetCDF/GRIB2 repository
    is configured. When unconfigured, safely returns an explicit WRF_DATA_UNAVAILABLE
    state without synthesizing fake weather values.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="wrf",
            failure_threshold=self.settings.provider_circuit_failure_threshold,
            recovery_timeout=self.settings.provider_circuit_recovery_seconds,
        )
        self.executor = ResilientHTTPExecutor(
            provider_name="wrf",
            circuit_breaker=self.circuit_breaker,
            timeout_seconds=self.settings.provider_timeout_seconds,
            max_retries=self.settings.provider_max_retries,
            retry_base_delay=self.settings.provider_retry_base_delay_seconds,
        )

    @property
    def name(self) -> str:
        return "wrf"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.NUMERICAL_MODEL

    @property
    def is_configured(self) -> bool:
        """Returns True only when a valid WRF data endpoint or dataset path is provided."""
        return bool(
            self.settings.wrf_enabled
            and (self.settings.wrf_base_url or self.settings.wrf_dataset_path)
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._http_client is not None:
            return self._http_client
        return httpx.AsyncClient(timeout=self.settings.provider_timeout_seconds)

    async def get_grid_point(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> NormalizedNWPGridPoint:
        """Extract atmospheric field values at the nearest WRF grid point.
        
        If WRF is not configured, returns an explicit UNAVAILABLE grid point rather than
        synthesizing fake numbers.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        if not self.is_configured:
            logger.info("WRF provider query received but WRF data source is not configured")
            return NormalizedNWPGridPoint(
                latitude=latitude,
                longitude=longitude,
                model_name="WRF_REGIONAL",
                initialization_time_iso=now_iso,
                forecast_lead_hours=lead_hours,
                valid_time_iso=now_iso,
                temperature_2m_c=0.0,
                relative_humidity_2m_pct=0.0,
                accumulated_precip_mm=0.0,
                step_precip_mm=0.0,
                u_wind_10m_ms=0.0,
                v_wind_10m_ms=0.0,
                wind_speed_kmh=0.0,
                wind_direction_deg=0.0,
                wind_gust_kmh=0.0,
                pressure_msl_hpa=1013.25,
                total_cloud_cover_pct=0.0,
                cape_jkg=None,
                grid_resolution_deg=0.03,
                provider="WRF Regional (Unconfigured)",
                quality=ProviderQuality.UNAVAILABLE,
                status_message="WRF regional numerical weather prediction data source is not configured or currently unavailable. Configure WRF_BASE_URL to activate live WRF stream.",
            )

        # When configured, fetch from upstream WRF API / OPeNDAP endpoint
        base_url = self.settings.wrf_base_url.rstrip("/") if self.settings.wrf_base_url else ""
        url = f"{base_url}/grid"
        params: Dict[str, Any] = {
            "lat": latitude,
            "lon": longitude,
            "lead_hours": lead_hours,
        }
        if self.settings.wrf_api_key:
            params["key"] = self.settings.wrf_api_key

        client = await self._get_client()
        try:
            resp = await self.executor.execute_request(
                client=client,
                method="GET",
                url=url,
                operation="grid_point",
                params=params,
            )
            raw = resp.json()
            if asyncio.iscoroutine(raw):
                raw = await raw
            return self._parse_wrf_response(raw, latitude, longitude, lead_hours)
        except Exception as exc:
            logger.warning("WRF provider request failed: %s", exc)
            return NormalizedNWPGridPoint(
                latitude=latitude,
                longitude=longitude,
                model_name="WRF_REGIONAL",
                initialization_time_iso=now_iso,
                forecast_lead_hours=lead_hours,
                valid_time_iso=now_iso,
                temperature_2m_c=0.0,
                relative_humidity_2m_pct=0.0,
                accumulated_precip_mm=0.0,
                step_precip_mm=0.0,
                u_wind_10m_ms=0.0,
                v_wind_10m_ms=0.0,
                wind_speed_kmh=0.0,
                wind_direction_deg=0.0,
                wind_gust_kmh=0.0,
                pressure_msl_hpa=1013.25,
                total_cloud_cover_pct=0.0,
                cape_jkg=None,
                grid_resolution_deg=0.03,
                provider="WRF Regional",
                quality=ProviderQuality.UNAVAILABLE,
                status_message=f"WRF stream communication error: {str(exc)}",
            )

    async def get_wrf_status_response(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> WRFGridPointResponse:
        """Returns the high-level WRF status payload distinguishing AVAILABLE vs UNAVAILABLE."""
        grid_point = await self.get_grid_point(latitude, longitude, lead_hours)
        if grid_point.quality == ProviderQuality.UNAVAILABLE:
            return WRFGridPointResponse(
                status=WRFStatus.UNAVAILABLE,
                status_code="WRF_DATA_UNAVAILABLE",
                message=grid_point.status_message or "WRF regional numerical weather prediction data is currently unavailable.",
                data=grid_point,
                provenance={
                    "model": "WRF_REGIONAL",
                    "configured": self.is_configured,
                    "resolution": "0.03° (~3 km)",
                    "status": "UNAVAILABLE",
                },
            )
        return WRFGridPointResponse(
            status=WRFStatus.AVAILABLE,
            status_code="WRF_DATA_AVAILABLE",
            message="WRF regional prognostic fields successfully retrieved.",
            data=grid_point,
            provenance={
                "model": "WRF_REGIONAL",
                "configured": True,
                "resolution": f"{grid_point.grid_resolution_deg}°",
                "provider": grid_point.provider,
                "initialization": grid_point.initialization_time_iso,
                "status": "AVAILABLE",
            },
        )

    def _parse_wrf_response(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        lead_hours: int,
    ) -> NormalizedNWPGridPoint:
        """Parses upstream WRF JSON response into standardized NormalizedNWPGridPoint."""
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            return NormalizedNWPGridPoint(
                latitude=float(data.get("latitude", latitude)),
                longitude=float(data.get("longitude", longitude)),
                model_name="WRF_REGIONAL",
                initialization_time_iso=str(data.get("initialization_time", now_iso)),
                forecast_lead_hours=int(data.get("forecast_lead_hours", lead_hours)),
                valid_time_iso=str(data.get("valid_time", now_iso)),
                temperature_2m_c=float(data["temperature_2m_c"]),
                relative_humidity_2m_pct=float(data["relative_humidity_2m_pct"]),
                accumulated_precip_mm=float(data["accumulated_precip_mm"]),
                step_precip_mm=float(data.get("step_precip_mm", 0.0)),
                u_wind_10m_ms=float(data.get("u_wind_10m_ms", 0.0)),
                v_wind_10m_ms=float(data.get("v_wind_10m_ms", 0.0)),
                wind_speed_kmh=float(data.get("wind_speed_kmh", 0.0)),
                wind_direction_deg=float(data.get("wind_direction_deg", 0.0)),
                wind_gust_kmh=float(data["wind_gust_kmh"]) if data.get("wind_gust_kmh") is not None else None,
                pressure_msl_hpa=float(data.get("pressure_msl_hpa", 1013.25)),
                total_cloud_cover_pct=float(data.get("total_cloud_cover_pct", 0.0)),
                cape_jkg=float(data["cape_jkg"]) if data.get("cape_jkg") is not None else None,
                grid_resolution_deg=float(data.get("grid_resolution_deg", 0.03)),
                provider=str(data.get("provider", "WRF Regional Stream")),
                quality=ProviderQuality.VALID,
                status_message="Valid WRF regional prognostic data retrieved.",
            )
        except (KeyError, ValueError, TypeError) as err:
            raise ProviderValidationError(f"Malformed WRF response payload: {err}") from err

    async def check_health(self) -> bool:
        """Returns True if WRF is configured and circuit is not open."""
        if not self.is_configured:
            return False
        return self.circuit_breaker.state != "OPEN"
