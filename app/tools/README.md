# Tool Gateway & Catalog (`app/tools/`)

## 1. Purpose
Implements the central deterministic Tool Gateway, permissions authorization matrix, security sanitization, and catalog of 15 standard meteorological, spatial GIS, NWP, analytical, and map-ready tools.

## 2. Responsibilities
- Enforce Brain-to-Tool access control according to `docs/05_TOOL_REGISTRY.md` and `docs/33_TOOL_GATEWAY.md`.
- Sanitize and validate tool arguments against strict JSON Schema parameters and security checks (SQL injection, shell keywords, India bbox coordinates, vertex limits).
- Provide per-tool timeout containment to prevent runaway calls.
- Enforce maximum 2 MB payload size limits on output responses.
- Support concurrent multi-tool execution (`execute_multiple`) with partial error isolation.
- Maintain immutable data provenance (sources, timestamps, methodology) for all tool executions.

## 3. Important Files
- `gateway.py`: `ToolGateway` executing validated tool calls with authorization, security checks, timeouts, and caching.
- `registry.py`: `ToolRegistry` indexing available tools and exporting Brain schemas.
- `base.py`: Abstract `BaseTool` class.
- `policies.py`: `ToolAccessPolicy` implementing the Brain $\to$ Tool authorization matrix.
- `catalog.py`: Standard deterministic tool catalog (15 tools):
  - **Weather:** `resolve_location`, `get_forecast`, `get_current_weather`, `get_weather_alerts`, `get_weather_intelligence`.
  - **GIS / Spatial:** `lookup_boundary`, `intersect_hazard`, `run_gis_analysis`.
  - **NWP:** `get_nwp_data`, `compare_models`.
  - **Analytics:** `calculate_irrigation_advisory`, `check_spray_window`, `run_risk_analysis`, `run_statistics`.
  - **Map:** `generate_map`.
- `errors.py`: Tool-specific RFC-compatible error hierarchy (`ToolSecurityError`, `ToolAuthorizationError`, `ToolArgumentValidationError`, etc.).

## 4. Invariants
- Unauthorized Brain attempts to call restricted tools are strictly rejected with a structured `ToolAuthorizationError`.
- No tool execution can mutate the official IMD warning severity level (`Green`, `Yellow`, `Orange`, `Red`).
- Exact numerical observations and calculations are preserved without distortion or rounding drift.
