"""Canonical Operational Data Adapter Contracts and Implementations for VAYUBODHAK Phase 9B.

Enforces:
1. OperationalDataAdapter interface: fetch -> validate -> normalize -> classify -> evidence
2. Cryptographic raw data preservation (SHA-256 hash calculation)
3. Audit run logging via AdapterRunRecord
4. SSRF protection via strict domain allowlisting
5. Zero silent conversion or authority escalation
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Dict, Generic, List, Optional, TypeVar
from urllib.parse import urlparse
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.adapters.circuit_breaker import CircuitBreaker
from app.adapters.errors import AdapterError, ProviderValidationError
from app.adapters.http_executor import ResilientHTTPExecutor
from app.adapters.metrics import provider_metrics
from app.adapters.models import (
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.config import Settings, settings as default_settings
from app.evidence.models import (
    EvidenceClass,
    EvidenceRecord,
    QualityState,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.service import evidence_service
from app.pipeline.models import DataSourceStatus

logger = logging.getLogger(__name__)

# Strict allowlist of approved external data provider hostnames to prevent SSRF
ALLOWED_OPERATIONAL_DOMAINS = frozenset({
    "mausam.imd.gov.in",
    "sachet.ndma.gov.in",
    "api.open-meteo.com",
    "nomads.ncep.noaa.gov",
    "api.openweathermap.org",
    "api.weatherapi.com",
    "api.tomorrow.io",
    "api.openaq.org",
    "ffs.tamcwc.gov.in",
    "bhukosh.gsi.gov.in",
    "www.ecmwf.int",
    "testserver",  # FastAPI TestClient
    "localhost",
    "127.0.0.1",
})


class SSRFSecurityError(AdapterError):
    """Raised when an outbound URL is not in the approved server-configured domain allowlist."""
    def __init__(self, url: str):
        super().__init__(f"SSRF violation: destination URL '{url}' is not in the approved domain allowlist.")
        self.url = url


def validate_outbound_url(url: str, allow_local_in_dev: bool = True) -> None:
    """Validate that target URL belongs to an approved operational domain."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SSRFSecurityError(url)
        if hostname not in ALLOWED_OPERATIONAL_DOMAINS:
            raise SSRFSecurityError(url)
        # Scheme check
        if parsed.scheme not in ("https", "http"):
            raise SSRFSecurityError(url)
    except SSRFSecurityError:
        raise
    except Exception as e:
        raise SSRFSecurityError(url) from e


class AdapterHealthStatus(str, Enum):
    """Operational health state of a data adapter."""
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class AdapterRunRecord(BaseModel):
    """Lightweight operational audit telemetry record for a single adapter execution."""
    adapter_run_id: str = Field(
        default_factory=lambda: f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    )
    source_id: str
    started_at: datetime
    completed_at: datetime
    status: str = "SUCCESS"  # SUCCESS, DEGRADED, FAILED
    http_status: Optional[int] = None
    latency_ms: float = 0.0
    records_received: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    error_code: Optional[str] = None
    raw_hash: str = ""

    model_config = ConfigDict(frozen=True)


T_Raw = TypeVar("T_Raw")
T_Norm = TypeVar("T_Norm")


class AdapterFetchResult(Generic[T_Raw]):
    """Container preserving raw external response and its cryptographic provenance."""
    def __init__(
        self,
        raw_payload: T_Raw,
        raw_hash: str,
        retrieval_time: datetime,
        source_status: DataSourceStatus = DataSourceStatus.LIVE,
        http_status: Optional[int] = 200,
        latency_ms: float = 0.0,
        endpoint_uri: Optional[str] = None,
    ):
        self.raw_payload = raw_payload
        self.raw_hash = raw_hash
        self.retrieval_time = retrieval_time
        self.source_status = source_status
        self.http_status = http_status
        self.latency_ms = latency_ms
        self.endpoint_uri = endpoint_uri


def compute_payload_hash(data: Any) -> str:
    """Deterministic SHA-256 hash of arbitrary string or JSON-compatible dictionary."""
    if isinstance(data, str):
        content_bytes = data.encode("utf-8")
    elif isinstance(data, bytes):
        content_bytes = data
    else:
        try:
            content_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        except Exception:
            content_bytes = str(data).encode("utf-8")
    return hashlib.sha256(content_bytes).hexdigest()


class OperationalDataAdapter(ABC, Generic[T_Raw, T_Norm]):
    """Canonical base contract for all operational data adapters."""

    def __init__(self, source_id: str, settings: Optional[Settings] = None):
        self.source_id = source_id
        self.settings = settings or default_settings
        self.recent_runs: List[AdapterRunRecord] = []
        self._consecutive_failures: int = 0
        self._last_success: Optional[datetime] = None
        self._last_failure: Optional[datetime] = None

    @property
    @abstractmethod
    def authority(self) -> ProviderAuthority:
        """Declared authority classification."""
        ...

    @abstractmethod
    async def fetch(self, **kwargs) -> AdapterFetchResult[T_Raw]:
        """Fetch raw data payload from external source or approved fixture."""
        ...

    @abstractmethod
    def validate(self, raw_data: T_Raw) -> bool:
        """Validate raw response structure and data boundary integrity."""
        ...

    @abstractmethod
    def normalize(self, raw_data: T_Raw) -> T_Norm:
        """Transform raw response into canonical internal model."""
        ...

    @abstractmethod
    def classify(self) -> EvidenceClass:
        """Return the authoritative EvidenceClass produced by this adapter."""
        ...

    def record_run(
        self,
        started_at: datetime,
        status: str,
        http_status: Optional[int],
        latency_ms: float,
        records_received: int,
        records_accepted: int,
        records_rejected: int,
        raw_hash: str,
        error_code: Optional[str] = None,
    ) -> AdapterRunRecord:
        """Create and store an operational audit telemetry record."""
        now = datetime.now(timezone.utc)
        record = AdapterRunRecord(
            source_id=self.source_id,
            started_at=started_at,
            completed_at=now,
            status=status,
            http_status=http_status,
            latency_ms=latency_ms,
            records_received=records_received,
            records_accepted=records_accepted,
            records_rejected=records_rejected,
            error_code=error_code,
            raw_hash=raw_hash,
        )
        self.recent_runs.append(record)
        if len(self.recent_runs) > 100:
            self.recent_runs.pop(0)

        if status == "SUCCESS":
            self._consecutive_failures = 0
            self._last_success = now
            provider_metrics.record_success(self.source_id, "fetch", latency_ms / 1000.0)
        else:
            self._consecutive_failures += 1
            self._last_failure = now
            provider_metrics.record_failure(self.source_id, "fetch", error_code or "ADAPTER_ERROR", latency_ms / 1000.0)

        return record

    @property
    def health_status(self) -> AdapterHealthStatus:
        """Current operational health status."""
        if self._consecutive_failures >= 5:
            return AdapterHealthStatus.FAILED
        if self._consecutive_failures > 0:
            return AdapterHealthStatus.DEGRADED
        return AdapterHealthStatus.ONLINE


class OfficialWarningAdapter(OperationalDataAdapter[str, List[NormalizedOfficialAlert]]):
    """Authoritative adapter for official severe weather warnings (IMD CAP / NDMA SACHET)."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(source_id="IMD", settings=settings)
        from app.adapters.imd.client import IMDWarningProvider
        self.provider = IMDWarningProvider(self.settings)

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.OFFICIAL

    def classify(self) -> EvidenceClass:
        return EvidenceClass.OFFICIAL_WARNING

    async def fetch(
        self,
        district_name: Optional[str] = None,
        state_name: Optional[str] = None,
        raw_fixture: Optional[str] = None,
        **kwargs,
    ) -> AdapterFetchResult[str]:
        """Fetch raw CAP XML alerts from live feed or verified fixture."""
        started_at = datetime.now(timezone.utc)
        url = self.settings.imd_cap_url

        if raw_fixture is not None:
            raw_hash = compute_payload_hash(raw_fixture)
            latency = 1.0
            self.record_run(
                started_at=started_at,
                status="SUCCESS",
                http_status=200,
                latency_ms=latency,
                records_received=1,
                records_accepted=1,
                records_rejected=0,
                raw_hash=raw_hash,
            )
            return AdapterFetchResult(
                raw_payload=raw_fixture,
                raw_hash=raw_hash,
                retrieval_time=started_at,
                source_status=DataSourceStatus.HISTORICAL,
                http_status=200,
                latency_ms=latency,
                endpoint_uri="fixture://cap_xml",
            )

        validate_outbound_url(url)
        client = await self.provider._get_client()
        headers = {}
        if self.settings.imd_api_key:
            headers["Authorization"] = f"Bearer {self.settings.imd_api_key}"

        try:
            resp = await self.provider.executor.execute_request(
                client=client,
                method="GET",
                url=url,
                operation="cap_alerts",
                headers=headers,
            )
            raw_xml = resp.text
            raw_hash = compute_payload_hash(raw_xml)
            latency = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0

            self.record_run(
                started_at=started_at,
                status="SUCCESS",
                http_status=resp.status_code,
                latency_ms=latency,
                records_received=1,
                records_accepted=1,
                records_rejected=0,
                raw_hash=raw_hash,
            )
            return AdapterFetchResult(
                raw_payload=raw_xml,
                raw_hash=raw_hash,
                retrieval_time=started_at,
                source_status=DataSourceStatus.LIVE,
                http_status=resp.status_code,
                latency_ms=latency,
                endpoint_uri=url,
            )
        except Exception as e:
            latency = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0
            self.record_run(
                started_at=started_at,
                status="FAILED",
                http_status=500,
                latency_ms=latency,
                records_received=0,
                records_accepted=0,
                records_rejected=1,
                raw_hash="",
                error_code=type(e).__name__,
            )
            raise

    def validate(self, raw_data: str) -> bool:
        if not raw_data or not raw_data.strip():
            return False
        if len(raw_data) > 5 * 1024 * 1024:
            return False
        return "<alert" in raw_data or "<feed" in raw_data

    def normalize(self, raw_data: str) -> List[NormalizedOfficialAlert]:
        from app.adapters.imd.parser import parse_cap_xml
        return parse_cap_xml(raw_data)

    def ingest_to_evidence(
        self,
        alert: NormalizedOfficialAlert,
        raw_hash: str,
        raw_xml_snippet: Optional[str] = None,
        source_status: DataSourceStatus = DataSourceStatus.LIVE,
    ) -> EvidenceRecord:
        """Transforms NormalizedOfficialAlert into canonical EvidenceRecord via EvidenceService."""
        retrieval_time = datetime.now(timezone.utc)

        def _parse_dt(iso_str: Optional[str]) -> Optional[datetime]:
            if not iso_str:
                return None
            try:
                return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            except Exception:
                return None

        issue_dt = _parse_dt(alert.effective_time_iso or alert.sent_time_iso) or retrieval_time
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

        raw_payload = {
            "alert_id": alert.alert_id,
            "sender": alert.sender,
            "sent": alert.sent_time_iso,
            "severity": alert.severity,
            "warning_level": alert.warning_level.value,
            "raw_hash": raw_hash,
            "source_status": source_status.value,
            "official_text": alert.description or alert.headline,
        }

        # Check for expired alert
        custom_flags: List[str] = []
        if expires_dt and expires_dt < datetime.now(timezone.utc):
            custom_flags.append("EXPIRED_VALIDITY")

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
                "source_status": source_status.value,
            },
            normalized_unit="CAP_1.2",
            temporal=temporal,
            spatial=spatial,
            raw_payload=raw_payload,
            product_id="IMD_CAP_BULLETIN",
            endpoint_uri="https://sachet.ndma.gov.in/cap",
            custom_flags=custom_flags,
        )


class OperationalWeatherAdapter(OperationalDataAdapter[Dict[str, Any], NormalizedWeatherObservation]):
    """Operational adapter for surface observations and multi-provider forecasts."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(source_id="OPEN_METEO", settings=settings)
        from app.adapters.strategy import WeatherProviderManager
        self.manager = WeatherProviderManager(self.settings)

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    def classify(self) -> EvidenceClass:
        return EvidenceClass.OBSERVATION

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        raw_fixture: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AdapterFetchResult[Dict[str, Any]]:
        """Fetch current surface weather observation."""
        started_at = datetime.now(timezone.utc)
        if raw_fixture is not None:
            raw_hash = compute_payload_hash(raw_fixture)
            latency = 1.0
            self.record_run(
                started_at=started_at,
                status="SUCCESS",
                http_status=200,
                latency_ms=latency,
                records_received=1,
                records_accepted=1,
                records_rejected=0,
                raw_hash=raw_hash,
            )
            return AdapterFetchResult(
                raw_payload=raw_fixture,
                raw_hash=raw_hash,
                retrieval_time=started_at,
                source_status=DataSourceStatus.HISTORICAL,
                http_status=200,
                latency_ms=latency,
                endpoint_uri=f"geo:{latitude},{longitude}",
            )

        try:
            obs = await self.manager.get_current_observation(latitude, longitude)
            raw_dict = obs.model_dump()
            raw_hash = compute_payload_hash(raw_dict)
            latency = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0

            source_status = DataSourceStatus.FALLBACK if obs.authority == ProviderAuthority.FALLBACK else DataSourceStatus.LIVE

            self.record_run(
                started_at=started_at,
                status="SUCCESS",
                http_status=200,
                latency_ms=latency,
                records_received=1,
                records_accepted=1,
                records_rejected=0,
                raw_hash=raw_hash,
            )
            return AdapterFetchResult(
                raw_payload=raw_dict,
                raw_hash=raw_hash,
                retrieval_time=started_at,
                source_status=source_status,
                http_status=200,
                latency_ms=latency,
                endpoint_uri=f"geo:{latitude},{longitude}",
            )
        except Exception as e:
            latency = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0
            self.record_run(
                started_at=started_at,
                status="FAILED",
                http_status=500,
                latency_ms=latency,
                records_received=0,
                records_accepted=0,
                records_rejected=1,
                raw_hash="",
                error_code=type(e).__name__,
            )
            raise

    def validate(self, raw_data: Dict[str, Any]) -> bool:
        if not isinstance(raw_data, dict):
            return False
        # Coordinates must be valid
        lat = raw_data.get("latitude")
        lon = raw_data.get("longitude")
        if lat is None or lon is None:
            return False
        if not (-90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0):
            return False
        return True

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedWeatherObservation:
        payload = dict(raw_data)
        if "relative_humidity_pct" not in payload and "humidity_pct" in payload:
            payload["relative_humidity_pct"] = payload.pop("humidity_pct")
        if "data_source" not in payload:
            payload["data_source"] = payload.get("provider", "open_meteo")
        return NormalizedWeatherObservation(**payload)

    def ingest_to_evidence(
        self,
        obs: NormalizedWeatherObservation,
        raw_hash: str,
        source_status: DataSourceStatus = DataSourceStatus.LIVE,
    ) -> List[EvidenceRecord]:
        """Convert NormalizedWeatherObservation into canonical EvidenceRecords."""
        from app.evidence.ingestion import ingest_observation_to_evidence
        raw_payload = obs.model_dump()
        raw_payload["raw_hash"] = raw_hash
        raw_payload["source_status"] = source_status.value
        return ingest_observation_to_evidence(obs, raw_payload=raw_payload)


# Singleton instances for operational use
official_warning_adapter = OfficialWarningAdapter()
operational_weather_adapter = OperationalWeatherAdapter()
