# Contributing to VAYUBODHAK

Thank you for your interest in contributing to **VAYUBODHAK (वयुबोधक)**. This document outlines our development process, scientific safety invariants, and architectural guidelines.

---

## 1. Safety-Critical Development Invariants

1. **No LLM on the Critical Decision Path**:
   * All disaster hazard levels, quantitative risk scores ($R = H \times E \times V$), exposure estimates, and operational verdicts (**Nirnay**) MUST be computed deterministically using registered Python algorithms.
   * Under no circumstances may an LLM prompt or generative token output dictate risk numbers or safety verdicts.
2. **Statutory Source Authority Rules**:
   * Only officially recognized Tier E0/E1 statutory bodies (IMD, CWC, NDMA, SDMA, DDMA) can issue official public safety alerts or mandatory evacuation decrees.
   * Third-party telemetry sources (Tier E2: Open-Meteo, OpenAQ, GFS) must be labeled as non-authoritative telemetry.
3. **Data-Truth & Offline Resilience**:
   * Stale or cached data must never be masked as live data in user interfaces.
   * When offline, the system must clearly display its last verified state and observation timestamp.
4. **Controlled Showcase Boundaries**:
   * The built-in showcase scenario (`data/showcase/`) is an internal demonstration benchmark.
   * Normal application UI must never display developer/mock terminology (e.g. `"Demo Mode"` or `"Mock Data"`).

---

## 2. Development Workflow & Standards

### Branching & PRs
* Branch from `main` using descriptive naming: `feature/`, `fix/`, `docs/`, `refactor/`.
* PR descriptions must include test results and identify any affected analytical stages.
* Ensure all tests pass before opening a PR.

### Code Style & Formatting
* **Python**: Adhere to PEP 8, Pydantic v2 conventions, and type annotations.
* **Kotlin**: Idiomatic Kotlin, Jetpack Compose best practices, immutable StateFlow architectures.
* **Testing**: Any new analytical feature or calculation rule must be accompanied by deterministic unit tests.

---

## 3. Running Regression Tests

Before submitting changes, execute the full test verification suite:

```bash
# 1. Backend Pytest Suite
pytest tests/ -q

# 2. Showcase Scenario Verification
pytest tests/test_showcase_scenario.py -v

# 3. Android Unit Tests
.\android\gradlew.bat -p android testDebugUnitTest

# 4. Android Build
.\android\gradlew.bat -p android assembleDebug
```
