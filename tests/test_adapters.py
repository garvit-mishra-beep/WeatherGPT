"""B5 — Meteorological Data Ingestion & Adapters Test Suite.

Tests cover:
1. IMD OASIS CAP XML Parsing & Severity Immutability
2. GFS 0.25° NWP Parameter Normalization & Grid Snapping
3. Open-Meteo Payload Normalization & Error Handling
4. Weather Provider Strategy & Fallback Cascade
5. Provenance & Authority Invariant Verification
"""

import json
from pathlib import Path
import pytest
import httpx

from app.adapters import (
    CAPParseError,
    GFSNWPProvider,
    IMDWarningProvider,
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    OpenMeteoProvider,
    ProviderAuthority,
    ProviderQuality,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
    WeatherProviderManager,
    classify_imd_rainfall,
    fahrenheit_to_celsius,
    kelvin_to_celsius,
    map_cap_severity_to_warning_level,
    ms_to_kmh,
    normalize_gfs_grid_message,
    normalize_open_meteo_forecast,
    normalize_open_meteo_observation,
    pa_to_hpa,
    parse_cap_xml,
    snap_to_gfs_grid,
    uv_wind_to_speed_and_direction,
)
from app.adapters.gfs.models import GFSAtmosphericParameters, GFSGridMessage
from app.adapters.open_meteo.models import OpenMeteoForecastResponse
from app.config import Settings
from app.contracts.enums import WarningLevel

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "adapters"


# ============================================================================
# 1. Normalization & Physical Conversions
# ============================================================================

def test_physical_unit_conversions():
    # Kelvin -> Celsius
    assert kelvin_to_celsius(273.15) == 0.0
    assert kelvin_to_celsius(303.15) == 30.0

    # Fahrenheit -> Celsius
    assert fahrenheit_to_celsius(32.0) == 0.0
    assert fahrenheit_to_celsius(212.0) == 100.0

    # m/s -> km/h
    assert ms_to_kmh(10.0) == 36.0
    assert ms_to_kmh(0.0) == 0.0

    # Pa -> hPa
    assert pa_to_hpa(101325.0) == 1013.25
    assert pa_to_hpa(100000.0) == 1000.0


def test_uv_wind_vector_calculation():
    # Calm wind (u=0, v=0) -> speed=0, dir=0
    spd_ms, spd_kmh, wdir = uv_wind_to_speed_and_direction(0.0, 0.0)
    assert spd_ms == 0.0
    assert spd_kmh == 0.0

    # Pure Westerly wind (u > 0, v = 0) -> coming from 270° (West)
    spd_ms, spd_kmh, wdir = uv_wind_to_speed_and_direction(10.0, 0.0)
    assert spd_ms == 10.0
    assert spd_kmh == 36.0
    assert wdir == 270.0

    # Pure Southerly wind (u = 0, v > 0) -> coming from 180° (South)
    spd_ms, spd_kmh, wdir = uv_wind_to_speed_and_direction(0.0, 10.0)
    assert wdir == 180.0


def test_imd_rainfall_classification_categories():
    assert classify_imd_rainfall(0.0) == "no_rain"
    assert classify_imd_rainfall(1.5) == "very_light_rain"
    assert classify_imd_rainfall(10.0) == "light_rain"
    assert classify_imd_rainfall(35.0) == "moderate_rain"
    assert classify_imd_rainfall(85.0) == "heavy_rain"
    assert classify_imd_rainfall(150.0) == "very_heavy_rain"
    assert classify_imd_rainfall(250.0) == "extremely_heavy_rain"


# ============================================================================
# 2. IMD OASIS CAP Alert Parsing
# ============================================================================

def test_parse_valid_red_alert_cap():
    xml_path = FIXTURES_DIR / "imd_cap_red_alert.xml"
    xml_text = xml_path.read_text(encoding="utf-8")

    alerts = parse_cap_xml(xml_text)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.alert_id == "IMD-NDMA-2026-GJ-00821_0"
    assert alert.sender == "imd_hq_newdelhi@imd.gov.in"
    assert alert.warning_level == WarningLevel.RED
    assert alert.event_title == "Extremely Heavy Rainfall"
    assert alert.urgency == "Immediate"
    assert alert.severity == "Extreme"
    assert alert.area_description == "Surat District, Gujarat"
    assert len(alert.polygons) == 1
    assert "21.05,72.60" in alert.polygons[0]
    assert alert.geocodes == [{"PCODE": "IN-GJ-25"}]
    assert alert.is_official is True
    assert alert.quality == ProviderQuality.VALID


def test_parse_valid_orange_alert_cap():
    xml_path = FIXTURES_DIR / "imd_cap_orange_alert.xml"
    xml_text = xml_path.read_text(encoding="utf-8")

    alerts = parse_cap_xml(xml_text)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.warning_level == WarningLevel.ORANGE
    assert "Pune District" in alert.area_description
    assert alert.severity == "Severe"


def test_parse_multi_entry_cap_feed():
    xml_path = FIXTURES_DIR / "imd_cap_multi_feed.xml"
    xml_text = xml_path.read_text(encoding="utf-8")

    alerts = parse_cap_xml(xml_text)
    assert len(alerts) == 2
    assert alerts[0].warning_level == WarningLevel.YELLOW
    assert alerts[0].event_title == "Thunderstorm"
    assert alerts[1].warning_level == WarningLevel.GREEN
    assert alerts[1].event_title == "Clear Weather"


def test_parse_malformed_cap_xml_raises():
    xml_path = FIXTURES_DIR / "imd_cap_malformed.xml"
    xml_text = xml_path.read_text(encoding="utf-8")

    with pytest.raises(CAPParseError, match="Malformed CAP XML"):
        parse_cap_xml(xml_text)


def test_parse_missing_fields_cap_xml_raises():
    xml_path = FIXTURES_DIR / "imd_cap_missing_fields.xml"
    xml_text = xml_path.read_text(encoding="utf-8")

    with pytest.raises(CAPParseError, match="mandatory"):
        parse_cap_xml(xml_text)


def test_cap_severity_immutability():
    """Verify official warning levels are preserved exactly without alteration."""
    assert map_cap_severity_to_warning_level("Extreme") == WarningLevel.RED
    assert map_cap_severity_to_warning_level("Severe") == WarningLevel.ORANGE
    assert map_cap_severity_to_warning_level("Moderate") == WarningLevel.YELLOW
    assert map_cap_severity_to_warning_level("Minor") == WarningLevel.GREEN


# ============================================================================
# 3. GFS 0.25° NWP Data Extraction & Grid Snapping
# ============================================================================

def test_gfs_grid_snapping():
    # 23.12, 72.58 -> snaps to 23.00, 72.50 or 23.25, 72.50
    lat, lon = snap_to_gfs_grid(23.12, 72.58)
    assert lat == 23.0
    assert lon == 72.5

    lat2, lon2 = snap_to_gfs_grid(19.07, 72.87)
    assert lat2 == 19.0
    assert lon2 == 72.75


def test_normalize_gfs_grid_message():
    raw_msg = GFSGridMessage(
        cycle_time_iso="2026-08-30T00:00:00Z",
        forecast_hour=24,
        valid_time_iso="2026-08-31T00:00:00Z",
        latitude=23.0225,
        longitude=72.5714,
        variables=GFSAtmosphericParameters(
            tmp_2m_k=303.15,  # 30.0 °C
            rh_2m_pct=70.0,
            apcp_surface_kg_m2=15.2,
            ugrd_10m_ms=5.0,
            vgrd_10m_ms=0.0,
            gust_surface_ms=10.0,
            prmsl_pa=100600.0,  # 1006.0 hPa
            tcdc_pct=60.0,
        ),
    )

    nwp_point = normalize_gfs_grid_message(raw_msg)
    assert isinstance(nwp_point, NormalizedNWPGridPoint)
    assert nwp_point.temperature_2m_c == 30.0
    assert nwp_point.relative_humidity_2m_pct == 70.0
    assert nwp_point.accumulated_precip_mm == 15.2
    assert nwp_point.wind_speed_kmh == 18.0
    assert nwp_point.wind_direction_deg == 270.0
    assert nwp_point.wind_gust_kmh == 36.0
    assert nwp_point.pressure_msl_hpa == 1006.0
    assert nwp_point.total_cloud_cover_pct == 60.0
    assert nwp_point.grid_resolution_deg == 0.25
    assert nwp_point.quality == ProviderQuality.VALID


@pytest.mark.asyncio
async def test_gfs_client_get_grid_point():
    provider = GFSNWPProvider()
    point = await provider.get_grid_point(latitude=21.17, longitude=72.83, lead_hours=48)
    assert point.latitude == 21.25
    assert point.longitude == 72.75
    assert point.forecast_lead_hours == 48
    assert point.model_name == "GFS_0P25"
    await provider.close()


# ============================================================================
# 4. Open-Meteo Adapter Normalization
# ============================================================================

def test_normalize_open_meteo_payload():
    json_path = FIXTURES_DIR / "open_meteo_response.json"
    raw_dict = json.loads(json_path.read_text(encoding="utf-8"))
    resp = OpenMeteoForecastResponse(**raw_dict)

    # 1. Observation
    obs = normalize_open_meteo_observation(resp)
    assert isinstance(obs, NormalizedWeatherObservation)
    assert obs.latitude == 23.0225
    assert obs.longitude == 72.5714
    assert obs.temperature_c == 31.5
    assert obs.feels_like_c == 36.8
    assert obs.relative_humidity_pct == 68.0
    assert obs.precipitation_mm == 1.2
    assert obs.rain_intensity_category == "very_light_rain"
    assert obs.wind_speed_kmh == 14.5
    assert obs.surface_pressure_hpa == 1005.4
    assert obs.weather_condition == "slight_rain_showers"
    assert obs.authority == ProviderAuthority.SECONDARY

    # 2. Forecast
    fc = normalize_open_meteo_forecast(resp)
    assert isinstance(fc, NormalizedWeatherForecastPayload)
    assert len(fc.hourly) == 3
    assert len(fc.daily) == 3
    assert fc.daily[0].date_str == "2026-08-30"
    assert fc.daily[0].temp_max_c == 34.0
    assert fc.daily[0].temp_min_c == 26.2
    assert fc.daily[1].precipitation_sum_mm == 45.2
    assert fc.daily[1].rain_intensity_category == "moderate_rain"


@pytest.mark.asyncio
async def test_open_meteo_client_mock_fetch():
    json_path = FIXTURES_DIR / "open_meteo_response.json"
    raw_dict = json.loads(json_path.read_text(encoding="utf-8"))

    # Create mock transport
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=raw_dict))
    async with httpx.AsyncClient(transport=transport) as mock_client:
        provider = OpenMeteoProvider(http_client=mock_client)
        obs = await provider.get_current_weather(23.0225, 72.5714)
        assert obs.temperature_c == 31.5

        fc = await provider.get_forecast(23.0225, 72.5714, days=3)
        assert len(fc.daily) == 3
        await provider.close()


@pytest.mark.asyncio
async def test_open_meteo_client_timeout_handling():
    def raise_timeout(req):
        raise httpx.ReadTimeout("Mock timeout")

    transport = httpx.MockTransport(raise_timeout)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        settings = Settings(weather_provider_retries=0)
        provider = OpenMeteoProvider(settings=settings, http_client=mock_client)
        with pytest.raises(ProviderTimeoutError, match="Timeout connecting to Open-Meteo"):
            await provider.get_current_weather(23.0225, 72.5714)
        await provider.close()


# ============================================================================
# 5. Weather Provider Strategy & Fallback Cascade
# ============================================================================

@pytest.mark.asyncio
async def test_provider_manager_imd_warnings_with_filter():
    xml_path = FIXTURES_DIR / "imd_cap_red_alert.xml"
    xml_text = xml_path.read_text(encoding="utf-8")

    transport = httpx.MockTransport(lambda req: httpx.Response(200, text=xml_text))
    async with httpx.AsyncClient(transport=transport) as mock_client:
        imd_prov = IMDWarningProvider(http_client=mock_client)
        manager = WeatherProviderManager(warning_provider=imd_prov)

        # 1. Matching district filter
        surat_alerts = await manager.get_official_warnings(district_name="Surat")
        assert len(surat_alerts) == 1
        assert surat_alerts[0].warning_level == WarningLevel.RED

        # 2. Non-matching district filter
        delhi_alerts = await manager.get_official_warnings(district_name="Delhi")
        assert len(delhi_alerts) == 0

        await imd_prov.close()


@pytest.mark.asyncio
async def test_provider_manager_weather_fallback_on_primary_failure():
    json_path = FIXTURES_DIR / "open_meteo_response.json"
    raw_dict = json.loads(json_path.read_text(encoding="utf-8"))

    # Primary fails with 500 error
    primary_transport = httpx.MockTransport(lambda req: httpx.Response(500, text="Primary Server Error"))
    # Secondary succeeds
    secondary_transport = httpx.MockTransport(lambda req: httpx.Response(200, json=raw_dict))

    async with httpx.AsyncClient(transport=primary_transport) as primary_client, \
               httpx.AsyncClient(transport=secondary_transport) as secondary_client:

        settings = Settings(weather_provider_retries=0)
        primary = OpenMeteoProvider(settings=settings, http_client=primary_client)
        secondary = OpenMeteoProvider(settings=settings, http_client=secondary_client)

        manager = WeatherProviderManager(
            primary_weather_provider=primary,
            secondary_weather_provider=secondary,
        )

        obs = await manager.get_current_observation(23.0225, 72.5714)
        assert obs.temperature_c == 31.5
        # Secondary usage must be flagged as FALLBACK authority
        assert obs.authority == ProviderAuthority.FALLBACK
        assert obs.quality == ProviderQuality.PARTIAL

        await primary.close()
        await secondary.close()


@pytest.mark.asyncio
async def test_provider_manager_health_checks():
    transport = httpx.MockTransport(lambda req: httpx.Response(200))
    async with httpx.AsyncClient(transport=transport) as mock_client:
        manager = WeatherProviderManager(
            warning_provider=IMDWarningProvider(http_client=mock_client),
            primary_weather_provider=OpenMeteoProvider(http_client=mock_client),
            nwp_provider=GFSNWPProvider(http_client=mock_client),
        )
        health = await manager.check_all_providers_health()
        assert health["imd_cap"] is True
        assert health["open_meteo"] is True
        assert health["gfs_0p25"] is True


# ============================================================================
# 6. Optional Live Gated Provider Connectivity Check
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_open_meteo_endpoint_connectivity():
    """Gated integration test connecting to live Open-Meteo API."""
    provider = OpenMeteoProvider()
    try:
        obs = await provider.get_current_weather(23.0225, 72.5714)
        assert -20.0 <= obs.temperature_c <= 55.0
        assert obs.provider == "Open-Meteo"
    finally:
        await provider.close()
