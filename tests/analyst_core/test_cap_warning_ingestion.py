"""Unit tests for OASIS / WMO Common Alerting Protocol (CAP v1.2) alert ingestion."""

import pytest
from app.brains.analyst_core.models.schemas import AlertSeverity, DataType
from app.brains.analyst_core.data.cap_parser import CAPParser
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider


SAMPLE_CAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>IMD-CAP-2026-MUMBAI-09</identifier>
  <sender>India Meteorological Department (IMD)</sender>
  <sent>2026-09-01T08:30:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Met</category>
    <event>Heavy Rainfall</event>
    <urgency>Immediate</urgency>
    <severity>Severe</severity>
    <certainty>Observed</certainty>
    <headline>Orange Alert for Intense Rainfall in Mumbai Suburban</headline>
    <description>Very heavy precipitation exceeding 115 mm expected over next 12 hours.</description>
    <instruction>Avoid waterlogged underpasses. Commuters plan alternative routes.</instruction>
    <area>
      <areaDesc>Mumbai, Thane, and Raigad</areaDesc>
    </area>
  </info>
</alert>
"""

SAMPLE_CAP_JSON = {
    "identifier": "NDMA-CAP-DELHI-004",
    "sender": "National Disaster Management Authority (NDMA)",
    "sent": "2026-09-01T09:00:00+05:30",
    "status": "Actual",
    "msgType": "Alert",
    "info": [
        {
            "event": "Heatwave",
            "urgency": "Expected",
            "severity": "Extreme",
            "certainty": "Likely",
            "headline": "Red Warning: Extreme Heatwave in NCR",
            "description": "Day temperatures likely to exceed 45 degrees Celsius.",
            "instruction": "Avoid direct sun exposure between 12 PM and 3 PM. Hydrate frequently.",
            "area": {"areaDesc": "National Capital Region"},
        }
    ],
}


def test_cap_parser_xml():
    """Verifies parsing of standard OASIS CAP XML."""
    parser = CAPParser()
    alerts = parser.parse_cap_xml(SAMPLE_CAP_XML)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_id == "IMD-CAP-2026-MUMBAI-09"
    assert alert.issuing_authority == "India Meteorological Department (IMD)"
    assert alert.severity == AlertSeverity.ORANGE_ALERT
    assert alert.warning_type == "HEAVY_RAINFALL"
    assert "Orange Alert for Intense Rainfall" in alert.headline
    assert "Avoid waterlogged underpasses" in alert.recommended_precautions[0]
    assert alert.geographic_area == "Mumbai, Thane, and Raigad"
    assert alert.is_verified is True
    assert alert.data_type == DataType.OFFICIAL_WARNING


def test_cap_parser_json():
    """Verifies parsing of CAP JSON alert structure."""
    parser = CAPParser()
    alerts = parser.parse_cap_json(SAMPLE_CAP_JSON)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_id == "NDMA-CAP-DELHI-004"
    assert alert.severity == AlertSeverity.RED_WARNING
    assert alert.warning_type == "HEATWAVE"
    assert "Red Warning: Extreme Heatwave" in alert.headline
    assert alert.is_verified is True


def test_cap_parser_skips_test_or_draft():
    """Verifies that non-actual status alerts (e.g. Test, Draft) are rejected."""
    parser = CAPParser()
    test_xml = SAMPLE_CAP_XML.replace("<status>Actual</status>", "<status>Test</status>")
    alerts = parser.parse_cap_xml(test_xml)
    assert len(alerts) == 0


def test_real_provider_cap_ingestion():
    """Verifies that RealDataProvider ingests and caches parsed CAP alerts."""
    provider = RealDataProvider(
        mock_http_responses={"alert:mumbai": SAMPLE_CAP_XML}
    )
    alerts = provider.get_official_warnings("Mumbai")
    assert len(alerts) == 1
    assert alerts[0].alert_id == "IMD-CAP-2026-MUMBAI-09"
    assert alerts[0].severity == AlertSeverity.ORANGE_ALERT
