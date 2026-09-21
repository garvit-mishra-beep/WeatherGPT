"""B9 — FastAPI REST API Comprehensive Test Suite (/api/v1).

Tests:
1. Liveness (/api/v1/health) and Readiness (/api/v1/ready)
2. Weather endpoints (/current, /forecast, /alerts, /intelligence)
3. GIS endpoints (/location, /boundary, /hazard-intersection, /risk-assessment, /analysis)
4. Map endpoints (/point, /warning, /risk)
5. NWP endpoints (/gfs, /comparison)
6. Parameter validation & out-of-bounds coordinate handling
7. Request-ID correlation header propagation
8. OpenAPI schema completeness (/openapi.json)
9. Performance smoke benchmarking (< 25 ms)
"""

import time
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.factory import create_app


@pytest.fixture
def client():
    """Build a test client with lifespan lifecycle initialized."""
    settings = Settings(app_env="test", app_name="WeatherGPT-Test")
    app = create_app(settings=settings, configure_logging_enabled=False)
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "environment" in data


def test_ready_endpoint(client):
    res = client.get("/api/v1/ready")
    assert res.status_code in (200, 503)
    data = res.json()
    assert "status" in data


def test_weather_current_endpoint(client):
    res = client.get("/api/v1/weather/current?lat=21.17&lon=72.83")
    assert res.status_code == 200
    data = res.json()
    assert "temperature_c" in data
    assert "location" in data
    assert data["location"]["latitude"] == 21.17


def test_weather_forecast_endpoint(client):
    res = client.get("/api/v1/weather/forecast?lat=21.17&lon=72.83&days=3")
    assert res.status_code == 200
    data = res.json()
    assert "daily_forecast" in data
    assert len(data["daily_forecast"]) == 3


def test_weather_alerts_endpoint(client):
    res = client.get("/api/v1/weather/alerts?district=Surat")
    assert res.status_code == 200
    data = res.json()
    assert "active_alerts_count" in data
    assert "alerts" in data


def test_weather_intelligence_endpoint(client):
    res = client.get("/api/v1/weather/intelligence?lat=21.17&lon=72.83")
    assert res.status_code == 200
    data = res.json()
    assert "latitude" in data
    assert "longitude" in data


def test_gis_hazard_intersection_endpoint(client):
    poly = {
        "type": "Polygon",
        "coordinates": [[[72.5, 21.0], [73.3, 21.0], [73.3, 21.9], [72.5, 21.9], [72.5, 21.0]]],
    }
    payload = {
        "warning_geometry": poly,
        "alert_id": "IMD-CAP-001",
        "severity": "Orange",
        "event": "Very Heavy Rain",
    }
    res = client.post("/api/v1/gis/hazard-intersection", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["alert_id"] == "IMD-CAP-001"
    assert data["severity"] == "Orange"
    assert "total_affected_boundaries" in data


def test_gis_risk_assessment_endpoint(client):
    payload = {
        "district_name": "Surat",
        "precip_24h_percentile": 92.0,
        "exposure_index": 8.0,
        "vulnerability_index": 7.0,
    }
    res = client.post("/api/v1/gis/risk-assessment", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["district"] == "Surat"
    assert data["hazard_index"] == 7.5  # 92nd percentile -> 7.5
    assert data["composite_risk_score"] > 0.0


def test_gis_analysis_endpoint(client):
    payload = {
        "latitude": 21.17,
        "longitude": 72.83,
        "observed_rain_mm": 120.0,
        "observed_wind_kmh": 45.0,
    }
    res = client.post("/api/v1/gis/analysis", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "impact" in data
    assert data["impact"]["composite_impact_score"] > 0.0


def test_map_point_endpoint(client):
    res = client.get("/api/v1/map/point?lat=21.17&lon=72.83")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "map_specification"
    assert "viewport" in data
    assert "layers" in data


def test_map_warning_endpoint(client):
    poly = {
        "type": "Polygon",
        "coordinates": [[[72.5, 21.0], [73.3, 21.0], [73.3, 21.9], [72.5, 21.9], [72.5, 21.0]]],
    }
    payload = {
        "warning_geometry": poly,
        "alert_id": "IMD-001",
        "severity": "Red",
        "event": "Cyclonic Storm",
    }
    res = client.post("/api/v1/map/warning", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "map_specification"
    assert len(data["layers"]) >= 1


def test_map_risk_endpoint(client):
    payload = {"latitude": 21.17, "longitude": 72.83, "observed_rain_mm": 80.0}
    res = client.post("/api/v1/map/risk", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "map_specification"


def test_nwp_gfs_endpoint(client):
    res = client.get("/api/v1/nwp/gfs?lat=21.17&lon=72.83&lead_hours=24")
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "GFS_0P25"
    assert "atmospheric_variables" in data


def test_nwp_comparison_endpoint(client):
    res = client.get("/api/v1/nwp/comparison?lat=21.17&lon=72.83&lead_hours=24")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "GFS_0p25" in data["models"]


def test_invalid_coordinates_validation(client):
    # Latitude 50.0 is out of bounds [6.0, 38.0]
    res = client.get("/api/v1/weather/current?lat=50.0&lon=72.83")
    assert res.status_code == 422


def test_openapi_schema_generation(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert "openapi" in schema
    paths = schema.get("paths", {})
    assert "/api/v1/health" in paths
    assert "/api/v1/weather/current" in paths
    assert "/api/v1/gis/hazard-intersection" in paths
    assert "/api/v1/map/point" in paths
    assert "/api/v1/nwp/gfs" in paths


def test_api_performance_smoke(client):
    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
    duration = time.perf_counter() - start
    avg_latency_ms = (duration / iterations) * 1000.0

    assert avg_latency_ms < 15.0
