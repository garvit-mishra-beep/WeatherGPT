# Vayubodhak — Final Physical Device Bug Report & Stabilization Audit

## 1. Test Execution Metadata

- **Date:** 2026-09-11
- **Time:** 06:55 IST
- **Host System:** `Garvit-Laptop` (Laptop 1: Windows 11 Home Single Language, AMD Ryzen 7 7840HS, 16 GB RAM)
- **Second Host System:** `UJJWAL` (Laptop 2: Windows 11, Ollama Host)
- **Physical Mobile Device:** OnePlus Nord CE4 (CPH2717)
- **Device Serial:** `US4L6H5HMNJZR8YT`
- **Android Version:** Android 16 (API Level 36, VanillaIceCream)
- **Target Application:** WeatherGPT / Vayubodhak
- **APK Target:** Debug APK (`app-debug.apk`)
- **Demo Mode Active:** `AppConfig.isDemoMode = true`
- **Showcase Region:** Gwalior, Madhya Pradesh (`26.2183°N, 78.1828°E`, Cache Key: `loc_26.22_78.18`)
- **Ollama Engine:** Ollama v0.5.x on Laptop 2 (`169.254.88.2:11434`), bridged via Laptop 1 Hotspot (`192.168.137.1:11434`)
- **Ollama Model:** `gemma4:e2b` (5.1B params, 7.16 GB, Q4_K_M GGUF format)
- **Physical Network:** Phone connected to Laptop 1 Windows Mobile Hotspot (`GarvitHotspot`), Laptop 1 connected to Laptop 2 via physical Ethernet cable.

---

## 2. Executive Summary & Showcase Readiness Verdict

$$\mathbf{SHOWCASE\ READINESS:\ READY}$$

All 9 critical stabilization areas and 11 tracked defects have been completely resolved, unit-tested, and physically verified on the live OnePlus Nord CE4 device (`US4L6H5HMNJZR8YT`):

1. **Zero-Crash Chat (P0 — RESOLVED)**: Chat opens instantaneously under all network conditions (Internet OFF, Backend OFF, Ollama OFF, Laptop 2 disconnected).
2. **Physical Phone $\to$ Hotspot $\to$ Ethernet $\to$ Ollama Pathway (P0 — RESOLVED)**: Phone (`192.168.137.240`) routes through Laptop 1 Hotspot (`192.168.137.1:11434`) across the dedicated TCP bridge daemon (`scripts/ethernet_ollama_bridge.py`) directly to Laptop 2 (`169.254.88.2:11434`). Live inference with `gemma4:e2b` confirmed.
3. **100% Offline Weather (P1 — PRESERVED)**: In Demo Mode, zero HTTP/network weather requests occur. Gwalior observations and 3-day forecasts load from local SQLite (`weather_cache`).
4. **Full Scrollable Forecast (P1 — RESOLVED)**: 3-Day, 5-Day, and Hourly forecast cards are completely scrollable with 88dp bottom clearance above navigation bars.
5. **Dynamic Data Graphs (P1 — RESOLVED)**: Static demonstration arrays replaced with real dynamic Canvas line curves reflecting actual cached weather points (34°C, 35°C, 33°C).
6. **Honest WRF Regional Modeling (P1 — RESOLVED)**: Honest status displayed: *"WRF regional data unavailable — Live WRF feed is not configured in this deployment."* Zero fabricated data.
7. **Single Arrow Clean Navigation (P3 — RESOLVED)**: All duplicate arrow indicators (`→ →`) eliminated across the entire Android app.
8. **Explicit Alerts (DEMO MODE) Labeling (P2 — RESOLVED)**: Prominent demo badge, cached source attribution, and safe Green baseline status.
9. **Polished Analyst Dashboard (P2 — RESOLVED)**: Rich 30-day operational risk overview, 6 weather signal chips, dynamic trend curve, and spatial risk breakdown.
10. **Complete Farmer Profile & Settings (P2 — RESOLVED)**: Comprehensive agricultural details (Crop, Stage, Field, Area, Soil, FAO-56 Moisture) and privacy guarantees.
11. **Canonical Spray Threshold Alignment (P2 — RESOLVED)**: Android domain evaluation aligned to canonical specification $\text{PoP} \le 30\%$.

---

## 3. Physical Network Topology Validation

```text
Phone (OnePlus Nord CE4)
   │
   │ Wi-Fi: "GarvitHotspot" (WPA2-Personal, 192.168.137.240)
   ▼
Laptop 1 (Garvit-Laptop)
   │ • Hotspot Gateway: 192.168.137.1
   │ • TCP Bridge Daemon (0.0.0.0:11434 -> 169.254.88.2:11434)
   │ • FastAPI Backend (http://0.0.0.0:8000)
   │
   │ Physical Ethernet Cable (High Speed LAN)
   ▼
Laptop 2 (UJJWAL)
   │ • Ethernet Interface: 169.254.88.2
   │ • Windows Firewall Inbound Rule: TCP 11434
   │ • Ollama Service: OLLAMA_HOST=0.0.0.0:11434
   │ • Foundation Model: gemma4:e2b
```

---

## 4. Comprehensive Bug Tracking Matrix

| Bug ID | Title | Severity | Status | Description |
| :--- | :--- | :---: | :---: | :--- |
| **BUG-001** | App Crash when Opening Chat | **P0** | **FIXED** | Interceptor URL rewrite bug & regex compilation fixed; tested offline & online. |
| **BUG-002** | Ollama Phone Connectivity over LAN | **P0** | **FIXED** | TCP socket bridge forwards Hotspot to Ethernet; `gemma4:e2b` verified. |
| **BUG-003** | WRF Regional Modeling Status | **P1** | **FIXED** | Honest unavailable status displayed without fabricating fake curves. |
| **BUG-004** | Static Demonstration Graphs in Data | **P1** | **FIXED** | Graphs dynamically plotted from real cached Gwalior forecast points. |
| **BUG-005** | Full Forecast Clipped by Navigation | **P1** | **FIXED** | Complete scrollable column with 88dp bottom clearance implemented. |
| **BUG-006** | Duplicate Forward Arrows in Buttons | **P3** | **FIXED** | Removed duplicated arrow symbols (`→ →`) across all screens. |
| **BUG-007** | Alerts DEMO Mode Labeling | **P2** | **FIXED** | Prominent "Alerts (DEMO MODE)" badge and honest cached source added. |
| **BUG-008** | Analyst Dashboard Visual Quality | **P2** | **FIXED** | Professional executive dashboard with risk chips, signals, and trend chart. |
| **BUG-009** | Farmer Profile & Settings Incomplete | **P2** | **FIXED** | Rich agricultural details (crop, stage, plot, soil, moisture) exposed. |
| **BUG-010** | Spray Threshold Inconsistency | **P2** | **FIXED** | Aligned code, UI, and tests to canonical specification $\text{PoP} \le 30\%$. |
| **BUG-011** | SIH Showcase Setup Documentation | **P1** | **FIXED** | Comprehensive runbook with topology, IPs, and commands added to README. |

---

## 5. Detailed Bug Reports

### BUG-001 — App Crashes when Opening Chat
- **Severity:** P0 (Demo Blocker)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Cold-launch app on device, tap "⚡ Nirnay: Should I spray cotton tonight?" or the Chat button from Home.
- **Expected:** Chat opens smoothly, displays previous history or initial greetings, loads deterministic NirnayCard without crash.
- **Actual:** `HttpClientFactory` dynamic URL interceptor mistakenly attempted to rewrite requests directed to port 11434, causing an invalid state exception; additionally, regex in `MarkdownText.kt` had malformed escape syntax.
- **Root Cause:**
  1. `HttpClientFactory.kt` lacked bypass logic for local Ollama endpoints (`port 11434` / `/api/chat`).
  2. `MarkdownText.kt` used malformed Kotlin raw string regex escaping `\$\{'\$'}` causing ICU syntax crash.
- **Fix:**
  1. Added header check and port check in `HttpClientFactory.kt` to bypass dynamic URL rewrites for Ollama traffic.
  2. Fixed regex patterns to character classes `[$]`.
  3. Added multi-endpoint fallback list in `WeatherGPTRepositoryImpl.kt` with bounded 5s timeout.
- **Test:** Unit test `MarkdownTextTest.kt` passes; unit test in `WeatherGPTRepositoryImplTest.kt` passes.
- **Physical Validation:** Verified on OnePlus Nord CE4: Chat opened multiple times, zero crashes recorded in Logcat.

---

### BUG-002 — Ollama Phone Connectivity over Hotspot to Ethernet
- **Severity:** P0 (Demo Blocker)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Phone connects to Laptop 1 Wi-Fi hotspot (`192.168.137.240`), Laptop 1 connects to Laptop 2 via Ethernet (`169.254.88.2:11434`). Phone attempts HTTP call to `169.254.88.2:11434`.
- **Expected:** Phone successfully reaches Ollama on Laptop 2 and generates natural-language explanation using `gemma4:e2b`.
- **Actual:** Windows Mobile Hotspot operates on isolated subnet `192.168.137.0/24` and does not forward packets across to the link-local Ethernet adapter `169.254.85.119`.
- **Root Cause:** Subnet segmentation in Windows without cross-adapter routing enabled.
- **Fix:** Developed and deployed Python socket bridge daemon `scripts/ethernet_ollama_bridge.py` on Laptop 1. It listens on `0.0.0.0:11434` on Laptop 1 (reachable by the phone at `192.168.137.1:11434`) and pipes raw bidirectional TCP traffic to `169.254.88.2:11434`. Handled half-duplex socket shutdowns cleanly.
- **Test:** Socket probe from phone to `192.168.137.1:11434` confirmed open; `/api/tags` returned model `gemma4:e2b`.
- **Physical Validation:** Phone successfully executed live generation over `GarvitHotspot` via bridge to Laptop 2 Ollama.

---

### BUG-003 — WRF Regional Modeling Status
- **Severity:** P1 (Major Showcase Defect)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Navigate to Data -> WRF (Regional).
- **Expected:** Honest, professional status card explaining whether WRF data is available or unconfigured without fabricating fake curves.
- **Actual:** Raw error string "High-resolution WRF data stream is not configured."
- **Root Cause:** Missing styled UI card for offline/unconfigured WRF regional modeling.
- **Fix:** Updated `DataScreen.kt` with styled WRF card:
  - Header: "WRF Regional Modeling • High-Resolution Regional Physics • 3-9 km"
  - Status: "Status: WRF regional data unavailable"
  - Reason: "Reason: Live WRF feed is not configured in this deployment."
- **Test:** Unit test in `DataScreenTest.kt` passes.
- **Physical Validation:** Screencap `screen_data_wrf_selected.png` confirms crisp, honest display.

---

### BUG-004 — Static Graphs in Data Section
- **Severity:** P1 (Major Showcase Defect)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Navigate to Data screen and inspect temperature, rain, wind, and humidity trend curves.
- **Expected:** Graphs dynamically plot actual data points from cached Gwalior weather.
- **Actual:** Graphs used hardcoded static arrays.
- **Root Cause:** Hardcoded mock arrays in `DataViewModel.kt`.
- **Fix:** Modified `DataViewModel.kt` to extract real temperatures, rainfall, wind, and humidity from `weather_cache` (3 daily points: 34°C, 35°C, 33°C) and pass them to dynamic Canvas chart components with exact date ranges (`2026-09-10 → 2026-09-13`).
- **Test:** Unit test verifies dynamic point extraction from forecast DTO.
- **Physical Validation:** Screencaps `screen_data.png` and `screen_analyst_scrolled.png` confirm dynamic Canvas rendering.

---

### BUG-005 — Full Forecast Clipped by Navigation Bar
- **Severity:** P1 (Major Showcase Defect)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Navigate to Weather & Forecast screen and scroll to bottom.
- **Expected:** Entire forecast summary and all days visible above the bottom navigation bar.
- **Actual:** Bottom forecast row was clipped behind the navigation bar.
- **Root Cause:** Missing bottom content padding / insets in `WeatherScreen.kt`.
- **Fix:** Added `Spacer(modifier = Modifier.height(88.dp))` at the end of the scrollable column in `WeatherScreen.kt`.
- **Test:** Layout unit test passes.
- **Physical Validation:** Screencap `screen_weather_scrolled.png` shows Forecast Summary card and "See full forecast →" completely above the navigation bar.

---

### BUG-006 — Duplicate Navigation Arrows in Buttons
- **Severity:** P3 (Polish / Visual Defect)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Inspect buttons such as "See full forecast → →" or "Detailed Report → →".
- **Expected:** Exactly one directional arrow per navigation action.
- **Actual:** Buttons rendered both a text unicode arrow `→` and an `Icon(Icons.Default.ArrowForward)`.
- **Root Cause:** Redundant arrow characters in string resources combined with Compose trailing icons.
- **Fix:** Audited all XML string resources (`strings.xml`) and Compose files; removed duplicate unicode arrow characters.
- **Test:** Verified via codebase grep for `→.*→`.
- **Physical Validation:** Confirmed single clean arrows on Weather, Data, and Profile screens.

---

### BUG-007 — Alerts DEMO Mode Labeling
- **Severity:** P2 (UX / Product Invariant)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Tap Alerts tab in Demo Mode.
- **Expected:** Clear labeling that alerts are in Demo Mode from cached baseline without implying active live emergency warnings.
- **Actual:** Generic "Official Weather Alerts" without clear offline indication.
- **Root Cause:** Missing demo badge and cached provenance header in `AlertsScreen.kt` and bottom navigation bar.
- **Fix:**
  1. Updated bottom tab in `BottomNavigationBar.kt` to dynamically show `"Alerts (DEMO)"` in Demo Mode.
  2. Added prominent `Alerts (DEMO MODE)` header card in `AlertsScreen.kt` citing cached source and retrieved timestamp.
  3. Displays honest green safe baseline: *"No cached official alerts available — Official IMD/NDMA status: Green"*.
- **Test:** Unit test `AlertsScreenTest` passes.
- **Physical Validation:** Screencap `screen_alerts.png` confirms prominent DEMO labeling.

---

### BUG-008 — Analyst Dashboard Visual Quality
- **Severity:** P2 (UX / Intelligence Polish)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Navigate to Data -> Quick Access -> Analyst Dashboard.
- **Expected:** Visual hierarchy with operational risk cards, weather signal chips, dynamic trend curve, and spatial breakdown.
- **Actual:** Visually plain dashboard with minimal structure.
- **Root Cause:** Primitive card layout in `AnalystDashboardScreen.kt`.
- **Fix:** Redesigned `AnalystDashboardScreen.kt` with:
  - Header: Dark Navy banner with "30 Days" badge.
  - Summary Cards: Rainfall total (0.0 mm) and Average Temperature (28.8°C).
  - Risk Overview: Flood (Low), Drought (Moderate 5.40), Squall (Low).
  - Weather Signals: 6 chips (Temp Anomaly, Rain Anomaly, Dry Spell, Heavy Rain, Wind Risk, Heat Stress).
  - 7-Day Dynamic Trend Canvas Line Chart.
  - Spatial Risk Report modal dialog.
- **Test:** Unit tests in `AnalystDashboardViewModelTest` pass.
- **Physical Validation:** Screencaps `screen_analyst_dashboard.png` and `screen_analyst_scrolled.png` confirm judge-ready appearance.

---

### BUG-009 — Farmer Profile & Settings Incomplete
- **Severity:** P2 (UX / Agricultural Support)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Navigate to Profile tab in Demo Mode.
- **Expected:** Full exposure of farmer profile, crop stage, plot area, soil type, and data privacy information.
- **Actual:** Minimal generic settings page omitting agricultural and soil fields.
- **Root Cause:** `ProfileScreen.kt` did not bind existing domain fields from `FarmerProfile` and `AppConfig`.
- **Fix:** Added comprehensive "Farmer & Field Details" card (Wheat crop, Vegetative stage, Plot #1, 2.5 Hectares, Alluvial / Loam soil, FAO-56 moisture status) and "Preferences, Data & Privacy" card (Metric units, IMD warnings, local SQLite only, zero cloud sync).
- **Test:** Unit test `ProfileScreenTest` passes.
- **Physical Validation:** Screencaps `screen_profile.png` and `screen_profile_scrolled2.png` confirm rich display.

---

### BUG-010 — Spray Decision Threshold Inconsistency
- **Severity:** P2 (Decision Safety)
- **Status:** **FIXED & PHYSICALLY VERIFIED**
- **Reproduction:** Inspect rain probability evaluation logic in `WeatherGPTRepositoryImpl.kt` vs `docs/11_ANALYTICS_ENGINE.md`.
- **Expected:** Strict canonical threshold $\text{PoP} \le 30.0\%$ adhered to across all tiers.
- **Actual:** Android code used $\le 40.0\%$.
- **Root Cause:** Specification drift during early prototyping.
- **Fix:** Updated `WeatherGPTRepositoryImpl.kt` to enforce canonical agronomic threshold:
  $$\text{rainOk} = \text{rainProb} \le 30.0 \ \&\&\ \text{precipMm} == 0.0$$
  Also updated comments, tests, and documentation.
- **Test:** Unit tests in `WeatherGPTRepositoryImplTest.kt` updated and passing.
- **Physical Validation:** NirnayCard evaluates `POSTPONE` with HIGH CONFIDENCE based on 72% humidity and overcast condition in Gwalior.

---

### BUG-011 — README / SIH Showcase Setup Documentation
- **Severity:** P1 (Documentation / Operational)
- **Status:** **FIXED**
- **Reproduction:** Inspect `README.md` for SIH booth setup instructions.
- **Expected:** Step-by-step setup covering Laptop 1, Laptop 2, Phone, Hotspot, Bridge, IPs, and demo flow.
- **Actual:** Missing physical multi-laptop network setup guide.
- **Root Cause:** Documentation focused solely on cloud/Linux production deployment.
- **Fix:** Added Section 14 to `README.md`: complete physical topology ASCII diagram, hardware table, startup commands for both laptops, Android configuration, offline invariants, troubleshooting table, and 9-step demo sequence.
- **Test:** Markdown syntax and cross-links verified.
