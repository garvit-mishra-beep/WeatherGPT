# Tool Result & Evidence Builder (`app/tool_results/`)

## 1. Purpose
Normalizes raw deterministic tool outputs into validated, type-safe evidence packages that provide the single source of factual truth for LLM reasoning and response grounding.

## 2. Responsibilities
- Convert `ToolCallResponse` payloads into `NormalizedToolResult` objects.
- Validate data completeness, freshness, and absence of prompt injections in tool payloads.
- Assemble normalized results, location context, and temporal metadata into unified `EvidencePackage` objects.
- Format tool results for safe insertion into the LLM conversation stream.

## 3. Important Files
- `validator.py`: `ToolResultValidator` validating response status, error conditions, and data freshness.
- `formatter.py`: `ToolResultFormatter` formatting tool outputs safely as JSON strings.
- `evidence_builder.py`: `EvidenceBuilder` constructing `EvidencePackage` instances with preserved provenance and official alerts.
- `handler.py`: `ToolResultHandler` coordinating validation and formatted message assembly.
- `models.py`: `NormalizedToolResult` data contract.

## 4. Invariants
- Official severe weather alerts (`WarningLevel.RED`, `ORANGE`, `YELLOW`, `GREEN`) returned by tools are strictly preserved in `official_alerts`.
- Stale or degraded tool data is transparently flagged in the evidence package's limitations list.
