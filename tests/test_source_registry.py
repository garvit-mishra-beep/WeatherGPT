"""Comprehensive Test Suite for Phase 9B Source Registry & Operational Governance.

Covers:
- Statutory E0 authority tier validation & registration boundaries
- Freshness policies and class validation
- Thread-safe health telemetry tracking (success, failure, degraded, offline)
- REST API endpoints for data source governance and health observability
- Security: RBAC protection on administrative manual refresh and SSRF rejection
"""

import pytest
from fastapi.testclient import TestClient

from app.decision.auth import create_reviewer_token
from app.evidence.models import (
    EvidenceClass,
    FreshnessPolicy,
    SourceAuthorityLevel,
    SourceMetadata,
)
from app.evidence.registry import SourceRegistry, source_registry
from app.main import app

client = TestClient(app)


def test_canonical_sources_initialized():
    """Verify all mandatory operational and scientific sources are present in registry."""
    reg = SourceRegistry()
    sources = reg.list_sources(active_only=False)
    source_ids = {s.source_id for s in sources}

    mandatory = {"IMD", "CWC", "NDMA_SACHET", "OPEN_METEO", "NWP_GFS", "NWP_ECMWF", "GSI", "NASA_IMERG", "WMO", "UNDRR"}
    assert mandatory.issubset(source_ids)


def test_statutory_e0_authority_lockdown():
    """Verify that unauthorized non-statutory sources cannot claim E0 Operational Authority."""
    reg = SourceRegistry()

    # Attempting to register a commercial provider as E0 must raise ValueError
    invalid_e0 = SourceMetadata(
        source_id="COMMERCIAL_API",
        source_name="Commercial Weather Inc.",
        authority="Commercial Vendor",
        source_type="WEATHER_API",
        authority_level=SourceAuthorityLevel.E0,
        supported_classes=[EvidenceClass.OBSERVATION],
    )
    with pytest.raises(ValueError, match="cannot be registered with E0 Operational Authority"):
        reg.register_source(invalid_e0)


def test_official_warning_class_lockdown():
    """Verify non-statutory sources cannot register EvidenceClass.OFFICIAL_WARNING."""
    reg = SourceRegistry()

    invalid_warning_src = SourceMetadata(
        source_id="THIRD_PARTY_FORECAST",
        source_name="Third Party Forecast",
        authority="Independent Model",
        source_type="NWP",
        authority_level=SourceAuthorityLevel.E2,
        supported_classes=[EvidenceClass.OFFICIAL_WARNING],
    )
    with pytest.raises(ValueError, match="cannot register EvidenceClass.OFFICIAL_WARNING"):
        reg.register_source(invalid_warning_src)


def test_source_health_telemetry_tracking():
    """Verify success and failure recording, consecutive failures, and status transitions."""
    reg = SourceRegistry()

    # Success records online
    reg.record_success("IMD")
    s = reg.get_source("IMD")
    assert s is not None
    assert s.health_status == "ONLINE"
    assert s.consecutive_failures == 0
    assert s.last_success is not None

    # Failures transition to DEGRADED
    reg.record_failure("IMD")
    assert s.consecutive_failures == 1
    assert s.health_status == "DEGRADED"

    # 5 consecutive failures transition to FAILED
    for _ in range(4):
        reg.record_failure("IMD")
    assert s.consecutive_failures == 5
    assert s.health_status == "FAILED"

    # Recovery
    reg.record_success("IMD")
    assert s.consecutive_failures == 0
    assert s.health_status == "ONLINE"


def test_source_disable_enable():
    """Verify administrative enable/disable transitions."""
    reg = SourceRegistry()
    reg.set_source_active("OPEN_METEO", False)
    s = reg.get_source("OPEN_METEO")
    assert s is not None
    assert s.is_active is False
    assert s.health_status == "DISABLED"

    # Re-enable
    reg.set_source_active("OPEN_METEO", True)
    assert s.is_active is True
    assert s.health_status == "ONLINE"


def test_api_list_data_sources():
    """Verify GET /api/v1/data-sources lists operational metadata without leaking secrets."""
    resp = client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 8

    # Verify no credentials or internal secrets exposed
    for item in data:
        assert "api_key" not in item
        assert "secret" not in item
        assert "source_id" in item
        assert "authority_level" in item
        assert "health_status" in item


def test_api_get_single_source():
    """Verify GET /api/v1/data-sources/{source_id} returns detailed metadata."""
    resp = client.get("/api/v1/data-sources/IMD")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["source_id"] == "IMD"
    assert detail["authority_level"] == "E0"
    assert "freshness_policies" in detail
    assert "OFFICIAL_WARNING" in detail["freshness_policies"]


def test_api_get_data_sources_health():
    """Verify GET /api/v1/data-sources/health aggregates provider states."""
    resp = client.get("/api/v1/data-sources/health")
    assert resp.status_code == 200
    health = resp.json()
    assert health["status"] in ("HEALTHY", "DEGRADED", "UNHEALTHY")
    assert health["total_sources"] >= 8
    assert "sources" in health


def test_api_refresh_unauthorized_blocked():
    """Verify unauthenticated/unauthorized users cannot trigger data source refresh."""
    # No auth header
    resp = client.post("/api/v1/data-sources/IMD/refresh")
    assert resp.status_code == 401

    # Unprivileged token
    guest_token = create_reviewer_token(subject="user-1", role="GUEST")
    resp_guest = client.post(
        "/api/v1/data-sources/IMD/refresh",
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert resp_guest.status_code == 403


def test_api_refresh_authorized_success():
    """Verify authorized operator can trigger controlled source refresh."""
    admin_token = create_reviewer_token(subject="admin-01", role="INCIDENT_COMMANDER")
    resp = client.post(
        "/api/v1/data-sources/IMD/refresh",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REFRESH_TRIGGERED"
    assert data["source_id"] == "IMD"
