# Phase 9B — Operational Data Adapter Contract Specification

## 1. Primary Contract Overview
Every external operational data source ingested into VAYUBODHAK must implement the canonical `OperationalDataAdapter` contract defined in `app/adapters/operational_adapter.py`.

The flow adheres strictly to:
$$\text{EXTERNAL SOURCE} \longrightarrow \text{ADAPTER FETCH} \longrightarrow \text{RAW PRESERVED} \longrightarrow \text{VALIDATE} \longrightarrow \text{NORMALIZE} \longrightarrow \text{EVIDENCE RECORD}$$

Direct insertion of raw external HTTP payloads into downstream hazard, exposure, vulnerability, or decision engines is strictly prohibited.

---

## 2. Generic Interface Definition

```python
class OperationalDataAdapter(ABC, Generic[T_Raw, T_Norm]):
    source_id: str
    authority: ProviderAuthority

    @abstractmethod
    async def fetch(self, **kwargs) -> AdapterFetchResult[T_Raw]:
        """Fetch raw payload, recording retrieval timestamp and raw SHA-256 hash."""
        ...

    @abstractmethod
    def validate(self, raw_data: T_Raw) -> bool:
        """Validate structural integrity, schema, coordinate bounds, and payload limits."""
        ...

    @abstractmethod
    def normalize(self, raw_data: T_Raw) -> T_Norm:
        """Deterministically map raw fields into canonical VAYUBODHAK models."""
        ...

    @abstractmethod
    def classify(self) -> EvidenceClass:
        """Declare authoritative EvidenceClass (OFFICIAL_WARNING, OBSERVATION, FORECAST, etc.)."""
        ...
```

---

## 3. Cryptographic Raw Data Preservation Contract
For every external response received:
1. **Raw Payload Hash**: The raw response string/bytes/JSON is deterministically hashed using SHA-256 (`sha256_checksum`).
2. **Immutable Storage**: The hash is embedded into both the `AdapterRunRecord` and the canonical `ProvenanceRecord`.
3. **Audit Trail**: The exact un-normalized raw fields (`raw_field`, `raw_value`, `raw_unit`, `raw_payload`) are preserved in the `EvidenceRecord`.
4. **Separation of Concerns**: Normalized values (`normalized_field`, `normalized_value`, `normalized_unit`) exist alongside raw fields, ensuring that subsequent normalization improvements can always be audited against untouched source data.

---

## 4. Deterministic Unit Normalization
All physical parameters must be mapped to standard SI / canonical meteorological units:

| Parameter | Source Unit Example | Standard Unit | Deterministic Conversion Formula |
| :--- | :--- | :--- | :--- |
| **Temperature** | Fahrenheit (°F) / Kelvin (K) | Celsius (°C) | $T_{^\circ\text{C}} = (T_{^\circ\text{F}} - 32) \times \frac{5}{9}$ or $T_{^\circ\text{C}} = T_{\text{K}} - 273.15$ |
| **Rainfall** | Inches / mm per hour | Millimeters (mm) | $R_{\text{mm}} = R_{\text{in}} \times 25.4$ |
| **Wind Speed** | Knots (kt) / mph / m/s | km/h | $W_{\text{km/h}} = W_{\text{kt}} \times 1.852$ or $W_{\text{km/h}} = W_{\text{m/s}} \times 3.6$ |
| **Atmospheric Pressure** | inHg / bar | hPa (mbar) | $P_{\text{hPa}} = P_{\text{inHg}} \times 33.8639$ |
| **Warning Severity** | CAP Severity / Text | IMD Color Code | Green, Yellow, Orange, Red |

Conversions are deterministic and recorded with `conversion_method` and `conversion_version`.

---

## 5. Non-Collapsing Temporal Identity Contract
Every adapter must populate the strict `TemporalIdentity` schema:
- `retrieval_time`: Exact UTC timestamp when VAYUBODHAK ingested the response.
- `issue_time`: Official publication timestamp by the issuing authority.
- `observation_time`: Physical measurement timestamp by the weather sensor/radar.
- `valid_from`: Beginning of the forecast/warning validity window.
- `valid_to`: Expiration timestamp of the forecast/warning window.

**CRITICAL RULE**: `retrieval_time` must NEVER be substituted for `observation_time` or `valid_from`. If a source omits a timestamp, the field must remain `None`.

---

## 6. Operational Telemetry (`AdapterRunRecord`)
Every execution emits an `AdapterRunRecord`:
- `adapter_run_id`: Unique identifier (e.g. `RUN-20260921-A9F02B1C`).
- `source_id`: Canonical source ID.
- `started_at` / `completed_at`: UTC execution timestamps.
- `status`: `SUCCESS`, `DEGRADED`, `FAILED`.
- `http_status`: Upstream response code.
- `latency_ms`: Monotonic duration.
- `records_received` / `records_accepted` / `records_rejected`.
- `raw_hash`: SHA-256 hash of external payload.
- `error_code`: High-level error classification.

---

## 7. Security, SSRF Protection & Rate Limiting
1. **SSRF Prevention**: All outbound destination URLs must be server-configured and match `ALLOWED_OPERATIONAL_DOMAINS`. Any request to non-allowlisted hosts raises `SSRFSecurityError` and is rejected.
2. **Payload Bounding**: External responses are limited to a maximum size of 5MB. Oversized payloads are aborted before parsing to prevent memory exhaustion.
3. **Parser Hardening**: XML parsers strictly forbid `<!DOCTYPE` and `<!ENTITY` declarations, preventing XXE and entity expansion attacks.
4. **Circuit Breakers**: Upstream providers are wrapped in a 3-state `CircuitBreaker` (`CLOSED`, `OPEN`, `HALF_OPEN`). 5 consecutive failures open the breaker for a 30-second cooling period.
5. **Bounded Retry**: Transient network failures retry up to 3 times with exponential backoff and randomized jitter. 4xx client errors (e.g. 401, 403, 404) are never retried.
