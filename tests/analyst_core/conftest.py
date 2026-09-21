"""Pytest configuration and shared test fixtures."""

from datetime import datetime, timedelta, date
import pytest

from app.brains.analyst_core.models.schemas import DataType, AlertSeverity
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
    LocationMetadata,
)
from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain


@pytest.fixture
def fixed_now():
    """Fixed reference datetime for reproducible testing."""
    return datetime(2026, 9, 1, 12, 0, 0)


@pytest.fixture
def nominal_obs(fixed_now):
    """Standard valid observation."""
    return WeatherObservation(
        timestamp=fixed_now - timedelta(minutes=30),
        location="Gwalior",
        temperature_c=32.0,
        humidity_pct=60.0,
        wind_speed_kmh=15.0,
        wind_gust_kmh=22.0,
        rainfall_mm=5.0,
        pressure_hpa=1008.0,
        visibility_m=7000.0,
        data_type=DataType.OBSERVATION,
        source="IMD Station Gwalior",
        retrieval_timestamp=fixed_now,
        is_synthetic=False,
    )


@pytest.fixture
def heavy_rain_obs(fixed_now):
    """Observation with heavy rainfall exceeding IMD threshold."""
    return WeatherObservation(
        timestamp=fixed_now - timedelta(minutes=15),
        location="Mumbai",
        temperature_c=27.0,
        humidity_pct=92.0,
        wind_speed_kmh=45.0,
        wind_gust_kmh=65.0,
        rainfall_mm=125.0,  # Very heavy rain
        pressure_hpa=998.0,
        visibility_m=1500.0,
        data_type=DataType.OBSERVATION,
        source="IMD Colaba Observatory",
        retrieval_timestamp=fixed_now,
        is_synthetic=False,
    )


@pytest.fixture
def heatwave_obs(fixed_now):
    """Observation during a severe heatwave."""
    return WeatherObservation(
        timestamp=fixed_now - timedelta(minutes=20),
        location="Delhi",
        temperature_c=46.2,  # Severe heatwave
        humidity_pct=25.0,
        wind_speed_kmh=18.0,
        wind_gust_kmh=25.0,
        rainfall_mm=0.0,
        pressure_hpa=1002.0,
        visibility_m=5000.0,
        data_type=DataType.OBSERVATION,
        source="IMD Safdarjung Observatory",
        retrieval_timestamp=fixed_now,
        is_synthetic=False,
    )


@pytest.fixture
def nominal_forecast(fixed_now):
    """Sequence of NWP forecast points."""
    return [
        ForecastPoint(
            valid_time=fixed_now + timedelta(hours=i),
            location="Gwalior",
            init_time=fixed_now,
            temperature_c=30.0 + (i % 5),
            precipitation_prob_pct=20.0,
            rainfall_mm=0.0,
            wind_speed_kmh=12.0,
            model_name="ECMWF-IFS",
            data_type=DataType.FORECAST_NWP,
            source="ECMWF",
            retrieval_timestamp=fixed_now,
            is_synthetic=False,
        )
        for i in range(1, 25, 3)
    ]


@pytest.fixture
def official_red_alert(fixed_now):
    """Official IMD Red Warning alert."""
    return OfficialAlert(
        alert_id="IMD-2026-RED-001",
        issuing_authority="India Meteorological Department (IMD)",
        warning_type="EXTREMELY_HEAVY_RAINFALL",
        severity=AlertSeverity.RED_WARNING,
        issue_time=fixed_now - timedelta(hours=2),
        valid_from=fixed_now,
        valid_to=fixed_now + timedelta(hours=24),
        geographic_area="Mumbai, Thane and Palghar",
        headline="Red Warning: Extremely heavy rainfall with localized inundation expected",
        description="Active monsoon surge likely to produce rainfall exceeding 204.4 mm in 24 hours.",
        recommended_precautions=[
            "Avoid non-essential travel in waterlogged sectors",
            "Follow municipal disaster management advisories",
        ],
        is_verified=True,
        is_synthetic=False,
        data_type=DataType.OFFICIAL_WARNING,
    )


@pytest.fixture
def synthetic_provider():
    """Synthetic provider instance."""
    return SyntheticProvider()


@pytest.fixture
def mocked_real_provider(fixed_now):
    """RealDataProvider with mock geocoding, observations, and forecasts for offline testing."""
    mock_responses = {
        "geo:gwalior": {
            "name": "Gwalior",
            "latitude": 26.2183,
            "longitude": 78.1828,
            "country": "IN",
            "timezone": "Asia/Kolkata",
            "elevation_m": 197.0,
        },
        "geo:delhi": {
            "name": "Delhi",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "country": "IN",
            "timezone": "Asia/Kolkata",
            "elevation_m": 216.0,
        },
        "geo:mumbai": {
            "name": "Mumbai",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "country": "IN",
            "timezone": "Asia/Kolkata",
            "elevation_m": 14.0,
        },
        "geo:pune": {
            "name": "Pune",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "country": "IN",
            "timezone": "Asia/Kolkata",
            "elevation_m": 560.0,
        },
        # Observations
        "obs:gwalior": [
            {
                "timestamp": fixed_now.isoformat(),
                "location": "Gwalior",
                "temperature_c": 32.5,
                "humidity_pct": 58.0,
                "wind_speed_kmh": 14.0,
                "wind_gust_kmh": 20.0,
                "rainfall_mm": 2.0,
                "pressure_hpa": 1009.5,
                "data_type": "MODEL_ANALYSIS",
                "source": "Open-Meteo NWP Surface Analysis",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
        ],
        "obs:delhi": [
            {
                "timestamp": fixed_now.isoformat(),
                "location": "Delhi",
                "temperature_c": 36.0,
                "humidity_pct": 45.0,
                "wind_speed_kmh": 16.0,
                "wind_gust_kmh": 22.0,
                "rainfall_mm": 0.0,
                "pressure_hpa": 1007.2,
                "data_type": "MODEL_ANALYSIS",
                "source": "Open-Meteo NWP Surface Analysis",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
        ],
        "obs:mumbai": [
            {
                "timestamp": fixed_now.isoformat(),
                "location": "Mumbai",
                "temperature_c": 28.5,
                "humidity_pct": 88.0,
                "wind_speed_kmh": 35.0,
                "wind_gust_kmh": 50.0,
                "rainfall_mm": 75.0,
                "pressure_hpa": 999.0,
                "data_type": "MODEL_ANALYSIS",
                "source": "Open-Meteo NWP Surface Analysis",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
        ],
        # Forecasts
        "fc:gwalior:24": [
            {
                "valid_time": (fixed_now + timedelta(hours=i)).isoformat(),
                "location": "Gwalior",
                "init_time": fixed_now.isoformat(),
                "temperature_c": 30.0 + (i % 4),
                "precipitation_prob_pct": 20.0,
                "rainfall_mm": 0.0,
                "wind_speed_kmh": 12.0,
                "humidity_pct": 55.0,
                "model_name": "ECMWF-IFS",
                "data_type": "FORECAST_NWP",
                "source": "ECMWF",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
            for i in range(1, 25, 3)
        ],
        "fc:gwalior:48": [
            {
                "valid_time": (fixed_now + timedelta(hours=i)).isoformat(),
                "location": "Gwalior",
                "init_time": fixed_now.isoformat(),
                "temperature_c": 30.0 + (i % 4),
                "precipitation_prob_pct": 25.0,
                "rainfall_mm": 0.0,
                "wind_speed_kmh": 12.0,
                "humidity_pct": 55.0,
                "model_name": "ECMWF-IFS",
                "data_type": "FORECAST_NWP",
                "source": "ECMWF",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
            for i in range(1, 49, 3)
        ],
        "fc:delhi:24": [
            {
                "valid_time": (fixed_now + timedelta(hours=i)).isoformat(),
                "location": "Delhi",
                "init_time": fixed_now.isoformat(),
                "temperature_c": 34.0 + (i % 5),
                "precipitation_prob_pct": 10.0,
                "rainfall_mm": 0.0,
                "wind_speed_kmh": 15.0,
                "humidity_pct": 40.0,
                "model_name": "ECMWF-IFS",
                "data_type": "FORECAST_NWP",
                "source": "ECMWF",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
            for i in range(1, 25, 3)
        ],
        "fc:delhi:48": [
            {
                "valid_time": (fixed_now + timedelta(hours=i)).isoformat(),
                "location": "Delhi",
                "init_time": fixed_now.isoformat(),
                "temperature_c": 34.0 + (i % 5),
                "precipitation_prob_pct": 15.0,
                "rainfall_mm": 0.0,
                "wind_speed_kmh": 15.0,
                "humidity_pct": 40.0,
                "model_name": "ECMWF-IFS",
                "data_type": "FORECAST_NWP",
                "source": "ECMWF",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
            for i in range(1, 49, 3)
        ],
        "fc:mumbai:24": [
            {
                "valid_time": (fixed_now + timedelta(hours=i)).isoformat(),
                "location": "Mumbai",
                "init_time": fixed_now.isoformat(),
                "temperature_c": 28.0,
                "precipitation_prob_pct": 90.0,
                "rainfall_mm": 25.0,
                "wind_speed_kmh": 40.0,
                "humidity_pct": 90.0,
                "model_name": "ECMWF-IFS",
                "data_type": "FORECAST_NWP",
                "source": "ECMWF",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
            for i in range(1, 25, 3)
        ],
        "fc:mumbai:48": [
            {
                "valid_time": (fixed_now + timedelta(hours=i)).isoformat(),
                "location": "Mumbai",
                "init_time": fixed_now.isoformat(),
                "temperature_c": 28.0,
                "precipitation_prob_pct": 95.0,
                "rainfall_mm": 35.0,
                "wind_speed_kmh": 45.0,
                "humidity_pct": 92.0,
                "model_name": "ECMWF-IFS",
                "data_type": "FORECAST_NWP",
                "source": "ECMWF",
                "retrieval_timestamp": fixed_now.isoformat(),
                "is_synthetic": False,
            }
            for i in range(1, 49, 3)
        ],
    }
    return RealDataProvider(mock_http_responses=mock_responses)
