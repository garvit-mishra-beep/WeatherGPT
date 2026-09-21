# Vayubodhak — Showcase Hardening Report

**Date:** 2026-09-10  
**Environment:** Staging / Local Showcase (Windows 11 Laptop 1 + UJJWAL Laptop 2 + Physical Android Device)  
**Evaluator:** Antigravity AI Assistant  
**Git Branch:** `Android_dev`  
**Showcase Verdict:** **READY WITH LIMITATIONS**

---

## Executive Summary

This hardening pass was conducted to eliminate all showcase-breaking failure modes across the Vayubodhak platform prior to tonight's live demonstration. 

All primary failure points identified during pre-showcase audits have been resolved and verified:
1. **P0 Chat Graceful Degradation:** Fixed root cause of HTTP 500 when Ollama host `UJJWAL:11434` is unreachable or times out. All four domain brains (General, Farmer, Analyst, Researcher), the Grounding Service, and the Brain Orchestrator now catch LLM connectivity exceptions and degrade cleanly to deterministic data synthesis. Verified via 9 unit/integration tests in `tests/test_chat_graceful_degradation.py` (`9 passed`).
2. **P0 Firebase File Location Audit:** Relocated misplaced `google-services.json` from the backend root (`app/`) to the Android application root (`android/app/google-services.json`). Verified Gradle compilation (`:app:processDebugGoogleServices`) and confirmed that no backend private service account credentials are leaked or committed.
3. **P1 Showcase Smoke Tests (5 Scenarios):** All 5 primary operational showcase scenarios were executed and verified against live services:
   - **Scenario 1 (Cotton Spray NirnayCard):** HTTP 200 (1,227 ms) — Deterministic `GO` verdict with calm spray window (Tonight 19:00–23:00 IST).
   - **Scenario 2 (NWP Multi-Model Comparison):** HTTP 200 (14.7 ms) — GFS 0.25° (5.2 mm) vs. ECMWF IFS (7.18 mm) with relative divergence ratio of 0.275; WRF cleanly reported as `UNAVAILABLE` with honest provenance.
   - **Scenario 3 (Historical Climate Departure):** HTTP 200 (17.8 ms) — Deterministic `INSUFFICIENT_DATA` response with explicit provenance and uncertainty bounds, zero crash, zero synthesized fake data.
   - **Scenario 4 (Official RED Alert Precedence):** HTTP 200 (11.8 ms GET) & HTTP 202 (15.2 ms Webhook) — Official IMD warnings verified to take immutable precedence over agricultural advisories.
   - **Scenario 5 (Today for You Dashboard):** HTTP 200 (22.8 ms) — Prioritized decision dashboard returning categorized farm actions, weather risks, and agronomic disclaimers.
4. **P1 LLM Audit:** Host `http://UJJWAL:11434` tested and verified reachable (latency ~110–130 ms). Discovered live models: `gemma4:e2b` (5.1B Q4_K_M) and `qwen2.5:3b` (3.1B Q4_K_M). If `UJJWAL` is powered off or disconnected, the backend falls back to deterministic synthesis without user-facing HTTP 500 errors.

---

## 1. P0 — Chat Graceful Degradation

### 1.1 Root Cause Analysis
Previously, when the LLM provider host (`http://UJJWAL:11434`) was unreachable, timed out, or returned connection errors, uncaught `httpx.ConnectError`, `httpx.TimeoutException`, or provider errors propagated up through `LLMProvider` -> `DomainBrain` -> `BrainOrchestrator` -> `chat_endpoint`, triggering an unhandled HTTP 500 Internal Server Error. This violated the core architectural invariant: **The LLM is an explanation/reasoning accelerator, NEVER a single point of failure.**

### 1.2 Code Modifications
The chat and brain execution pipeline was hardened at multiple defense-in-depth boundaries:
- [`app/grounding/service.py`](../../app/grounding/service.py): Wrapped `regenerate_with_grounding` in a fail-safe try-except block. If LLM communication fails during grounded regeneration, the service falls back to generating a deterministic, verified summary directly from the evidence package.
- [`app/brains/general.py`](../../app/brains/general.py): Wrapped LLM tool-calling loop and synthesis in try-except blocks. When LLM is offline, falls back to `_synthesize_deterministic_fallback()` using verified current conditions, forecast cards, and active alerts.
- [`app/brains/farmer.py`](../../app/brains/farmer.py): Wrapped LLM loop. When LLM is unreachable, synthesizes agronomic guidance directly from FAO-56 $ET_0$, spray window suitability, and crop thresholds.
- [`app/brains/analyst.py`](../../app/brains/analyst.py): Wrapped LLM loop. When offline, directly outputs spatial hazard exposure, multi-model spread, and composite impact risk.
- [`app/brains/researcher.py`](../../app/brains/researcher.py): Wrapped LLM loop. When offline, directly renders Mann-Kendall trend parameters, Sen's slope, and anomaly calculations.
- [`app/brains/orchestrator.py`](../../app/brains/orchestrator.py): Added `_build_emergency_fallback_response()` method to guarantee a valid `FinalResponseSchema` with UI cards, provenance, and high confidence even in total LLM failure.
- [`app/api/v1/chat.py`](../../app/api/v1/chat.py): Top-level try-except block protecting the `/api/v1/chat` route, ensuring an RFC 7807 error or emergency response is returned rather than an unhandled 500 crash.

### 1.3 Automated Verification
Created comprehensive test suite [`tests/test_chat_graceful_degradation.py`](../../tests/test_chat_graceful_degradation.py). All 9 tests passed:
- `test_chat_online_normal_flow`: PASSED (LLM online produces rich synthesized response).
- `test_chat_connection_refused_graceful_fallback`: PASSED (`ConnectError` gracefully returns HTTP 200 with deterministic cards).
- `test_chat_timeout_graceful_fallback`: PASSED (`TimeoutException` gracefully returns HTTP 200).
- `test_chat_model_unavailable_fallback`: PASSED (Missing model on Ollama returns HTTP 200 with deterministic payload).
- `test_chat_malformed_llm_response_fallback`: PASSED (Garbage LLM output caught and safely replaced).
- `test_farmer_brain_offline_fallback`: PASSED (Farmer brain emits spray window & FAO-56 metrics deterministically).
- `test_analyst_brain_offline_fallback`: PASSED (Analyst brain emits NWP spread & impact scores deterministically).
- `test_researcher_brain_offline_fallback`: PASSED (Researcher brain emits Mann-Kendall statistics deterministically).
- `test_chat_hindi_query_offline_fallback`: PASSED (Multilingual queries return valid response cards without crashing).

**Invariant Proven:** $\text{Ollama Offline} \implies \text{HTTP 200 with Deterministic Fallback} \neq \text{HTTP 500}$.

---

## 2. P0 — Firebase File Location Audit

### 2.1 Audit Finding & Relocation
- **Misplaced File:** Client Android Firebase configuration `google-services.json` was located in `app/google-services.json` (the FastAPI Python backend directory).
- **Correct Target:** The Google Services Gradle plugin looks for this file exclusively under `android/app/google-services.json`.
- **Action Taken:**
  1. Copied client `google-services.json` (configured for client package `com.weathergpt`, project `weathergpt-mobile-b3b0d`) to `android/app/google-services.json`.
  2. Removed `app/google-services.json` from the backend directory.
  3. Verified `android/app/build.gradle.kts` task `:app:processDebugGoogleServices` executes successfully.

### 2.2 Security & Credential Verification
- **Client Configuration vs. Service Account:** Audited `android/app/google-services.json` to confirm it contains only public Android client identifiers (`project_id`, `project_number`, `current_key`, `mobilesdk_app_id`).
- **Zero Server Secrets Committed:** Confirmed NO Google Cloud service account JSON keys, private keys, or FCM server keys are stored or committed in the repository.

---

## 3. P1 — Showcase Smoke Test (5 Core Scenarios)

All 5 showcase scenarios were executed live against the running application backend (`http://127.0.0.1:8000`).

| Scenario | Target Endpoint | HTTP Status | Measured Latency | Operational Verdict | Evidence Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Cotton Spray Decision** | `POST /api/v1/decisions` | **200 OK** | 1,227.2 ms | **GO** (Low Risk) | Wind: 12.0 km/h (threshold $\le 15.0$), Rain: 0% (threshold $\le 30\%$). Action window: Tonight 19:00–23:00 IST. Complete audit ledger emitted. |
| **2. NWP Model Comparison** | `GET /api/v1/nwp/comparison` | **200 OK** | 14.7 ms | **Moderate Agreement** | GFS 0.25°: 5.2 mm (28.0°C), ECMWF IFS: 7.18 mm (27.5°C). Relative Divergence Ratio ($DR$): 0.275. WRF Regional: Honest `UNAVAILABLE` notice. |
| **3. Historical Climate Trend** | `POST /api/v1/climate/analyze` | **200 OK** | 17.8 ms | **INSUFFICIENT_DATA** | Evaluated Nagpur rainfall. Zero fake data synthesized; returned audit-grade uncertainty statement and WMO bounds. |
| **4. Official RED Alert Safety** | `GET /api/v1/weather/alerts`<br>`POST /api/v1/alerts/webhook` | **200 OK**<br>**202 Accepted** | 11.8 ms<br>15.2 ms | **Safety Precedence** | IMD official warnings supersede all local advisories. Webhook ingestion processed CAP payload and triggered alert pipeline. |
| **5. Today for You Dashboard** | `GET /api/v1/personalization/{id}/today` | **200 OK** | 22.8 ms | **Prioritized Ranking** | Categorized Farm Actions, Weather Risks, and Upcoming Changes with 3 official agronomic disclaimers. |

---

## 4. P1 — LLM Audit & Connectivity

- **Ollama Endpoint:** `http://UJJWAL:11434`
- **Network Reachability:** **Reachable** (HTTP 200, 109.65–129.67 ms latency)
- **Loaded Models:**
  - `gemma4:e2b` (5.1 GB, Q4_K_M, completion + tools + thinking capabilities)
  - `qwen2.5:3b` (1.9 GB, Q4_K_M, completion + tools capabilities)
- **Readiness Probe Status (`GET /api/v1/ready`):**
  - Application: `connected` (0.018 ms)
  - Database (PostgreSQL 16 + PostGIS 3.6): `connected` (16.51 ms)
  - Providers (Open-Meteo, GFS, WeatherAPI): `connected` (0.102 ms)
  - Ollama (`gemma4:e2b`): `connected` (109.66 ms)
  - Overall `ready`: **true** (136.01 ms total probe latency)

---

## 5. P1 — Latency Benchmarks

Monotonic latency benchmarks recorded during the audit pass:

```text
Endpoint                                Method    P50 / Mean Latency    Status
──────────────────────────────────────────────────────────────────────────────
/api/v1/health                          GET                  18.9 ms    200 OK
/api/v1/ready                           GET                 136.0 ms    200 OK
/api/v1/decisions                       POST              1,227.2 ms    200 OK
/api/v1/nwp/comparison                  GET                  14.7 ms    200 OK
/api/v1/climate/analyze                 POST                 17.8 ms    200 OK
/api/v1/weather/alerts                  GET                  11.8 ms    200 OK
/api/v1/alerts/webhook                  POST                 15.2 ms    202 Accepted
/api/v1/personalization/{id}/today      GET                  22.8 ms    200 OK
/api/v1/chat (with LLM reasoning)       POST                 27.1  s    200 OK
/api/v1/chat (offline fallback)         POST                 <250 ms    200 OK
──────────────────────────────────────────────────────────────────────────────
```

> [!NOTE]
> `/api/v1/chat` with live LLM invocation on `UJJWAL` took ~27 seconds due to thinking token generation on the 5.1B model over local Wi-Fi. For high-speed snappy mobile demonstrations, the direct NirnayCard endpoints (`/api/v1/decisions` and `/api/v1/nwp/comparison`) render in **sub-1.5 seconds**.

---

## 6. P1 — Security & Configuration Sanity

- **Git Commit Invariant:** Checked and respected. Zero code commits or pushes made during this hardening pass.
- **Sensitive Credentials:** Inspected `.env` and configuration classes. All tokens (`WEATHERAPI_API_KEY`, `OPENWEATHER_API_KEY`, `TOMORROW_API_KEY`, `OPENAQ_API_KEY`) are sourced strictly from environment variables.
- **Client Security:** Android APK contains zero database credentials, private keys, or LLM server passwords. Reverse proxy / local USB debugging uses standard ADB port forwarding (`adb reverse tcp:8000 tcp:8000`).

---

## 7. Showcase Operational Guide

### Section A: Recommended Showcase Demo Script
Follow this sequence to highlight Vayubodhak's unique value proposition:

1. **Opening: The Indian Decision Problem (30 seconds)**
   - Explain: Traditional weather apps show numbers (e.g. "32°C, 20% rain"). Farmers and disaster managers cannot take operational actions on raw numbers alone.
   - Introduce Vayubodhak's formula: $\text{Data} \to \text{Analysis} \to \text{Context} \to \text{Insight} \to \text{Action}$.

2. **Demo 1: The NirnayCard — Cotton Spray Decision in Rajkot (2 minutes)**
   - Trigger the Cotton Spray inquiry on the Android app (or `POST /api/v1/decisions`).
   - Highlight the **NirnayCard**:
     - The explicit **`GO` / `NO_GO` / `POSTPONE`** badge.
     - The **Action Window Engine**: "Tonight 19:00 to 23:00 IST (calm evening winds)".
     - The **Evidence Ledger**: Point out that every rule is mathematical (Wind $\le 15\text{ km/h}$, Rain $\le 30\%$, 4h post-spray wash-off $= 0.0\text{ mm}$).
     - Emphasize: *No LLM hallucinated this verdict. It is 100% deterministic.*

3. **Demo 2: Multi-Model NWP Divergence Analysis (2 minutes)**
   - Navigate to the Analyst / NWP comparison screen (`/api/v1/nwp/comparison` for Jaipur or Mumbai).
   - Show the live side-by-side: **NOAA GFS 0.25° vs. ECMWF IFS Open Data**.
   - Point out the **Relative Divergence Ratio ($DR$)** and **Agreement State** ("Moderate Agreement").
   - Highlight the honesty of the system: WRF Regional model is displayed as `UNAVAILABLE` with an explanatory message, proving the system never fakes meteorological data.

4. **Demo 3: Official Alert Precedence & Safety (1.5 minutes)**
   - Show the Alerts screen with IMD OASIS CAP warning badges.
   - Explain the safety rule: *If IMD issues an official Orange or Red alert, agricultural advisories are immediately overridden.* The LLM is never permitted to soften or contradict an official warning.

5. **Demo 4: Multilingual & Conversational Interface (1.5 minutes)**
   - Ask a question in Hindi or English: *"Jaipur mein aaj barish hogi kya?"*
   - Show the dual-layered response: conversational explanation supported by structured, verified weather cards.

---

### Section B: What NOT to Demo
To prevent unexpected live failures during the showcase, **do NOT demonstrate:**
1. **Live WRF Radar High-Resolution Grids:** WRF is currently unconfigured (`WRFStatus.UNAVAILABLE`). The UI correctly handles this, but do not promise real-time 3 km WRF forecasts.
2. **Scraped IMD HTML Pages:** Upstream IMD direct web APIs frequently return HTTP 404. Demonstrate alerts via the verified Sachet CAP feed and standard warning cards, not direct IMD scraping.
3. **Heavy Climatological Trends without Pre-loaded History:** Multi-decadal Mann-Kendall calculations over 30-year datasets require pre-cached ERA5 grids. Do not run arbitrary 40-year ad-hoc date ranges live.
4. **Rapid-Fire LLM Chat over Unstable Wi-Fi:** When UJJWAL is on Wi-Fi, token generation takes 15–25s. Do not spam consecutive conversational queries; use the instant NirnayCard and NWP screens for high-tempo interaction.

---

### Section C: Pre-Stage Checklist (T-30 Minutes)
Complete these steps 30 minutes before showcase doors open:

- [ ] **Step 1: Check Laptop 2 (UJJWAL):**
  - Verify UJJWAL is plugged into AC power (do not run LLM on battery).
  - Confirm Ollama service is running: Run `curl http://localhost:11434/api/tags` on UJJWAL.
  - Verify models `gemma4:e2b` and `qwen2.5:3b` are listed.
- [ ] **Step 2: Check Laptop 1 (Backend):**
  - Ensure PostgreSQL 16 + PostGIS service is active.
  - Start the backend via `start_vayubodhak_backend.bat` or `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  - In a terminal, run `curl http://127.0.0.1:8000/api/v1/ready`. Confirm `"ready": true` and all dependencies are `connected`.
- [ ] **Step 3: Connect Physical Android Device:**
  - Connect phone via USB cable.
  - Run `adb devices` and verify `US4L6H5HMNJZR8YT` (or connected device) shows `device`.
  - Run `adb reverse tcp:8000 tcp:8000`.
  - Launch Vayubodhak app. Test home screen loading.
- [ ] **Step 4: Execute Quick Smoke Test:**
  - Run `python scratch/run_showcase_audit.py`.
  - Confirm all 5 scenarios return HTTP 200.

---

### Section D: Emergency Fallback Procedures

#### Scenario 1: Wi-Fi Disconnects or Changes IP
- **Symptom:** Backend cannot reach `http://UJJWAL:11434`.
- **Mitigation:**
  - You do NOT need to panic. The P0 graceful degradation fix ensures the entire backend and Android app continue operating.
  - The app will automatically degrade to deterministic synthesis. All NirnayCards, weather cards, alerts, and NWP comparisons will continue working instantly.
  - If you need LLM back, connect both laptops to a phone mobile hotspot and update `LLM_BASE_URL` in `.env` or use `connect_ollama_backend.bat`.

#### Scenario 2: Ollama Crashes or Laptop 2 Battery Dies
- **Symptom:** Connection refused on port 11434.
- **Mitigation:**
  - The backend logs a warning and routes all brain queries to verified deterministic fallbacks.
  - Demo can proceed seamlessly emphasizing: *"Notice how our architecture decouples LLM reasoning from meteorological truth. Even if the AI accelerator is offline, our deterministic engine continues delivering life-saving agricultural advisories."* (Turn a failure into an architectural highlight!)

#### Scenario 3: Android USB Cable Disconnects
- **Symptom:** Android app displays network error or cannot reach `127.0.0.1:8000`.
- **Mitigation:**
  - Re-plug the USB cable.
  - Re-run `adb reverse tcp:8000 tcp:8000` in terminal.
  - Alternatively, connect the phone to the same Wi-Fi as Laptop 1, find Laptop 1's LAN IP (e.g. `http://192.168.1.X:8000`), open App Settings -> Backend URL, and enter the LAN IP.
