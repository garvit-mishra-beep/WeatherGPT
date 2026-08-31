# WeatherGPT — P5.8 Staging & Release Handoff Specification

**Document ID:** `docs/37_RELEASE_PREPARATION.md`  
**Milestone:** P5.8 — Release Preparation & Handoff  
**Repository State:** `PRODUCTION-LIKE VERIFIED` (Ready for Staging / Release Handoff)  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md), [`docs/35_PRODUCTION_VERIFICATION.md`](35_PRODUCTION_VERIFICATION.md), [`docs/36_FULL_INTEGRATION_QA.md`](36_FULL_INTEGRATION_QA.md)

---

## 1. Executive Summary

Milestone **P5.8 (Release Preparation)** formally transitions the unified WeatherGPT platform (FastAPI backend + Android client foundation) from development and integration testing into a hardened, verified **Staging / Release Handoff** state.

The objective of P5.8 is to verify release-readiness across the entire system without modifying UI/UX designs, inventing unverified credentials or cloud infrastructure, or making unsubstantiated claims.

### Overall Status Classification
* **Backend Status:** `PRODUCTION-LIKE VERIFIED` (476/476 automated tests passing, 0 test failures).
* **Android Client Status:** `PRODUCTION-LIKE VERIFIED` (89/89 automated tests passing, debug build successful, release build successful).
* **API Contract Parity:** `22/22 Endpoints Verified` (Zero drift between OpenAPI `/openapi.json` and Android Retrofit `WeatherGPTApiService`).
* **Deployment Topology:** Native Linux Zero-Docker (FastAPI + Uvicorn 4-worker cluster + PostgreSQL 16 + PostGIS 3.4 + Nginx + Systemd).
* **Physical Device Validation:** `PHYSICAL DEVICE VALIDATION PENDING` (Automated & live loopback/emulator verified; physical hardware ingress scheduled for staging).
* **Actual Production Cloud Deployment:** `ACTUAL PRODUCTION DEPLOYMENT PENDING` (Staging/release candidate handoff complete; cloud server provisioning scheduled).
* **Final UI/UX Design Ownership:** **Pragya's Responsibility** (Technical Compose shell, map canvas, and voice session controller delivered cleanly decoupled).

---

## 2. Environment Configuration Matrix

| Environment | Backend Base URL | Database URL | LLM Inference Target | Android Logging | SSL / Cleartext Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Development** | `http://127.0.0.1:8000/` | `postgresql://postgres:postgres@localhost:5432/weathergpt` | Local vLLM / Ollama (`http://127.0.0.1:8001/v1`) | Enabled (`Level.HEADERS`) | Cleartext allowed on `127.0.0.1`, `localhost`, `10.0.2.2` |
| **Test (CI/Automated)** | TestClient / In-Memory | SQLite mock / Test PG | In-memory `VerificationMockLLM` | Disabled | In-memory TLS bypass |
| **Staging** | `https://staging-api.weathergpt.in/` | `postgresql://weathergpt_staging:...@db-host:5432/weathergpt_staging` | Staging vLLM Cluster (`Qwen/Qwen2.5-14B-Instruct`) | Enabled (Redacted) | Strict HTTPS / System CAs |
| **Production** | `https://api.weathergpt.in/` | `postgresql://weathergpt_user:...@localhost:5432/weathergpt_prod` | Dedicated GPU Inference Node (`vLLM`) | Disabled (`Level.NONE`) | Strict HTTPS / TLS 1.3 / HSTS |

The Android client does not require source-code changes to switch environments:
1. Default release URL is set via Gradle BuildConfig (`DEFAULT_API_BASE_URL = "https://api.weathergpt.in/"`).
2. Dynamic runtime override is supported via `AppConfig.setCustomBaseUrl(url)` for physical device testing and staging deployments.

---

## 3. Android Release Build & Signing Architecture

### 3.1 Gradle Build Variants
* **Debug Variant (`assembleDebug`):**
  * Target: `app-debug.apk` (~12.37 MB)
  * Default URL: `http://10.0.2.2:8000/`
  * Network Logging: `Enabled` (Sensitive headers redacted)
* **Release Variant (`assembleRelease`):**
  * Target: `app-release-unsigned.apk` (~8.30 MB)
  * Default URL: `https://api.weathergpt.in/`
  * Network Logging: `Disabled` (`Level.NONE`)
  * Optimization: ProGuard / R8 rules in `proguard-rules.pro`

### 3.2 Secure Signing Configuration
No signing keys, keystores, or credentials are committed to Git. The Gradle build script in `android/app/build.gradle.kts` dynamically inspects environment variables:

```kotlin
signingConfigs {
    create("release") {
        val keystorePath = System.getenv("WEATHERGPT_KEYSTORE_FILE")
        val keystorePass = System.getenv("WEATHERGPT_KEYSTORE_PASSWORD")
        val keyAliasVal = System.getenv("WEATHERGPT_KEY_ALIAS")
        val keyPassVal = System.getenv("WEATHERGPT_KEY_PASSWORD")

        if (!keystorePath.isNullOrBlank() && file(keystorePath).exists()) {
            storeFile = file(keystorePath)
            storePassword = keystorePass
            keyAlias = keyAliasVal
            keyPassword = keyPassVal
        }
    }
}
```

When building in CI/CD or staging environments, the release manager supplies:
* `WEATHERGPT_KEYSTORE_FILE`: Absolute path to the release `.keystore` or `.jks` file.
* `WEATHERGPT_KEYSTORE_PASSWORD`: Keystore vault password.
* `WEATHERGPT_KEY_ALIAS`: Key alias.
* `WEATHERGPT_KEY_PASSWORD`: Private key password.

If these environment variables are omitted, Gradle produces `app-release-unsigned.apk` without failing.

---

## 4. Subsystem Readiness & Verification

### 4.1 Voice Integration Layer (`docs/18_VOICE_SPEC.md`)
* **Microphone Permission:** `IMPLEMENTED` (`MicrophonePermissionManager` handling Android `RECORD_AUDIO`).
* **Audio Capture Engine:** `IMPLEMENTED` (`AndroidAudioRecorder` recording 16 kHz Mono AAC/MPEG-4 to application `cacheDir` with automatic cleanup).
* **Voice Session Controller:** `IMPLEMENTED` (`VoiceSessionController` state machine orchestrating Record $\to$ STT $\to$ Backend Chat $\to$ TTS $\to$ Audio Playback).
* **Speech-to-Text (STT):** `ABSTRACTED` (`SpeechToTextEngine` contract; on-device native Whisper.cpp pending staging hardware validation).
* **Text-to-Speech (TTS):** `IMPLEMENTED` (`AndroidTextToSpeechEngine` with Indian locale mappings `hi-IN`, `en-IN`, `mr-IN`, `gu-IN`, `bn-IN`; Parler-TTS server optional).

### 4.2 GIS & Map Specification Engine (`docs/31_MAP_READY_DATA.md`)
* **Coordinate Ordering:** Strict RFC 7946 `[longitude, latitude]` in EPSG:4326.
* **MapSpecification:** Declarative contracts for Point Weather, Official Warnings, and Analytical Risk.
* **Renderer Boundary:** `MapRendererAdapter` converts GeoJSON geometries into UI coordinates (`latitude, longitude`) exclusively at the renderer presentation boundary.
* **Warning Color Immutability:** Green (`#22C55E`), Yellow (`#EAB308`), Orange (`#F97316`), Red (`#EF4444`) strictly immutable.

### 4.3 Database & Migrations
* **Engine:** PostgreSQL 16+ with PostGIS 3.4+ spatial extension.
* **Alembic Migrations:**
  * `0001_enable_postgis.py`: Enables PostGIS extension.
  * `0002_administrative_boundaries.py`: Administrative boundary hierarchy (`SpatialCountry`, `SpatialState`, `SpatialDistrict`, `SpatialSubDistrict`) with GiST spatial indexes.
* **Spatial Performance:** Sub-5ms reverse geocoding via `ST_Contains`.

---

## 5. Security & Privacy Audit

* **Repository Credentials Scan:** `0 Real Credentials Found` (Zero API keys, zero passwords, zero private keys, zero unredacted tokens).
* **Android Security:**
  * Zero server secrets, zero direct LLM API keys, zero database credentials.
  * No trust-all SSL or insecure TrustManager.
  * Sensitive headers (`Authorization`, `API-Key`, `Cookie`, `Token`) automatically redacted in HTTP logs.
  * Temporary audio recordings stored exclusively in application-private cache directory and deleted immediately after transcription.
* **Backend Security:**
  * Fail-fast production configuration validation (`DEBUG=false`, non-default `SECRET_KEY`, explicit `CORS_ORIGINS`).
  * RFC 7807 problem details error format without leaking internal stack traces.
  * Tool Gateway sanitization against SQL and shell injection patterns.

---

## 6. Performance Benchmarks

Measured via `scripts/benchmark_native.py` on native runtime:
* **Cold Start & Application Factory Construction:** `55.91 ms`
* **Liveness Probe (`GET /api/v1/health`):** avg=`1.83 ms`, p95=`2.17 ms`
* **Readiness Probe (`GET /api/v1/ready`):** avg=`1.82 ms`, p95=`2.68 ms`
* **Sequential Domain Load Test (100 Requests):**
  * Total Requests: 100
  * Success Rate: 100.0% (0 failures)
  * Average Latency: 139.07 ms
  * Median Latency: 158.28 ms
  * P95 Latency: 302.19 ms

---

## 7. Database Backup & Disaster Recovery Plan

1. **Daily Automated Backup (pg_dump):**
   ```bash
   pg_dump -Fc -h localhost -U weathergpt_user -d weathergpt_prod -f /var/backups/weathergpt/weathergpt_$(date +%Y%m%d_%H%M%S).dump
   ```
2. **Retention Schedule:**
   * Daily backups retained for 30 days.
   * Weekly backups retained for 12 weeks.
   * Monthly backups retained for 12 months.
3. **Restore Procedure:**
   ```bash
   pg_restore -h localhost -U weathergpt_user -d weathergpt_prod --clean --if-exists /var/backups/weathergpt/weathergpt_<TIMESTAMP>.dump
   ```
4. **Migration Rollback Strategy:**
   ```bash
   alembic downgrade -1
   ```

---

## 8. Handoff Notes

### 8.1 Backend Team
* Native Linux Systemd service file is prepared at [`deploy/weathergpt.service.example`](../deploy/weathergpt.service.example).
* Nginx reverse proxy configuration is prepared at [`deploy/nginx.conf.example`](../deploy/nginx.conf.example).
* Production settings verification tool is available at `scripts/verify_production_config.py`.

### 8.2 Android Team
* Debug APK (`app-debug.apk`) and unsigned Release APK (`app-release-unsigned.apk`) build successfully without errors.
* To generate signed release builds, configure the `WEATHERGPT_KEYSTORE_*` environment variables in the CI pipeline.
* Network monitoring, bounded retries, and RFC 7807 error mappings are fully operational.

### 8.3 Pragya / UI-UX Team
* **Boundary:** Technical foundation, data models, networking, map renderer adapters, and voice controllers are complete and decoupled.
* **Pragya's Scope:** Final visual styling, color themes, component typography, MapLibre GL map styling, microphone button animations, and conversational card layouts remain Pragya's creative domain.

---

## 9. Final Release Checklist

- [x] Backend tests green (476/476 passed)
- [x] Android tests green (89/89 passed)
- [x] Debug build green (`assembleDebug` succeeded)
- [x] Release build green (`assembleRelease` succeeded)
- [x] OpenAPI verified (`/openapi.json` matches 22 Retrofit routes)
- [x] Health probe verified (`/api/v1/health` avg=1.83 ms)
- [x] Readiness probe verified (`/api/v1/ready` avg=1.82 ms)
- [x] Chat pipeline verified
- [x] Weather endpoints verified
- [x] Farmer advisories verified
- [x] GIS & boundary hierarchy verified
- [x] Map-ready GeoJSON specifications verified
- [x] NWP grid comparison verified
- [x] Voice architecture verified (STT abstracted, TTS implemented)
- [x] HTTPS production configuration verified
- [x] Signing secrets protected via environment variables
- [x] No credentials committed to Git
- [x] No direct LLM access from Android
- [x] No direct DB access from Android
- [x] Zero Docker / Zero Kubernetes in production topology
- [x] Nginx configuration reviewed
- [x] Systemd service configuration reviewed
- [x] Database migrations reviewed
- [x] Backup & restore strategy documented
- [x] External weather provider strategy documented
- [x] Security audit clean (0 credentials found)
- [x] Performance benchmark recorded
- [x] Git audit clean
