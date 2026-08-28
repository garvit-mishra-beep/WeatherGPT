# Personalization & Question Logic (`app/personalization/`)

## 1. Purpose
Implements progressive, low-friction personalization for agricultural decision support, asking at most one targeted follow-up question only when strictly necessary.

## 2. Responsibilities
- Evaluate whether missing agronomic context (such as crop name or growth stage) blocks actionable advisory generation.
- Formulate localized, single follow-up questions in the user's preferred language.
- Extract answers from user responses while respecting user refusals ("skip", "not sure", "don't know", "पता नहीं").
- Ensure general consumer forecasts never ask agricultural profiling questions.

## 3. Important Files
- `service.py`: `PersonalizationService` orchestrating question evaluation and answer extraction.
- `policy.py`: `PersonalizationPolicy` defining question rules and refusal triggers.
- `extractor.py`: `AnswerExtractor` extracting crop entities and growth stages across English, Hindi, Bengali, Marathi, and Gujarati.
- `questions.py`: Multilingual catalog of standardized clarification prompts.
- `models.py`: `ClarificationQuestion` and `PersonalizationUpdate` schemas.

## 4. Invariants
- Zero interrogation: Maximum 1 question per turn; never chain multiple profiling questions.
- User refusal ("skip", "not sure") permanently stores a skip flag to prevent asking again in the same session.
