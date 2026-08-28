# Multilingual Support Layer (`app/multilingual/`)

## 1. Purpose
Provides robust language handling, script detection, code-mixed query understanding, Indic numeral normalization, and standardized meteorological terminology mapping across 5 Indian languages.

## 2. Supported Languages
1. **English (`en`)**
2. **Hindi (`hi` — हिन्दी)**
3. **Bengali (`bn` — বাংলা)**
4. **Marathi (`mr` — मराठी)**
5. **Gujarati (`gu` — ગુજરાતી)**

## 3. Responsibilities
- Detect language and script from Unicode character ranges and romanized transliteration keywords.
- Normalize Indic numerals (e.g. `३३.२`, `৩৩.২`, `૩૩.૨`) to standard ASCII digits (`33.2`) for deterministic tool execution.
- Maintain localized meteorological glossaries to prevent mistranslation of critical terms (e.g. "evapotranspiration", "frost warning").
- Enforce numerical invariance: Scientific measurements remain invariant across all languages.

## 4. Important Files
- `detector.py`: `LanguageDetector` combining Unicode script analysis with code-mixed keyword matching.
- `numerals.py`: `NumeralNormalizer` converting bidirectionally between Indic digits and ASCII numerals.
- `catalog.py`: `TerminologyCatalog` providing standardized meteorological glossaries for 5 languages.
- `service.py`: `MultilingualService` unifying normalization, system prompt generation, and terminology resolution.

## 5. Invariants
- Numerical facts, units, and official alert levels cannot drift or change across language translations.
- Explicit language commands (e.g., "Reply in Marathi") immediately override automatic script detection.
