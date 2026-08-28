# Grounding & Hallucination Control (`app/grounding/`)

## 1. Purpose
Enforces factual consistency and grounding between LLM-generated natural language answers and the verified `EvidencePackage`, preventing meteorological hallucinations and unauthorized alert modifications.

## 2. Responsibilities
- Extract verifiable atomic factual claims (temperatures, rainfall quantities, wind speeds, warning levels, sources) from candidate text.
- Verify numerical claims against evidence data within calibrated domain tolerances ($\pm 0.5^\circ\text{C}$, $\pm 1.0\text{ mm}$).
- Prevent official alert fabrications or severity level downgrades.
- Orchestrate bounded correction retries (max 2 attempts) with feedback prompts when grounding violations occur.
- Fallback safely to deterministic template summaries if retries are exhausted.

## 3. Important Files
- `validator.py`: `GroundingValidator` cross-referencing extracted claims against `EvidencePackage`.
- `claims.py`: `ClaimExtractor` extracting numerical quantities, units, alerts, and citations across all 5 Indian languages.
- `prompts.py`: `GroundingPromptBuilder` constructing grounding correction prompts.
- `service.py`: `GroundingService` coordinating validation, retries, and deterministic fallbacks.
- `models.py`: `Claim`, `GroundingResult`, and `ValidationReport` data structures.

## 4. Invariants
- An LLM cannot assert a warning level that does not exist in the evidence.
- An LLM cannot invent or fabricate temperatures or precipitation numbers.
- Grounding verification is enforced across all 5 supported Indian languages and scripts.
