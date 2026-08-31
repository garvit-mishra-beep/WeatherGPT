# WeatherGPT — P5.13 Physical Android Device E2E & Local Backend Connection Specification

**Document ID:** `docs/42_PHYSICAL_DEVICE_E2E.md`  
**Milestone:** P5.13 — Physical Android Device E2E Validation & Local Backend Connection  
**Repository State:** `PHYSICAL DEVICE VERIFIED (USB / ADB REVERSE / LAN CONFIGURABLE)`  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/14_MOBILE_UI_SPEC.md`](14_MOBILE_UI_SPEC.md), [`docs/37_RELEASE_PREPARATION.md`](37_RELEASE_PREPARATION.md), [`docs/38_STAGING_VALIDATION.md`](38_STAGING_VALIDATION.md), [`docs/41_STAGING_INFRASTRUCTURE.md`](41_STAGING_INFRASTRUCTURE.md)

---

## 1. Executive Summary

Milestone **P5.13 (Physical Android Device E2E Validation)** establishes a robust, zero-rebuild local development and physical-device testing architecture for WeatherGPT Android.

### Physical Device Verification: `PASS (USB/ADB REVERSE VERIFIED)`
* **Device ID:** `US4L6H5HMNJZR8YT` (Physical Android Device attached via USB).
* **Port Forwarding / Reverse:** `adb reverse tcp:8000 tcp:8000` (`UsbFfs tcp:8000 tcp:8000`).
* **Liveness Probe Response:** `200 OK` from `http://127.0.0.1:8000/api/v1/health` with round-trip latency of `23 ms`.
* **Automated Unit Tests:** `105/105 PASS` (Android Unit Tests).
* **Backend Pytest Tests:** `483/483 PASS, 21 SKIPPED` (0 failures).

---

## 2. Connection Topologies for Development & Testing

```text
PATH A — Physical USB (Default):
Android Phone (US4L6H5HMNJZR8YT)
       │
       ▼ (http://127.0.0.1:8000/api/v1/health)
ADB Reverse Port Forward (tcp:8000 -> tcp:8000)
       │
       ▼
Local FastAPI Backend (Windows PC 0.0.0.0:8000)

PATH B — Local Wi-Fi / LAN:
Android Phone
       │
       ▼ (http://<LAN_IP>:8000/api/v1/health)
Local Wi-Fi Router / LAN
       │
       ▼
Local FastAPI Backend (Windows PC <LAN_IP>:8000)

PATH C — Staging / Production HTTPS:
Android Phone
       │
       ▼ (https://staging-api.weathergpt.in/ or https://api.weathergpt.in/)
Nginx TLS Reverse Proxy
       │
       ▼
Staging / Production Backend Cluster
```

---

## 3. Local Connection Options & Features (DEBUG Only)

### 3.1 USB / ADB Reverse Mode (Default)
* **Endpoint:** `http://127.0.0.1:8000/`
* **Configuration:** Pre-configured as default debug target (`AppConfig.PHYSICAL_DEBUG_URL`).
* **Usage:** Execute `adb reverse tcp:8000 tcp:8000` on host machine.

### 3.2 Manual LAN URL Entry
* **Endpoint:** `http://<LAN_IP>:8000/` (e.g. `http://192.168.1.100:8000/`)
* **Validation:** Verified by `BackendUrlValidator.kt` checking scheme (`http://` or `https://`), host, port (1..65535), and syntax before applying.
* **Zero Hardcoded IPs:** Developers input their dynamic local IP without touching source code or rebuilding APKs.

### 3.3 QR Code Configuration
* **Developer Utility:** `python scripts/generate_backend_qr.py [--url http://<IP>:8000/]`
* **Dynamic IP Detection:** Discovers primary LAN IP automatically and renders terminal ASCII QR code and optional image.
* **Payload Safety:** Payload contains exclusively the raw URL string (e.g. `http://192.168.1.50:8000/`). Zero credentials, API keys, tokens, or passwords are included.

### 3.4 Local Persistence & Reset
* **Persistence:** Persisted in `SharedPreferences` (`weathergpt_debug_config`) so custom endpoints survive app restarts.
* **Reset Button:** Instant single-click restoration of default physical endpoint `http://127.0.0.1:8000/`.

---

## 4. Release Safety & Security Model

1. **Strict Release Lock-Down:**
   * In `release` builds (`!BuildConfig.DEBUG`), `AppConfig.setCustomBaseUrl` refuses all mutation attempts and returns a validation error.
   * `AppConfig.apiBaseUrl` unconditionally returns `PRODUCTION_URL` (`https://api.weathergpt.in/`).
   * `BackendUrlValidator` strictly rejects `http://`, `127.0.0.1`, `localhost`, `10.0.2.2`, and private LAN IP ranges (`10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`).
2. **Network Security Configuration:**
   * `src/main/res/xml/network_security_config.xml`: Strict production baseline (`cleartextTrafficPermitted="false"`).
   * `src/debug/res/xml/network_security_config.xml`: Debug-specific overlay permitting local developer HTTP cleartext traffic without weakening release security.
3. **Zero Secrets in Mobile Client:**
   * Zero API keys, passwords, database URLs, or private keys committed in the repository or compiled into APKs.

---

## 5. Automated Test Matrix

| Test Suite / Component | Passed / Total | Status | Notes |
| :--- | :---: | :---: | :--- |
| `BackendUrlValidatorTest` | 8 / 8 | `PASS` | Localhost, LAN IPs, missing scheme, invalid port, release security lock-down. |
| `AppConfigTest` | 8 / 8 | `PASS` | Trailing slashes, dynamic debug overrides, release invariant, reset to default. |
| `MainViewModelTest` | 5 / 5 | `PASS` | Backend URL update, validation error propagation, reset, and health probe cancellation. |
| Full Android Unit Tests | 105 / 105 | `PASS` | All DTOs, mappers, repositories, use cases, and presentation state machines. |
| Backend Pytest Suite | 483 / 483 | `PASS` | Full multi-brain reasoning, adapters, tool gateway, GIS, and NWP. |
| Debug APK Build (`assembleDebug`) | Clean | `PASS` | `app-debug.apk` compiled and installed on physical device. |
| Release APK Build (`assembleRelease`) | Clean | `PASS` | `app-release-unsigned.apk` compiled without errors. |
