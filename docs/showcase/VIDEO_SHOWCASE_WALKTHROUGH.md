# VAYUBODHAK VIDEO RECORDING — OPERATIONAL WALKTHROUGH

## 1. Executive Summary & Philosophy

This walkthrough instructs the video production team and software engineers on recording a deterministic, production-grade video showcase of **VAYUBODHAK**.

### Core Architecture
```text
Controlled Showcase Dataset (Inputs)
        ↓
Real Evidence Foundation
        ↓
Real Operational Event Engine
        ↓
Real Selective Recalculation Engine
        ↓
Real Decision / Nirnay Engine
        ↓
Real Notification Engine
        ↓
Real Android Sync / Room Cache
        ↓
Production UI (Zero "Demo Mode" Mentions)
```

---

## 2. Pre-Recording Setup & Verification

1. **Start Backend Server**:
   ```powershell
   .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. **Launch Android App on Device / Emulator**:
   * Build APK: `.\android\gradlew.bat -p android assembleDebug`
   * Target Location: Gwalior District, MP (`26.2183°N, 78.1828°E`)
3. **Verify Baseline State Reset**:
   ```powershell
   .venv\Scripts\python.exe scripts\run_showcase.py reset
   ```

---

## 3. Scene-by-Scene Operator Flow

### Scene 1: Introduction & Baseline (Step 0)
* **Operator Action**:
  ```powershell
  .venv\Scripts\python.exe scripts\run_showcase.py start
  ```
* **System Execution**:
  * Ingests `weather_initial.json` (3.0mm rain, 28.5°C).
  * Runs full canonical pipeline: Evidence → Hazard (0.12) → Exposure → Vulnerability → Risk (LOW) → Decision: `MONITOR` (Revision 1).
  * Dispatches event `EVT-SHOWCASE-001` (seq 1).
* **On Camera / App Focus**:
  * Show **Nirnay Card**: Verdict `MONITOR`, Severity `LOW`.
  * Highlight text: *"Atmospheric conditions nominal. Routine agricultural operations may proceed."*
  * Tap **Researcher Brain**: Show verified provenance, valid observation timestamp, and source quality (`VALID`, `FRESH`).
  * Tap **Farmer Brain**: Show advisory indicating favorable field windows.

### Scene 2: Precipitation Escalation & Selective Recalculation (Step 1)
* **Operator Action**:
  ```powershell
  .venv\Scripts\python.exe scripts\run_showcase.py next
  ```
* **System Execution**:
  * Ingests `weather_rain_increase.json` (88.5mm rain, 42.0 km/h wind).
  * Change Detector identifies precipitation threshold crossing (> 2.5mm delta and > 64.5mm heavy rain threshold).
  * **Selective Recalculator**: Reuses Exposure and Vulnerability cache; recomputes Hazard (0.58) and Risk (MODERATE).
  * Creates `DecisionRevision` 2 (`REV-SHOWCASE-002`).
  * Dispatches Notification: `Decision Update [PROCEED_WITH_CAUTION]: Gwalior District`.
* **On Camera / App Focus**:
  * Show incoming Notification banner on Android.
  * Tap notification: Nirnay card updates dynamically to `PROCEED_WITH_CAUTION`, Severity `MODERATE`.
  * Open **Analyst Brain**: Point out the live pipeline trace highlighting:
    * `HAZARD` recomputed.
    * `EXPOSURE` and `VULNERABILITY` preserved from cache.
    * `RISK` escalated.

### Scene 3: Authoritative Red Warning Escalation (Step 2)
* **Operator Action**:
  ```powershell
  .venv\Scripts\python.exe scripts\run_showcase.py next
  ```
* **System Execution**:
  * Ingests `warning_update.json` (IMD Statutory Red Alert).
  * Evaluates statutory alert; overrides hazard to `HIGH` (0.85).
  * Triggers safety rule `DEC-RULE-ROAD-VERIFY-001` (NH-44 & SH-19 inundation risk).
  * Creates `DecisionRevision` 3 (`REV-SHOWCASE-003`).
  * Dispatches High-Priority Notification: `[OFFICIAL ALERT] RED Warning: Gwalior District`.
* **On Camera / App Focus**:
  * Show Red Warning notification.
  * Nirnay card updates to `POSTPONE`, Severity `HIGH`.
  * Highlight binding action: *"Halt outdoor operations. Road flooding risk on NH-44."*

### Scene 4: Offline Resilience & Graceful Degradation (Step 3)
* **Operator Action**:
  * Disconnect Wi-Fi / Enable Airplane Mode on Android device, OR run:
  ```powershell
  .venv\Scripts\python.exe scripts\run_showcase.py next
  ```
* **System Execution**:
  * Android `SystemResilienceManager` detects network loss (`OFFLINE`).
  * `OperationalSyncManager` switches to local Room database cache.
* **On Camera / App Focus**:
  * Show status pill transitions to **"OFFLINE"**.
  * Crucial verification: The app **never** hides data or claims stale data is live. It clearly displays:
    * `Last Verified Assessment`: `POSTPONE` (Revision 3)
    * `Source Status`: `Verified Offline Cache`
    * Exact timestamp of last verified synchronization.

### Scene 5: Network Recovery & Re-synchronization (Step 4)
* **Operator Action**:
  * Turn off Airplane Mode / Reconnect Wi-Fi, OR run:
  ```powershell
  .venv\Scripts\python.exe scripts\run_showcase.py next
  ```
* **System Execution**:
  * Connectivity restored: `OperationalSyncManager.onConnectivityRestored()` triggers handshake.
  * Sends client cursor (`cursor_seq=2`, `last_synced_revision=2`) to `/api/v1/sync/operational-state`.
  * Server responds with incremental delta (event sequence 3).
  * Android updates local store and updates UI to `FULL_OPERATIONAL`.
* **On Camera / App Focus**:
  * Status indicator switches from **"RECOVERING"** to **"OPERATIONAL"**.
  * Data seamlessly updates without UI glitches or full page reloads.

### Scene 6: LLM Failure Independence
* **Operator Action**:
  * In settings or backend, toggle LLM to simulated failure/offline.
* **System Execution**:
  * Deterministic analytical engines continue calculating Hazard, Exposure, Vulnerability, Risk, and Nirnay.
* **On Camera / App Focus**:
  * Show that Nirnay cards, risk numbers, and impact maps remain 100% functional and authoritative.
  * Only conversational chat indicates fallback to rule-based structured guidance.

---

## 4. Reset Procedure for Repeat Takes

If a take needs to be re-recorded:
```powershell
.venv\Scripts\python.exe scripts\run_showcase.py reset
```
This instantly restores:
1. Scenario step to Baseline.
2. In-memory and persisted pipeline state to Revision 1.
3. Event sequence cursors to 1.
4. Clean state ready for Take 2.

---

## 5. Truthful Voiceover Script Guidance

| Permitted Voiceover Claims | Prohibited Misrepresentations |
| :--- | :--- |
| "Here we demonstrate VAYUBODHAK evaluating a controlled monsoon escalation scenario for Gwalior District." | "This is live, real-time data streaming directly from the Indian Meteorological Department." |
| "The deterministic analytical pipeline recalculates the localized risk based on the ingested precipitation." | "The AI guessed the risk level from the weather report." |
| "When network connectivity is lost, VAYUBODHAK preserves the last verified state in offline cache." | "The app operates completely seamlessly without any internet dependency ever." |
| "Selective recalculation reuses unaffected spatial exposure layers while recomputing dynamic hazard." | "Every screen is instantly updated by an AI model." |
