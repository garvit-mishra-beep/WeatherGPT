"""Ingestion adapters attaching operational data types to canonical EvidenceRecords.

Supports:
- Surface weather observations (Open-Meteo, OpenWeather, etc.)
- Multi-day weather forecasts
- Official IMD CAP alerts
- NWP grid observations (GFS, WRF)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.adapters.models import (
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
)
from app.evidence.models import (
    EvidenceClass,
    EvidenceRecord,
    QualityState,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.service import evidence_service


def ingest_observation_to_evidence(
    obs: NormalizedWeatherObservation,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> List[EvidenceRecord]:
    """Converts a NormalizedWeatherObservation into canonical EvidenceRecords for key variables."""
    def _parse_dt(iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except Exception:
            return None

    retrieval_time = _parse_dt(obs.retrieval_timestamp_iso) or datetime.now(timezone.utc)
    obs_time = _parse_dt(obs.observation_time_iso) or retrieval_time

    temporal = TemporalIdentity(
        retrieval_time=retrieval_time,
        observation_time=obs_time,
        issue_time=None,
        valid_from=None,
        valid_to=None,
    )

    spatial = SpatialIdentity(
        location_id=None,
        latitude=obs.latitude,
        longitude=obs.longitude,
        geometry_geojson={"type": "Point", "coordinates": [obs.longitude, obs.latitude]},
        spatial_resolution="point",
    )

    records: List[EvidenceRecord] = []
    source_id = "OPEN_METEO" if "open_meteo" in obs.provider.lower() else "OPEN_METEO"

    # 1. Temperature Record
    if obs.temperature_c is not None:
        rec_t = evidence_service.create_evidence(
            source_id=source_id,
            evidence_class=EvidenceClass.OBSERVATION,
            raw_field="temperature_c",
            raw_value=obs.temperature_c,
            raw_unit="degC",
            normalized_field="air_temperature",
            normalized_value=obs.temperature_c,
            normalized_unit="degC",
            temporal=temporal,
            spatial=spatial,
            raw_payload=raw_payload,
            endpoint_uri=f"geo:{obs.latitude},{obs.longitude}",
        )
        records.append(rec_t)

    # 2. Rainfall Record
    if obs.precipitation_mm is not None:
        rec_r = evidence_service.create_evidence(
            source_id=source_id,
            evidence_class=EvidenceClass.OBSERVATION,
            raw_field="precipitation_mm",
            raw_value=obs.precipitation_mm,
            raw_unit="mm",
            normalized_field="precipitation_amount",
            normalized_value=obs.precipitation_mm,
            normalized_unit="mm",
            temporal=temporal,
            spatial=spatial,
            raw_payload=raw_payload,
            endpoint_uri=f"geo:{obs.latitude},{obs.longitude}",
        )
        records.append(rec_r)

    # 3. Wind Speed Record
    if obs.wind_speed_kmh is not None:
        rec_w = evidence_service.create_evidence(
            source_id=source_id,
            evidence_class=EvidenceClass.OBSERVATION,
            raw_field="wind_speed_kmh",
            raw_value=obs.wind_speed_kmh,
            raw_unit="km/h",
            normalized_field="wind_speed",
            normalized_value=obs.wind_speed_kmh,
            normalized_unit="km/h",
            temporal=temporal,
            spatial=spatial,
            raw_payload=raw_payload,
            endpoint_uri=f"geo:{obs.latitude},{obs.longitude}",
        )
        records.append(rec_w)

    return records


def ingest_alert_to_evidence(
    alert: NormalizedOfficialAlert,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> EvidenceRecord:
    """Converts an official IMD CAP alert into a canonical OFFICIAL_WARNING EvidenceRecord."""
    retrieval_time = datetime.now(timezone.utc)

    def _parse_dt(iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except Exception:
            return None

    issue_dt = _parse_dt(alert.effective_time_iso or alert.sent_time_iso)
    expires_dt = _parse_dt(alert.expires_time_iso)

    temporal = TemporalIdentity(
        retrieval_time=retrieval_time,
        issue_time=issue_dt,
        observation_time=None,
        valid_from=issue_dt,
        valid_to=expires_dt,
    )

    spatial = SpatialIdentity(
        location_id=alert.area_description,
        latitude=None,
        longitude=None,
        geometry_geojson={"type": "Polygon", "coordinates": alert.polygons} if alert.polygons else None,
        spatial_resolution="district",
    )

    # Check for expired warning
    custom_flags: List[str] = []
    if expires_dt and expires_dt < datetime.now(timezone.utc):
        custom_flags.append("EXPIRED_VALIDITY")

    alert_raw = dict(raw_payload) if raw_payload else {}
    alert_raw.setdefault("alert_id", alert.alert_id)
    alert_raw.setdefault("sender", alert.sender)
    alert_raw.setdefault("official_text", alert.description or alert.headline)

    return evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OFFICIAL_WARNING,
        raw_field="warning_level",
        raw_value=alert.warning_level.value,
        raw_unit="IMD_COLOR_CODE",
        normalized_field="official_hazard_warning",
        normalized_value={
            "hazard": alert.event_title,
            "severity": alert.severity,
            "warning_level": alert.warning_level.value,
            "headline": alert.headline,
            "instruction": alert.instruction,
        },
        normalized_unit="CAP_1.2",
        temporal=temporal,
        spatial=spatial,
        raw_payload=alert_raw,
        product_id="IMD_CAP_BULLETIN",
        endpoint_uri="https://sachet.ndma.gov.in/cap",
        custom_flags=custom_flags,
    )


def ingest_nwp_to_evidence(
    nwp: NormalizedNWPGridPoint,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> List[EvidenceRecord]:
    """Converts an NWP grid point query into canonical FORECAST EvidenceRecords."""
    def _parse_dt(iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except Exception:
            return None

    retrieval_time = datetime.now(timezone.utc)
    init_dt = _parse_dt(nwp.initialization_time_iso)
    valid_dt = _parse_dt(nwp.valid_time_iso)

    temporal = TemporalIdentity(
        retrieval_time=retrieval_time,
        issue_time=init_dt,
        observation_time=None,
        valid_from=valid_dt,
        valid_to=None,
    )

    spatial = SpatialIdentity(
        location_id=None,
        latitude=nwp.latitude,
        longitude=nwp.longitude,
        spatial_resolution="0.25deg" if "GFS" in nwp.model_name.upper() else "grid",
    )

    records: List[EvidenceRecord] = []
    source_id = "NWP_GFS" if "GFS" in nwp.model_name.upper() else "OPEN_METEO"

    if nwp.temperature_2m_c is not None:
        records.append(
            evidence_service.create_evidence(
                source_id=source_id,
                evidence_class=EvidenceClass.FORECAST,
                raw_field="temperature_2m_c",
                raw_value=nwp.temperature_2m_c,
                raw_unit="degC",
                normalized_field="projected_temperature",
                normalized_value=nwp.temperature_2m_c,
                normalized_unit="degC",
                temporal=temporal,
                spatial=spatial,
                raw_payload=raw_payload,
                product_id=f"{nwp.model_name}_SURFACE",
            )
        )

    if nwp.step_precip_mm is not None:
        records.append(
            evidence_service.create_evidence(
                source_id=source_id,
                evidence_class=EvidenceClass.FORECAST,
                raw_field="step_precip_mm",
                raw_value=nwp.step_precip_mm,
                raw_unit="mm",
                normalized_field="projected_precipitation_amount",
                normalized_value=nwp.step_precip_mm,
                normalized_unit="mm",
                temporal=temporal,
                spatial=spatial,
                raw_payload=raw_payload,
                product_id=f"{nwp.model_name}_PRECIP",
            )
        )

    if nwp.wind_speed_kmh is not None:
        records.append(
            evidence_service.create_evidence(
                source_id=source_id,
                evidence_class=EvidenceClass.FORECAST,
                raw_field="wind_speed_kmh",
                raw_value=nwp.wind_speed_kmh,
                raw_unit="km/h",
                normalized_field="projected_wind_speed",
                normalized_value=nwp.wind_speed_kmh,
                normalized_unit="km/h",
                temporal=temporal,
                spatial=spatial,
                raw_payload=raw_payload,
                product_id=f"{nwp.model_name}_WIND",
            )
        )

    return records
