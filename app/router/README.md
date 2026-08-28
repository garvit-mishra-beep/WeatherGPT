# Auto Router Layer (`app/router/`)

## 1. Purpose
Determines which domain Brain (`General`, `Farmer`, `Researcher`, or `Analyst`) should handle a user request when `target_brain` is set to `AUTO`.

## 2. Responsibilities
- Classify intent from user queries, conversational history, and active context.
- Support multilingual and code-mixed queries across English, Hindi, Bengali, Marathi, and Gujarati.
- Apply confidence thresholds:
  - **High Confidence ($\ge 0.85$):** Direct dispatch to target Brain.
  - **Medium Confidence ($0.60 \le c < 0.85$):** Route to primary candidate while noting secondary intent.
  - **Low Confidence ($< 0.60$):** Generate disambiguation card with selectable domain options.
- Support explicit manual Brain overrides to bypass Auto Router execution.

## 3. Important Files
- `base.py`: Abstract `BaseAutoRouter` definition.
- `llm_router.py`: `LLMAutoRouter` providing LLM-driven structured intent classification.
- `classifier.py`: Confidence threshold evaluation and routing decision logic.
- `disambiguation.py`: `DisambiguationGenerator` building interactive disambiguation choices for low-confidence queries.
- `prompts.py`: Multilingual system prompts and routing few-shot examples.
- `models.py`: `RouterResult` and `RoutingClassification` schemas.

## 4. Invariants
- If the user specifies an explicit `target_brain` (e.g. `BrainType.FARMER`), the Auto Router is completely bypassed.
- Low-confidence classifications never guess silently; they prompt the user with disambiguation options.
