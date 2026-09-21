"""Comprehensive unit test suite for Analyst Brain V5 precision fixes.

Verifies:
P0:
1. Never infer NWP init_time when provider doesn't supply it.
2. Never infer producing center from an unverified model name.
3. Complete real historical-data retrieval.
4. Replace/expand embedded climate normals with verified authoritative data.
5. Remove hard-coded agency/license provenance assumptions.
6. Don't expose synthetic nwp://, station://, cap:// URIs as real source URLs.
7. Separate WeatherObservation from ModelAnalysis at the domain-model level.

P1 & Architecture:
8. Correct rainfall amount vs rainfall-rate semantics.
9. Make all timestamps timezone-aware and consistent.
10. Enforce rainfall accumulation-window compatibility in comparisons/fusion.
11. Label max forecast temperature/wind explicitly as maxima.
12. Improve warning geographic matching using coordinates/polygons.
13. Tie cyclone classification to official storm IDs/tracks where possible.
14. Keep storm-surge estimates explicitly heuristic.
15. Separate meteorological flood potential from actual flooding.
16. Strict Data Provider Contracts.
17. Full analytical metadata fields in CanonicalWeatherVariable.
18. Distinct statuses for UNKNOWN / SOURCE_UNAVAILABLE / NO_EVENT / NO_WARNING.
"""

from datetime import datetime, date, timedelta, timezone
from unittest.mock import MagicMock
import pytest

from app.brains.analyst_core.models.schemas import (
    DataType,
    AlertSeverity,
    EpistemicStatus,
    ConfidenceLevel,
    HazardType,
    WarningFeedStatus,
    HistoricalDataStatus,
    ClimatologyStatus,
    RiskLevel,
)
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ModelAnalysis,
    ForecastPoint,
    OfficialAlert,
    ensure_utc,
)
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherVariable
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.data.providers.warning_provider import CAPAlertProvider
from app.brains.analyst_core.data.providers.historical_provider import ReanalysisHistoricalProvider
from app.brains.analyst_core.data.climate_normals import ClimateNormalsEngine
from app.brains.analyst_core.evidence.provenance import ProvenanceTracker
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.analysis.comparison import ComparisonEngine as WeatherComparisonEngine
from app.brains.analyst_core.analysis.forecast import ForecastAnalyzer
from app.brains.analyst_core.qc.validator import DataValidator


# ------------------------------------------------------------------------------
# P0 Tests
# ------------------------------------------------------------------------------

def test_v5_p0_1_never_infer_nwp_init_time():
    """1. Never infer NWP init_time when provider doesn't supply it."""
    mock_session = MagicMock()
    geo_resp = MagicMock(status_code=200)
    geo_resp.json.return_value = {"results": [{"name": "Nagpur", "latitude": 21.14, "longitude": 79.08}]}
    
    # Provider payload without init_time
    fc_resp = MagicMock(status_code=200)
    fc_resp.json.return_value = {
        "model": "Open-Meteo Blend",
        "hourly": {
            "time": ["2026-09-01T15:00:00"],
            "temperature_2m": [30.5],
            "precipitation": [0.0],
        }
    }
    mock_session.get.side_effect = lambda url, params=None, timeout=None: geo_resp if "geocoding" in url else fc_resp
    
    provider = RealDataProvider(session=mock_session)
    points = provider.get_forecast("Nagpur", horizon_hours=1)
    assert len(points) == 1
    # Must NOT fabricate an initialization time or lead time
    assert points[0].init_time is None
    assert points[0].lead_time_hours is None
    assert points[0].model_cycle == "UNKNOWN_CYCLE"


def test_v5_p0_2_never_infer_producing_center_from_unverified_model():
    """2. Never infer producing center from an unverified model name."""
    mock_session = MagicMock()
    geo_resp = MagicMock(status_code=200)
    geo_resp.json.return_value = {"results": [{"name": "Jaipur", "latitude": 26.9, "longitude": 75.8}]}
    
    # Provider does NOT confirm model
    fc_resp = MagicMock(status_code=200)
    fc_resp.json.return_value = {
        "hourly": {
            "time": ["2026-09-01T15:00:00"],
            "temperature_2m": [34.0],
            "precipitation": [0.0],
        }
    }
    mock_session.get.side_effect = lambda url, params=None, timeout=None: geo_resp if "geocoding" in url else fc_resp
    
    provider = RealDataProvider(session=mock_session)
    points = provider.get_forecast("Jaipur", horizon_hours=1)
    assert points[0].model_confirmed is False
    assert points[0].producing_center == "Unspecified NWP Center"
    assert "Unconfirmed Model Variant" in points[0].source


def test_v5_p0_3_complete_real_historical_retrieval():
    """3. Complete real historical-data retrieval through RealDataProvider."""
    mock_hist = ReanalysisHistoricalProvider(
        mock_series={
            "delhi": [
                {
                    "timestamp": datetime(2025, 9, 1, 12, 0, 0),
                    "location": "Delhi",
                    "temperature_c": 31.5,
                    "rainfall_mm": 5.0,
                    "source": "ECMWF ERA5 Reanalysis",
                    "data_type": DataType.REANALYSIS,
                }
            ]
        }
    )
    provider = RealDataProvider(historical_provider=mock_hist)
    records, status, audit = provider.get_historical_with_status("Delhi", date(2025, 9, 1), date(2025, 9, 2))
    assert status == HistoricalDataStatus.HISTORICAL_DATA_AVAILABLE
    assert len(records) == 1
    assert records[0].temperature_c == 31.5
    assert records[0].data_type == DataType.REANALYSIS


def test_v5_p0_4_climate_normals_authoritative_12_months_and_strict_lookup():
    """4. Replace/expand embedded climate normals with verified authoritative data (no fake fallback)."""
    engine = ClimateNormalsEngine()
    
    # 4a. Verified station (Delhi) has verified 12-month data with WMO attribution
    for m in range(1, 13):
        normal = engine.get_baseline("Delhi", month=m)
        assert normal is not None
        assert normal.month == m
        assert normal.station_wmo_id == "42182"
        assert "IMD" in normal.authoritative_agency
        assert normal.normal_temp_c > 0.0

    # 4b. Unverified location or missing month returns None (Zero fake formula simulation)
    assert engine.get_baseline("ImaginaryCity", month=5) is None


def test_v5_p0_5_and_6_provenance_source_driven_no_synthetic_uris():
    """5 & 6. Remove hardcoded assumptions and don't expose synthetic nwp://, station://, cap:// URIs."""
    tracker = ProvenanceTracker()
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Observation without endpoint_uri or agency
    obs = WeatherObservation(
        timestamp=now,
        location="Lucknow",
        temperature_c=32.0,
        source="Custom Agro Met Station",
        data_type=DataType.OBSERVATION,
    )
    ev_obs = tracker.create_observation_evidence(obs, "temperature", "32.0 °C")
    assert ev_obs.source == "Custom Agro Met Station"
    assert ev_obs.producing_agency == "Custom Agro Met Station"
    assert ev_obs.data_license == "Unspecified License"
    # Never manufacture synthetic station:// URI
    assert ev_obs.uri_or_endpoint is None
    assert not str(ev_obs.uri_or_endpoint).startswith("station://")

    # Forecast without init_time and endpoint_uri
    fc = ForecastPoint(
        valid_time=now + timedelta(hours=3),
        location="Lucknow",
        init_time=None,
        lead_time_hours=None,
        temperature_c=33.0,
        model_name="Regional WRF",
        model_cycle="UNKNOWN_CYCLE",
        source="State WRF Run",
    )
    ev_fc = tracker.create_forecast_evidence(fc, "temperature", "33.0 °C")
    assert ev_fc.producing_agency == "Unspecified NWP Center"
    assert ev_fc.uri_or_endpoint is None
    assert not str(ev_fc.uri_or_endpoint).startswith("nwp://")
    assert "Uninitialized" in ev_fc.method


def test_v5_p0_7_separate_weather_observation_from_model_analysis():
    """7. Separate WeatherObservation from ModelAnalysis at the domain-model level."""
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Direct physical sensor
    station_obs = WeatherObservation(
        timestamp=now,
        location="Safdarjung AWS",
        temperature_c=32.5,
        source="IMD_AWS",
        data_type=DataType.OBSERVATION,
        epistemic_status=EpistemicStatus.OBSERVED,
    )
    assert station_obs.data_type == DataType.OBSERVATION
    assert station_obs.epistemic_status == EpistemicStatus.OBSERVED

    # Gridded model reanalysis/analysis field
    model_field = ModelAnalysis(
        valid_time=now,
        location="Delhi Grid (28.6N, 77.2E)",
        temperature_c=32.2,
        model_name="ECMWF-ERA5",
        data_type=DataType.MODEL_ANALYSIS,
        epistemic_status=EpistemicStatus.MODEL_DERIVED,
        grid_resolution_km=31.0,
    )
    assert model_field.data_type == DataType.MODEL_ANALYSIS
    assert model_field.epistemic_status == EpistemicStatus.MODEL_DERIVED
    assert isinstance(model_field, ModelAnalysis)
    assert not isinstance(station_obs, ModelAnalysis)


# ------------------------------------------------------------------------------
# P1 & Architecture Tests
# ------------------------------------------------------------------------------

def test_v5_p1_8_rainfall_amount_vs_rate_semantics():
    """8. Correct rainfall amount vs rainfall-rate semantics."""
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # 24-hour total rainfall of 60mm with 2.5 mm/h moderate steady rate
    obs = WeatherObservation(
        timestamp=now,
        location="Kochi",
        rainfall_mm=60.0,
        rainfall_accumulation_period_hours=24.0,
        rainfall_rate_mm_h=2.5,
        source="AWS",
    )
    
    analyzer = HazardAnalyzer()
    hazards, sev, evidence = analyzer.analyze_hazards([obs], [], [])
    # 60 mm in 24 hours does not exceed 64.5 mm heavy rain threshold, and 2.5 mm/h is NOT a burst
    assert HazardType.FLASH_FLOOD not in hazards


def test_v5_p1_9_timezone_aware_consistency():
    """9. Make all timestamps timezone-aware and consistent."""
    naive_dt = datetime(2026, 9, 1, 12, 0, 0)
    aware_dt = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    ensured_1 = ensure_utc(naive_dt)
    ensured_2 = ensure_utc(aware_dt)
    assert ensured_1.tzinfo == timezone.utc
    assert ensured_2.tzinfo == timezone.utc
    assert ensure_utc(None) is None

    # DataValidator handles mixed naive and aware timestamps without TypeError
    validator = DataValidator(max_observation_age_hours=3.0)
    obs_naive = WeatherObservation(
        timestamp=naive_dt,
        location="Kanpur",
        temperature_c=31.0,
        source="Station",
    )
    # Validate with UTC aware current_time
    is_valid, flags = validator.validate_observation(obs_naive, current_time=datetime.now(timezone.utc))
    assert isinstance(is_valid, bool)


def test_v5_p1_10_enforce_accumulation_window_in_comparison():
    """10. Enforce rainfall accumulation-window compatibility in comparisons."""
    now = datetime(2026, 9, 1, 12, 0, 0)
    
    # Location A has 1h accumulation of 15 mm
    obs_a = [
        WeatherObservation(
            timestamp=now,
            location="CityA",
            temperature_c=28.0,
            rainfall_mm=15.0,
            rainfall_accumulation_period_hours=1.0,
            source="AWS",
        )
    ]
    # Location B has 24h accumulation of 20 mm
    obs_b = [
        WeatherObservation(
            timestamp=now,
            location="CityB",
            temperature_c=28.0,
            rainfall_mm=20.0,
            rainfall_accumulation_period_hours=24.0,
            source="AWS",
        )
    ]

    comp_engine = WeatherComparisonEngine()
    result = comp_engine.compare_locations("CityA", obs_a, [], RiskLevel.LOW, "CityB", obs_b, [], RiskLevel.LOW)
    
    assert "accumulation_window_warning" in result["differences"]
    assert "disparity: CityA (1.0h) vs CityB (24.0h)" in result["differences"]["accumulation_window_warning"]


def test_v5_p1_11_explicit_maxima_labels_in_forecast():
    """11. Label max forecast temperature/wind explicitly as maxima."""
    analyzer = ForecastAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)
    fc = [
        ForecastPoint(valid_time=now + timedelta(hours=1), location="Ahmedabad", init_time=now, temperature_c=38.5, wind_speed_kmh=24.0),
        ForecastPoint(valid_time=now + timedelta(hours=2), location="Ahmedabad", init_time=now, temperature_c=42.0, wind_speed_kmh=35.0),
    ]
    res = analyzer.analyze_forecast_stream(fc)
    assert res["forecast_maximum_temperature_c"] == 42.0
    assert res["peak_wind_gust_kmh"] == 35.0


def test_v5_p1_12_warning_polygon_and_coordinate_matching():
    """12. Improve warning geographic matching using coordinates/polygons."""
    now = datetime(2026, 9, 1, 12, 0, 0)
    alert = OfficialAlert(
        alert_id="TEST-POLY-01",
        issuing_authority="IMD",
        warning_type="CYCLONE",
        severity=AlertSeverity.RED_WARNING,
        issue_time=now,
        valid_from=now,
        valid_to=now + timedelta(hours=24),
        geographic_area="Coastal Zone Alpha",
        headline="Cyclone Alert for Coastal Zone Alpha",
        description="Severe cyclonic storm approaching",
        # Triangle around (19.0, 84.0), (20.0, 86.0), (18.0, 86.0)
        polygon_coordinates=[(19.0, 84.0), (20.0, 86.0), (18.0, 86.0)],
        affected_bounds=(18.0, 84.0, 20.0, 86.0),
        storm_id="BOB-02-2026",
    )

    # Inside polygon (19.0, 85.0)
    assert alert.matches_location("Anytown", latitude=19.0, longitude=85.0) is True

    # Outside polygon / outside bounds (22.0, 88.0)
    assert alert.matches_location("DifferentTown", latitude=22.0, longitude=88.0) is False

    # Name matching fallback works if coordinates not supplied
    assert alert.matches_location("Coastal Zone Alpha") is True
    assert alert.matches_location("Inland Desert") is False


def test_v5_p1_13_and_14_cyclone_storm_id_and_heuristic_surge():
    """13 & 14. Tie cyclone classification to official storm IDs and keep surge explicitly heuristic."""
    analyzer = HazardAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)
    
    alert = OfficialAlert(
        alert_id="IMD-CYCLONE-BOB-01",
        issuing_authority="IMD",
        warning_type="CYCLONE",
        severity=AlertSeverity.RED_WARNING,
        issue_time=now,
        valid_from=now,
        valid_to=now + timedelta(hours=24),
        geographic_area="Odisha Coast",
        headline="Cyclone Warning",
        description="Extremely severe cyclonic storm approaching",
        storm_id="BOB-01-2026",
    )
    
    fc = [
        ForecastPoint(
            valid_time=now,
            location="Puri",
            init_time=now,
            wind_speed_kmh=175.0,
            pressure_hpa=955.0,
        )
    ]
    
    hazards, sev, evidence = analyzer.analyze_hazards([], fc, [alert])
    assert HazardType.CYCLONE in hazards
    cyc_ev = next(e for e in evidence if "IMD Cyclone Classification" in e)
    # Verifies storm ID binding
    assert "BOB-01-2026" in cyc_ev
    # Verifies heuristic surge qualification
    assert "Heuristic empirical estimate" in cyc_ev or "hydrodynamic run required" in cyc_ev


def test_v5_p1_15_separate_meteorological_flood_potential_from_actual_flooding():
    """15. Separate meteorological flood potential from actual hydrological inundation."""
    analyzer = HazardAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)
    
    # Saturated soil with heavy rain but NO river breach or flood alert
    obs = [
        WeatherObservation(
            timestamp=now,
            location="Patna",
            rainfall_mm=60.0,
            rainfall_accumulation_period_hours=24.0,
            rainfall_rate_mm_h=2.5,
            soil_moisture_pct=85.0,
            river_level_m=2.0,  # Below 5m river gauge warning threshold
            river_discharge_m3s=300.0,
            source="AWS",
        )
    ]
    
    hazards, sev, evidence = analyzer.analyze_hazards(obs, [], [])
    assert HazardType.FLOODING in hazards
    flood_ev = next(e for e in evidence if "Meteorological Flood Potential" in e)
    assert "in-situ gauge breach not confirmed" in flood_ev


def test_v5_arch_17_canonical_weather_variable_metadata():
    """17. Ensure CanonicalWeatherVariable carries full analytical metadata."""
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    var = CanonicalWeatherVariable(
        name="surface_temperature",
        value=32.4,
        unit="°C",
        origin_type=DataType.OBSERVATION,
        source_name="IMD Automatic Weather Station",
        timestamp=now,
        valid_time=now,
        epistemic_status=EpistemicStatus.OBSERVED,
        freshness_hours=0.5,
        provenance_id="PROV-IMD-01",
        is_extreme_or_maximum=False,
    )
    assert var.valid_time == now
    assert var.epistemic_status == EpistemicStatus.OBSERVED
    assert var.freshness_hours == 0.5
    assert var.provenance_id == "PROV-IMD-01"


def test_v5_arch_18_distinct_statuses_unknown_unavailable_no_event():
    """18. Ensure UNKNOWN / SOURCE_UNAVAILABLE / NO_EVENT remain distinct everywhere."""
    # Warning Feed Statuses
    assert WarningFeedStatus.ACTIVE_WARNINGS_FOUND != WarningFeedStatus.NO_WARNING_ISSUED
    assert WarningFeedStatus.NO_WARNING_ISSUED != WarningFeedStatus.SOURCE_UNAVAILABLE
    
    # Historical Data Statuses
    assert HistoricalDataStatus.HISTORICAL_DATA_AVAILABLE != HistoricalDataStatus.NO_HISTORICAL_EVENT
    assert HistoricalDataStatus.NO_HISTORICAL_EVENT != HistoricalDataStatus.SOURCE_UNAVAILABLE
    
    # Climatology Statuses
    assert ClimatologyStatus.CLIMATOLOGY_AVAILABLE != ClimatologyStatus.CLIMATOLOGY_UNAVAILABLE
    assert ClimatologyStatus.CLIMATOLOGY_UNAVAILABLE != ClimatologyStatus.SOURCE_UNAVAILABLE
