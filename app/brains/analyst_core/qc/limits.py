"""Configurable meteorological physical plausibility boundaries."""

from typing import Optional
from pydantic import BaseModel


class PhysicalMeteorologicalLimits(BaseModel):
    """Meteorological physical limits for ground and upper-air measurements."""
    min_temp_c: float = -90.0
    max_temp_c: float = 60.0
    min_humidity_pct: float = 0.0
    max_humidity_pct: float = 100.0
    allow_supersaturation: bool = False
    min_wind_speed_kmh: float = 0.0
    max_wind_speed_kmh: float = 450.0  # Record category 5 cyclone gusts
    min_rainfall_mm: float = 0.0
    max_rainfall_hourly_mm: float = 350.0  # World record hourly ~305mm
    min_pressure_hpa: float = 870.0        # Super Typhoon Tip record low 870 hPa
    max_pressure_hpa: float = 1085.0       # Agata Siberia record high 1084.8 hPa
    min_visibility_m: float = 0.0
    max_visibility_m: float = 100000.0     # 100 km standard max
    min_soil_moisture_pct: float = 0.0
    max_soil_moisture_pct: float = 100.0

    def check_temperature(self, temp_c: Optional[float]) -> Optional[str]:
        """Checks temperature validity."""
        if temp_c is None:
            return None
        if temp_c < self.min_temp_c or temp_c > self.max_temp_c:
            return f"Temperature {temp_c}°C violates physical limits [{self.min_temp_c}, {self.max_temp_c}]"
        return None

    def check_humidity(self, humidity_pct: Optional[float]) -> Optional[str]:
        """Checks relative humidity validity."""
        if humidity_pct is None:
            return None
        if humidity_pct < self.min_humidity_pct:
            return f"Humidity {humidity_pct}% cannot be negative"
        if humidity_pct > self.max_humidity_pct and not self.allow_supersaturation:
            return f"Humidity {humidity_pct}% exceeds 100% without supersaturation flag enabled"
        return None

    def check_wind_speed(self, wind_speed_kmh: Optional[float]) -> Optional[str]:
        """Checks wind speed validity."""
        if wind_speed_kmh is None:
            return None
        if wind_speed_kmh < self.min_wind_speed_kmh:
            return f"Wind speed {wind_speed_kmh} km/h cannot be negative"
        if wind_speed_kmh > self.max_wind_speed_kmh:
            return f"Wind speed {wind_speed_kmh} km/h exceeds maximum physical plausible limit {self.max_wind_speed_kmh}"
        return None

    def check_rainfall(self, rainfall_mm: Optional[float]) -> Optional[str]:
        """Checks rainfall accumulation validity."""
        if rainfall_mm is None:
            return None
        if rainfall_mm < self.min_rainfall_mm:
            return f"Rainfall {rainfall_mm} mm cannot be negative"
        if rainfall_mm > self.max_rainfall_hourly_mm:
            return f"Hourly rainfall {rainfall_mm} mm exceeds plausible limit {self.max_rainfall_hourly_mm}"
        return None

    def check_pressure(self, pressure_hpa: Optional[float]) -> Optional[str]:
        """Checks barometric pressure validity."""
        if pressure_hpa is None:
            return None
        if pressure_hpa < self.min_pressure_hpa or pressure_hpa > self.max_pressure_hpa:
            return f"Pressure {pressure_hpa} hPa outside physical limits [{self.min_pressure_hpa}, {self.max_pressure_hpa}]"
        return None
