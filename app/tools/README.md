# Tool Gateway & Catalog (`app/tools/`)

## 1. Purpose
Implements the central deterministic Tool Gateway, permissions authorization matrix, tool registration lifecycle, and catalog of standard meteorological and analytical tools.

## 2. Responsibilities
- Enforce Brain-to-Tool access control according to `docs/05_TOOL_REGISTRY.md`.
- Sanitize and validate tool arguments against strict JSON Schema parameters.
- Provide per-tool timeout containment (default 10s) to prevent runaway calls.
- Maintain data provenance (sources, timestamps, methodology) for all tool executions.

## 3. Important Files
- `gateway.py`: `ToolGateway` executing validated tool calls with authorization checks.
- `registry.py`: `ToolRegistry` indexing available tools and exporting Brain schemas.
- `base.py`: Abstract `BaseTool` class.
- `policy.py`: `ToolAccessPolicy` implementing the Brain $\to$ Tool authorization matrix.
- `catalog.py`: Standard baseline deterministic tools:
  - `ResolveLocationTool` (`resolve_location`): Gazetteer geocoding.
  - `GetWeatherForecastTool` (`get_forecast`): Multi-variable numerical weather forecasts.
  - `CalculateIrrigationAdvisoryTool` (`calculate_irrigation_advisory`): Dual-coefficient crop water balance.
  - `RunRiskAnalysisTool` (`run_risk_analysis`): Spatial hazard exposure and vulnerability scoring.
- `errors.py`: Tool-specific error hierarchy.

## 4. Invariants
- Unauthorized Brain attempts to call restricted tools are strictly rejected with a structured `ToolUnauthorizedError`.
- No tool execution can mutate the official IMD warning severity level.
