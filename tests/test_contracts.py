"""Comprehensive contract tests validating Pydantic schemas, serialization, and Indian geographical bounds."""

import json
import pytest
from pydantic import ValidationError

from app.contracts import (
    AdvisoryAction,
    AnalystContextSchema,
    BrainRequest,
    BrainResponse,
    BrainType,
    ClientRequestSchema,
    ConfidenceInfo,
    Coordinates,
    CropContext,
    DateRange,
    DetectedLanguage,
    DeviceContext,
    ErrorResponse,
    EvidencePackage,
    FarmContext,
    FarmerContextSchema,
    FinalResponseSchema,
    GPSLocation,
    LocationContext,
    LocationSource,
    NormalizedRequestSchema,
    OfficialAlertItem,
    ProblemDetailRFC7807,
    ProvenanceItem,
    Recommendation,
    RequestedOutputFormat,
    ResearcherContextSchema,
    SourceCitation,
    SupportedLanguage,
    TemporalType,
    TemporalWindow,
    ToolCallRequest,
    ToolCallResponse,
    ToolProvenance,
    ToolQuality,
    ValidityWindow,
    VisualizationSpec,
    WarningLevel,
    WeatherAlert,
)


# ============================================================================
# 1. Location & Coordinate Validation Tests
# ============================================================================

def test_valid_indian_coordinates():
    """Verify coordinates within Indian bounding box (6N-38N, 68E-98E) pass validation."""
    coords = Coordinates(latitude=23.0225, longitude=72.5714)
    assert coords.latitude == 23.0225
    assert coords.longitude == 72.5714


def test_invalid_coordinates_outside_india():
    """Verify coordinates outside the Indian subcontinent bounding box are rejected."""
    # Latitude too far north (e.g. London 51.5N)
    with pytest.raises(ValidationError) as exc:
        Coordinates(latitude=51.5074, longitude=0.1278)
    assert "outside the supported Indian subcontinent bounding box" in str(exc.value)

    # Longitude too far west (e.g. New York -74.0W)
    with pytest.raises(ValidationError) as exc:
        Coordinates(latitude=23.0, longitude=-74.0)
    assert "outside the supported Indian subcontinent bounding box" in str(exc.value)


def test_location_context_creation():
    """Verify complete LocationContext construction and coordinates property."""
    loc = LocationContext(
        source=LocationSource.GPS,
        name="Surat",
        district="Surat",
        state="Gujarat",
        latitude=21.1702,
        longitude=72.8311,
        elevation_m=13.0,
        admin_pcode="IN-GJ-24",
    )
    assert loc.name == "Surat"
    assert loc.coordinates.latitude == 21.1702
    assert loc.coordinates.longitude == 72.8311


# ============================================================================
# 2. Client Request (UserInput) Tests
# ============================================================================

def test_valid_client_request():
    """Verify ClientRequestSchema parsing with GPS device context."""
    raw_payload = {
        "session_id": "sess_88fa109c-4993-4a11-8201-cf9e302a9b40",
        "user_id": "usr_990142",
        "query": "Should I irrigate my cotton crop tomorrow?",
        "language_preference": "hi",
        "selected_brain": "auto",
        "device_context": {
            "gps_location": {
                "latitude": 21.1702,
                "longitude": 72.8311,
                "accuracy_meters": 12.5,
            },
            "client_timestamp": "2026-08-29T11:30:00+05:30",
            "platform": "android",
            "app_version": "1.0.0",
        },
        "requested_output_formats": ["text", "weather_card", "recommendation"],
    }
    req = ClientRequestSchema.model_validate(raw_payload)
    assert req.session_id == "sess_88fa109c-4993-4a11-8201-cf9e302a9b40"
    assert req.language_preference == SupportedLanguage.HINDI
    assert req.selected_brain == BrainType.AUTO
    assert req.device_context.gps_location.latitude == 21.1702


def test_client_request_missing_query():
    """Verify ClientRequestSchema rejects empty/missing queries."""
    with pytest.raises(ValidationError):
        ClientRequestSchema(session_id="sess_123", query="")


def test_client_request_invalid_language():
    """Verify ClientRequestSchema rejects unsupported languages."""
    with pytest.raises(ValidationError):
        ClientRequestSchema(
            session_id="sess_123",
            query="Forecast today",
            language_preference="fr",  # French not in supported 5 Indic languages
        )


# ============================================================================
# 3. Normalized Request Tests
# ============================================================================

def test_normalized_request_schema():
    """Verify NormalizedRequestSchema parsing matching docs/04_INPUT_OUTPUT_CONTRACT.md."""
    norm_payload = {
        "request_id": "req_df4092b1",
        "session_id": "sess_88fa109c-4993-4a11-8201-cf9e302a9b40",
        "raw_query": "Should I irrigate my cotton crop tomorrow?",
        "normalized_query": "Should I irrigate my cotton crop tomorrow?",
        "detected_language": {
            "code": "en",
            "script": "Latin",
            "is_code_mixed": False,
            "confidence": 0.99,
        },
        "target_language": "hi",
        "location": {
            "source": "gps",
            "name": "Surat",
            "district": "Surat",
            "state": "Gujarat",
            "country": "India",
            "latitude": 21.1702,
            "longitude": 72.8311,
            "elevation_m": 13.0,
            "admin_pcode": "IN-GJ-24",
        },
        "temporal_window": {
            "reference_ist": "2026-08-29T11:30:00+05:30",
            "start_utc": "2026-08-29T18:30:00Z",
            "end_utc": "2026-08-30T18:29:59Z",
            "temporal_type": "relative_day",
            "relative_expression": "tomorrow",
        },
        "router_override": None,
        "conversation_state": {
            "turn_count": 3,
            "last_brain_used": "general",
            "active_context_keys": ["location", "crop"],
        },
    }
    norm_req = NormalizedRequestSchema.model_validate(norm_payload)
    assert norm_req.request_id == "req_df4092b1"
    assert norm_req.target_language == SupportedLanguage.HINDI
    assert norm_req.location.name == "Surat"
    assert norm_req.temporal_window.temporal_type == TemporalType.RELATIVE_DAY


# ============================================================================
# 4. Optional Personalization Tests
# ============================================================================

def test_farmer_personalization_optional():
    """Verify FarmerContextSchema can be instantiated partially or empty."""
    empty_ctx = FarmerContextSchema()
    assert empty_ctx.crop is None
    assert empty_ctx.farm is None

    full_ctx = FarmerContextSchema(
        crop=CropContext(
            name="Cotton",
            variety="Bt Cotton RCH-2",
            growth_stage="flowering_and_boll_formation",
            sowing_date="2026-06-15",
        ),
        farm=FarmContext(
            farm_size_acres=4.5,
            irrigation_type="drip",
            soil_type="black_cotton_clay",
            soil_moisture_estimate_pct=68.0,
        ),
    )
    assert full_ctx.crop.name == "Cotton"
    assert full_ctx.farm.farm_size_acres == 4.5


def test_researcher_and_analyst_personalization():
    """Verify ResearcherContextSchema and AnalystContextSchema default structures."""
    r_ctx = ResearcherContextSchema()
    assert "imd_gridded_0p25" in r_ctx.preferred_datasets
    assert r_ctx.baseline_period.start_year == 1991

    a_ctx = AnalystContextSchema(target_districts=["Surat", "Bharuch"])
    assert len(a_ctx.target_districts) == 2
    assert a_ctx.hazard_thresholds.heavy_rainfall_24h_mm == 64.5


# ============================================================================
# 5. Tool Invocation & Response Contracts Tests
# ============================================================================

def test_tool_call_request_and_response():
    """Verify ToolCallRequest and ToolCallResponse envelopes."""
    req = ToolCallRequest(
        call_id="call_9901ad87",
        tool_name="calculate_irrigation_advisory",
        requested_by_brain=BrainType.FARMER,
        arguments={
            "location": {"latitude": 21.1702, "longitude": 72.8311},
            "crop_name": "Cotton",
            "forecast_rainfall_24h_mm": 35.0,
        },
    )
    assert req.call_id == "call_9901ad87"
    assert req.requested_by_brain == BrainType.FARMER

    resp = ToolCallResponse(
        call_id="call_9901ad87",
        tool_name="calculate_irrigation_advisory",
        status="success",
        execution_time_ms=42.1,
        data={"advisory_action": "POSTPONE", "water_deficit_mm": -30.8},
        provenance=ToolProvenance(
            data_sources=["IMD Numerical Guidance", "FAO-56 Dual Model"],
            retrieval_timestamp="2026-08-29T11:30:15Z",
            validity_window=ValidityWindow(
                start="2026-08-29T18:30:00Z",
                end="2026-08-30T18:29:59Z",
            ),
        ),
        quality=ToolQuality(freshness="fresh", completeness="complete"),
    )
    assert resp.is_success is True
    assert resp.data["advisory_action"] == "POSTPONE"


# ============================================================================
# 6. Evidence Package & Final Response Schema Tests
# ============================================================================

def test_evidence_package_validation():
    """Verify EvidencePackage structure holding verified meteorological evidence."""
    loc = LocationContext(
        name="Ahmedabad",
        district="Ahmedabad",
        state="Gujarat",
        latitude=23.0225,
        longitude=72.5714,
    )
    evidence = EvidencePackage(
        evidence_id="ev_89f72b14",
        generated_at="2026-08-29T06:00:00Z",
        location=loc,
        temporal_context={"reference_time_ist": "2026-08-29 11:30:00+05:30"},
        official_alerts=[
            OfficialAlertItem(
                source="IMD",
                warning_level=WarningLevel.YELLOW,
                hazard="Heavy Rainfall",
                description="Heavy rainfall at isolated places over Ahmedabad district.",
                valid_until="2026-08-31T08:30:00+05:30",
            )
        ],
        tool_results={
            "forecast": {"temperature_max_c": 33.5, "rainfall_total_mm": 28.4},
        },
        provenance=[
            ProvenanceItem(
                dataset="IMD District Bulletin",
                retrieved_at="2026-08-29T05:30:00Z",
                is_official=True,
            )
        ],
        limitations=["Convective rain may vary at field scale."],
    )
    assert evidence.evidence_id == "ev_89f72b14"
    assert len(evidence.official_alerts) == 1
    assert evidence.official_alerts[0].warning_level == WarningLevel.YELLOW


def test_final_response_schema_full_roundtrip():
    """Verify FinalResponseSchema serialization matching the PRD and contracts document."""
    final_payload = {
        "response_id": "resp_cc9140fa-81a1-46bb-9321-72990aa0b98e",
        "session_id": "sess_88fa109c-4993-4a11-8201-cf9e302a9b40",
        "brain": "farmer",
        "language": "hi",
        "created_at": "2026-08-29T11:30:18+05:30",
        "summary": "कल सूरत में भारी बारिश की संभावना के कारण कपास की फसल की सिंचाई स्थगित करें।",
        "answer": "मौसम पूर्वानुमान के अनुसार कल भारी बारिश की संभावना है।",
        "data": {
            "forecast_summary": {"temp_max_c": 31.2, "rainfall_total_mm": 35.0},
            "agronomic_metrics": {"crop": "Cotton", "irrigation_action": "POSTPONE"},
        },
        "recommendation": {
            "primary_action": "POSTPONE_IRRIGATION",
            "urgency": "high",
            "actions": ["सिंचाई स्थगित करें।", "जल निकासी नालियों को साफ रखें।"],
        },
        "alert": {
            "source": "IMD",
            "level": "Yellow",
            "hazard_type": "Heavy Rain",
            "headline": "भारी बारिश की चेतावनी (Yellow Alert)",
            "description": "सूरत जिले में भारी वर्षा होने की संभावना है।",
            "valid_until": "2026-08-31T08:30:00+05:30",
        },
        "visualizations": [
            {
                "type": "weather_card",
                "id": "viz_card_01",
                "title": "Daily Weather Card",
                "spec": {"temperature_range": [25.4, 31.2]},
            }
        ],
        "sources": [
            {
                "authority": "IMD",
                "dataset": "Official District Forecast",
                "retrieved_at": "2026-08-29T10:45:00+05:30",
                "is_official": True,
            }
        ],
        "confidence": {
            "evidence_level": "high",
            "model_agreement": "high",
            "data_freshness_status": "fresh",
            "notes": "Corroborated across IMD and GFS.",
        },
        "limitations": ["लोकल स्तर पर वर्षा भिन्न हो सकती है।"],
    }

    # Deserialization
    response_obj = FinalResponseSchema.model_validate(final_payload)
    assert response_obj.response_id == "resp_cc9140fa-81a1-46bb-9321-72990aa0b98e"
    assert response_obj.brain == BrainType.FARMER
    assert response_obj.recommendation.primary_action == AdvisoryAction.POSTPONE_IRRIGATION
    assert response_obj.alert.level == WarningLevel.YELLOW

    # JSON Round-Trip
    json_str = response_obj.model_dump_json()
    re_parsed = json.loads(json_str)
    assert re_parsed["brain"] == "farmer"
    assert re_parsed["alert"]["level"] == "Yellow"


# ============================================================================
# 7. Error Models & RFC 7807 Tests
# ============================================================================

def test_error_response_and_rfc7807():
    """Verify standard conversational ErrorResponse and RFC 7807 problem details."""
    err = ErrorResponse(
        error_code="MISSING_MANDATORY_LOCATION",
        message="Please specify your city or grant GPS permission.",
        action_required="PROMPT_LOCATION_INPUT",
        details={"suggested_cities": ["Ahmedabad", "Surat", "Pune"]},
    )
    assert err.status == "error"
    assert err.error_code == "MISSING_MANDATORY_LOCATION"

    rfc = ProblemDetailRFC7807(
        type="https://weathergpt.in/errors/INVALID_COORDINATES",
        title="Invalid Coordinate Range",
        status=400,
        detail="Latitude outside Indian bounding box.",
        timestamp="2026-08-29T11:35:00+05:30",
    )
    assert rfc.status == 400
    assert rfc.title == "Invalid Coordinate Range"
