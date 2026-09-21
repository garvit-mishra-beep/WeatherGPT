"""Unit tests for strengthened flood, cyclone, and lightning methodology."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import HazardType
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer


def test_antecedent_precipitation_index():
    """Verifies Antecedent Precipitation Index (API) decay calculation."""
    analyzer = HazardAnalyzer()
    daily_rain = [20.0, 40.0, 60.0]  # sequential days
    api = analyzer.calculate_antecedent_precipitation_index(daily_rain, decay_factor=0.85)
    # API = 0.85^1 * 60 + 0.85^2 * 40 + 0.85^3 * 20 = 51.0 + 28.9 + 12.28 = 92.18 -> 92.2
    assert 90.0 <= api <= 95.0


def test_imd_cyclone_classification_and_surge():
    """Verifies 8-stage IMD tropical cyclone scale and storm surge estimation."""
    analyzer = HazardAnalyzer()

    # Very Severe Cyclonic Storm (118-166 km/h)
    vscs = analyzer.classify_cyclone(max_wind_kmh=130.0, min_pressure_hpa=970.0)
    assert "Very Severe Cyclonic Storm" in vscs["stage"]
    assert vscs["severity_score"] == 88.0
    assert vscs["central_pressure_deficit_hpa"] == 40.0
    assert "2.0m - 3.5m" in vscs["estimated_storm_surge"]

    # Super Cyclone (>= 222 km/h)
    sucs = analyzer.classify_cyclone(max_wind_kmh=230.0, min_pressure_hpa=920.0)
    assert "Super Cyclonic Storm" in sucs["stage"]
    assert sucs["severity_score"] == 100.0
    assert "> 5.0m" in sucs["estimated_storm_surge"]


def test_flash_flood_hourly_burst_hazard():
    """Verifies that high hourly rainfall burst (>50 mm/h) triggers flood hazard."""
    analyzer = HazardAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)
    obs = [
        WeatherObservation(
            timestamp=now,
            location="Dehradun",
            rainfall_mm=55.0,  # Intense burst in 1 hour
            source="AWS",
        )
    ]
    hazards, sev, evidence = analyzer.analyze_hazards(obs, [], [])
    assert HazardType.FLOODING in hazards
    assert sev >= 75.0
    assert any("Burst rain" in e or "Elevated flood potential" in e for e in evidence)


def test_convective_lightning_cape_and_lifted_index():
    """Verifies that high CAPE and negative Lifted Index trigger severe convective hazards."""
    analyzer = HazardAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)
    fc = [
        ForecastPoint(
            valid_time=now,
            location="Kolkata",
            init_time=now,
            cape_jkg=2800.0,  # Extreme CAPE > 2500
            lifted_index=-7.0,  # Extremely unstable < -6
            temperature_c=34.0,
            model_name="ECMWF-IFS",
        )
    ]
    hazards, sev, evidence = analyzer.analyze_hazards([], fc, [])
    assert HazardType.THUNDERSTORM in hazards
    assert HazardType.LIGHTNING in hazards
    assert sev >= 85.0
    assert any("Severe convective" in e for e in evidence)


def test_hazard_alerts_and_cyclone_stages():
    """Tests alert severity integration and intermediate cyclone stages in HazardAnalyzer."""
    from app.brains.analyst_core.models.schemas import AlertSeverity, DataType
    from app.brains.analyst_core.models.weather_data import OfficialAlert

    analyzer = HazardAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)

    # 1. Depression & Deep Depression stages
    dd = analyzer.classify_cyclone(max_wind_kmh=55.0, min_pressure_hpa=1005.0)
    assert dd["stage"] == "Deep Depression (DD)"
    assert dd["severity_score"] == 50.0

    d = analyzer.classify_cyclone(max_wind_kmh=35.0, min_pressure_hpa=1008.0)
    assert d["stage"] == "Depression (D)"
    assert d["severity_score"] == 35.0

    lpa = analyzer.classify_cyclone(max_wind_kmh=20.0, min_pressure_hpa=1009.0)
    assert lpa["stage"] == "Low Pressure Area (LPA)"
    assert lpa["severity_score"] == 20.0

    # 2. Official Alerts Integration (RED, ORANGE, YELLOW)
    alerts = [
        OfficialAlert(
            alert_id="ALT-RED",
            issuing_authority="IMD",
            warning_type="FLASH_FLOOD",
            severity=AlertSeverity.RED_WARNING,
            issue_time=now,
            valid_from=now,
            valid_to=now,
            geographic_area="Goa",
            headline="Red Warning: Flash flood inundation",
            description="",
        ),
        OfficialAlert(
            alert_id="ALT-ORANGE",
            issuing_authority="IMD",
            warning_type="GALE",
            severity=AlertSeverity.ORANGE_ALERT,
            issue_time=now,
            valid_from=now,
            valid_to=now,
            geographic_area="Goa",
            headline="Orange Alert: Gale force gusts",
            description="",
        ),
        OfficialAlert(
            alert_id="ALT-YELLOW",
            issuing_authority="IMD",
            warning_type="SQUALL",
            severity=AlertSeverity.YELLOW_WATCH,
            issue_time=now,
            valid_from=now,
            valid_to=now,
            geographic_area="Goa",
            headline="Yellow Watch: Squally weather",
            description="",
        ),
    ]

    hazards, sev, evidence = analyzer.analyze_hazards([], [], alerts)
    assert sev == 100.0
    assert any("OFFICIAL RED WARNING" in e for e in evidence)
    assert any("OFFICIAL ORANGE ALERT" in e for e in evidence)
    assert any("Official Yellow Watch" in e for e in evidence)
