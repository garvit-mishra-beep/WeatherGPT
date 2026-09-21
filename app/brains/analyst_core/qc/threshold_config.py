"""Versioned meteorological threshold registry.

Ensures all hazard and risk determinations are tied to an immutable, cited configuration.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class ThresholdConfig(BaseModel):
    """Immutable versioned meteorological threshold configuration."""
    config_version: str = "IMD-MET-2024.1"
    authority_citation: str = (
        "India Meteorological Department (IMD) Standard Operational Guidelines for "
        "Severe Weather Warnings (2024) & WMO Guidelines on Multi-Hazard Early Warning Systems (No. 1150)"
    )
    effective_date: str = "2024-01-01"

    # Precipitation thresholds (24-hour accumulation)
    heavy_rain_24h_mm: float = 64.5
    very_heavy_rain_24h_mm: float = 115.6
    extremely_heavy_rain_24h_mm: float = 204.5

    # Short-duration burst intensity
    flash_flood_hourly_burst_mm: float = 50.0
    flash_flood_3hour_burst_mm: float = 100.0

    # Heatwave thresholds (Plains)
    heatwave_min_temp_plains_c: float = 40.0
    heatwave_min_temp_coastal_c: float = 37.0
    heatwave_min_temp_hills_c: float = 30.0
    heatwave_departure_c: float = 4.5
    severe_heatwave_departure_c: float = 6.5

    # Coldwave thresholds
    coldwave_max_min_temp_c: float = 10.0
    coldwave_departure_c: float = -4.5
    severe_coldwave_departure_c: float = -6.5

    # Wind / Gales (km/h)
    strong_wind_kmh: float = 40.0
    squall_wind_kmh: float = 50.0
    gale_wind_kmh: float = 62.0
    severe_gale_wind_kmh: float = 89.0

    # Visibility / Fog (meters)
    moderate_fog_visibility_m: float = 500.0
    dense_fog_visibility_m: float = 200.0
    very_dense_fog_visibility_m: float = 50.0

    # Convective Instability
    cape_moderate_threshold: float = 1000.0
    cape_severe_threshold: float = 2500.0
    lifted_index_unstable_threshold: float = -3.0
    lifted_index_very_unstable_threshold: float = -6.0


class ThresholdRegistry:
    """Registry maintaining available versioned threshold specifications."""

    REGISTRY: Dict[str, ThresholdConfig] = {
        "IMD-MET-2024.1": ThresholdConfig(
            config_version="IMD-MET-2024.1",
            authority_citation="India Meteorological Department (IMD) Standard Operational Guidelines for Severe Weather Warnings (2024)",
            effective_date="2024-01-01",
        ),
        "WMO-STANDARD-2020": ThresholdConfig(
            config_version="WMO-STANDARD-2020",
            authority_citation="WMO Technical Regulations (WMO-No. 49), Volume I - General Meteorological Standards",
            effective_date="2020-06-01",
        ),
    }

    DEFAULT_VERSION = "IMD-MET-2024.1"

    @classmethod
    def get_config(cls, version: Optional[str] = None) -> ThresholdConfig:
        """Retrieves threshold configuration by version key."""
        v = version or cls.DEFAULT_VERSION
        return cls.REGISTRY.get(v, cls.REGISTRY[cls.DEFAULT_VERSION])
