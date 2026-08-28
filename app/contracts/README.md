# Data Contracts & Schemas (`app/contracts/`)

## 1. Purpose
Defines the strict, authoritative Pydantic v2 data models for all system inputs, outputs, inter-component messages, tool invocations, and error payloads.

## 2. Responsibilities
- Guarantee data integrity between client requests, Auto Router, Domain Brains, Tool Gateway, and API endpoints.
- Enforce domain boundary constraints (e.g. Indian geographical coordinates bounding box: Lat 6.0°–38.0°N, Lon 68.0°–98.0°E).
- Provide RFC 7807 problem detail error structures.

## 3. Important Files
- `request.py`: `ClientRequestSchema` and `NormalizedRequestSchema`.
- `response.py`: `FinalResponseSchema`, `Recommendation`, `VisualizationSpec`, `SourceCitation`, and `ConfidenceInfo`.
- `brain.py`: `BrainRequest` and `BrainResponse`.
- `evidence.py`: `EvidencePackage`, `OfficialAlert`, and `ProvenanceItem`.
- `tool.py`: `ToolCallRequest`, `ToolCallResponse`, and `ToolDefinition`.
- `location.py`: `LocationContext` with bounding box validations.
- `temporal.py`: `TemporalWindow` with ISO 8601 validation.
- `personalization.py`: `FarmerPersonalizationContext` and `ResearcherPersonalizationContext`.
- `enums.py`: Core enumerations (`BrainType`, `SupportedLanguage`, `AdvisoryAction`, `WarningLevel`).
- `error.py`: `ErrorDetail` and `ProblemDetailRFC7807`.

## 4. Invariants
- All cross-module communication is strictly typed and validated using Pydantic v2.
- No loose, untyped dictionaries are passed across architectural boundaries.
