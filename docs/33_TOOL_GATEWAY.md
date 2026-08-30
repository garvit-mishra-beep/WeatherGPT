# 33 — Tool Gateway Integration Specification

**Document:** `docs/33_TOOL_GATEWAY.md`  
**Status:** Completed & Verified  
**Milestone:** B10 — Tool Gateway Integration  
**Authority:** `docs/05_TOOL_REGISTRY.md`, `docs/03_LLM_BRAIN_SPEC.md`, `AGENTS.md`  

---

## 1. Overview & Architecture

The **Tool Gateway** is the single, strictly controlled boundary through which LLM Domain Brains (General, Farmer, Researcher, Analyst) request backend capabilities.

Under WeatherGPT's non-negotiable meteorological invariants:
- The LLM is **NEVER** the source of numerical weather truth, alerts, mathematical calculations, or GIS queries.
- The LLM **NEVER** accesses the database, PostGIS, filesystem, weather providers, NWP binaries, or OS shell directly.
- All capabilities execute deterministically via registered, strongly typed, and permission-checked tools.

```
       ┌───────────────────────────────┐
       │   LLM Domain Brain Reasoner   │
       └──────────────┬────────────────┘
                      │ (ToolCallRequest)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      TOOL GATEWAY                           │
│  1. Registry Lookup & Existence Check                       │
│  2. Brain-to-Tool Authorization Matrix (ToolAccessPolicy)   │
│  3. Security & Safety Sanitization:                         │
│     - Injection rejection (SQL / Shell / Exec)              │
│     - Coordinate bounds validation (India BBox)             │
│     - Geometry size limits (<= 5,000 vertices)              │
│  4. Argument Schema Validation (ToolCallValidator)          │
│  5. Result Caching & Deduplication (ToolResultCache)        │
│  6. Timeout Containment (asyncio.wait_for)                  │
│  7. Payload Size & Schema Enforcement (<= 2MB payload)      │
│  8. Audit Metrics & Provenance Attachment                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
   ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
   │ Weather / GIS   │ │ NWP Engine  │ │ Deterministic   │
   │ Integration     │ │ (GFS/ECMWF) │ │ Analytics / Map │
   └─────────────────┘ └─────────────┘ └─────────────────┘
```

---

## 2. Brain-to-Tool Authorization Matrix

| Tool Name | General Brain | Farmer Brain | Researcher Brain | Analyst Brain | Category |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `resolve_location` | ✅ | ✅ | ✅ | ✅ | Weather / Spatial |
| `get_forecast` | ✅ | ✅ | ✅ | ✅ | Weather |
| `get_current_weather` | ✅ | ✅ | ✅ | ✅ | Weather |
| `get_weather_alerts` | ✅ | ✅ | ✅ | ✅ | Weather / Alerts |
| `get_weather_intelligence`| ✅ | ✅ | ✅ | ✅ | Joint Spatial |
| `lookup_boundary` | ❌ | ❌ | ✅ | ✅ | GIS |
| `intersect_hazard` | ❌ | ❌ | ❌ | ✅ | GIS / Warnings |
| `run_gis_analysis` | ❌ | ❌ | ✅ | ✅ | GIS / Risk |
| `get_nwp_data` | ❌ | ✅ | ✅ | ✅ | NWP |
| `compare_models` | ❌ | ❌ | ✅ | ✅ | NWP / Spread |
| `calculate_irrigation_advisory` | ❌ | ✅ | ❌ | ❌ | Agronomic |
| `check_spray_window` | ❌ | ✅ | ❌ | ❌ | Agronomic |
| `run_risk_analysis` | ❌ | ❌ | ❌ | ✅ | Risk |
| `run_statistics` | ❌ | ❌ | ✅ | ✅ | Climate Trends |
| `generate_map` | ✅ | ✅ | ✅ | ✅ | Map Specification |

---

## 3. Security & Safety Invariants

1. **Dangerous Keyword & SQL Injection Rejection:**
   - Arguments containing keywords (`command`, `exec`, `eval`, `shell`, `__import__`) or SQL patterns (`union select`, `drop table`, `--`, `;`) are intercepted immediately and raise `ToolSecurityError`.
2. **India Bounding Box Enforcement:**
   - All spatial coordinates are validated against the Indian subcontinent bounding box ($6.0^\circ\text{N} \le \text{lat} \le 38.0^\circ\text{N}$ and $68.0^\circ\text{E} \le \text{lon} \le 98.0^\circ\text{E}$). Out-of-bounds coordinates raise `ToolArgumentValidationError`.
3. **Geometry Vertex Ceiling:**
   - Warning and hazard GeoJSON geometries are capped at 5,000 vertices to prevent ReDoS / CPU exhaustion attacks.
4. **Timeout Containment:**
   - Every tool call executes within a strict timeout window ($\min(\text{request.timeout}, \text{tool.default\_timeout}, \text{gateway.timeout})$). Breaches raise `ToolTimeoutError` and release workers.
5. **Payload Size Guard:**
   - Serialized response data payloads cannot exceed 2 MB. Oversized payloads raise `ToolResultValidationError`.
6. **Multi-Tool Batch Execution & Error Isolation:**
   - `execute_multiple(requests, isolate_failures=True)` runs concurrent tool calls while isolating partial failures into individual error response envelopes, preserving deterministic result ordering.
7. **Provenance & Immutability:**
   - Official IMD alert severities (`Green`, `Yellow`, `Orange`, `Red`) and numerical observations/predictions are immutable across the pipeline.
   - All responses attach `ToolProvenance` (sources, retrieval timestamps, validity windows).

---

## 4. Verification & Test Coverage

- **Suite:** `tests/test_tool_gateway.py` (25 tests).
- **Test Scenarios Covered:**
  - Dynamic tool registration, duplicate rejection, and lookup.
  - Brain schema export and authorization enforcement.
  - Missing argument, invalid argument type, and disallowed parameter detection.
  - Security protections (SQL injection, shell execution, out-of-bounds bounds, oversized geometry).
  - Timeout containment and multi-tool failure isolation.
  - End-to-end execution across Weather, GIS, NWP, Analytics, and Map tool categories.
  - Multi-round LLM tool-calling loop with `MockLLMProvider`.
  - Latency smoke test demonstrating sub-15 ms throughput for local deterministic tools.
