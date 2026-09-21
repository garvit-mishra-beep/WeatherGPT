# PHASE 11.2 — FIREBASE CLIENT + STAGING FCM INTEGRATION

**Document:** `docs/PHASE_11_2_FCM_PHYSICAL_E2E.md`  
**System:** Vayubodhak / WeatherGPT  
**Status:** BLOCKED (Staging Credentials Prerequisite)  
**Date:** September 2026  

---

## 1. Executive Summary

Phase 11.2 audited and completed the Android Firebase Cloud Messaging (FCM) client integration and verified the end-to-end backend push architecture for Vayubodhak.

All non-secret client code, permission handling, token registration pipelines, service lifecycles, and backend test suites are verified and passing:
- **Android Gradle & SDK Integration:** Firebase BoM `33.10.0`, Firebase Messaging SDK, and Google Services Gradle Plugin `4.4.2` integrated with conditional compilation guard (`if (file("google-services.json").exists())`).
- **Notification Permissions (Android 13+):** `POST_NOTIFICATIONS` runtime permission implemented with graceful degradation (`GRANTED` / `DENIED` handling without app crashes).
- **Service & Token Management:** `WeatherGPTFirebaseMessagingService` and `PushTokenManager` implemented with token truncation masking, single-device backend synchronization, and deep-link payload extraction (`weathergpt_proactive_decisions` notification channel).
- **App Installation & Launch:** Debug APK built and installed on physical device `US4L6H5HMNJZR8YT` via ADB. Verified graceful initialization and permission grant without crashes.
- **Backend Outbox & FCM Delivery:** 50/50 Phase 9 and Phase 11 backend pytest tests passing, including idempotency, backoff, invalid-token deactivation, and offline LLM resilience.
- **Physical Push Delivery Status:** **BLOCKED**. As required by Sections 3, 7, and 23 of the operating manual, physical delivery cannot occur without `google-services.json` from the Firebase Console and server service-account credentials configured via `FCM_CREDENTIALS_PATH`. No credentials or tokens were fabricated or committed.

---

## 2. Android Firebase Client Architecture

### 2.1 Dependencies and Gradle Configuration
- **Version Catalog:** [`android/gradle/libs.versions.toml`](../android/gradle/libs.versions.toml) defines `firebaseBom = "33.10.0"` and `googleServicesPlugin = "4.4.2"`.
- **Conditional Plugin Application:** In [`android/app/build.gradle.kts`](../android/app/build.gradle.kts):
  ```kotlin
  if (file("google-services.json").exists()) {
      apply(plugin = "com.google.gms.google-services")
  }
  ```
  This prevents local development and CI build breaks when `google-services.json` is unpopulated while allowing instantaneous activation once the staging file is provided.
- **Libraries:**
  - `platform(libs.firebase.bom)`
  - `libs.firebase.messaging`

### 2.2 Manifest & Permissions
In [`android/app/src/main/AndroidManifest.xml`](../android/app/src/main/AndroidManifest.xml):
- Declared permission: `<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />`.
- Registered service:
  ```xml
  <service
      android:name=".core.push.WeatherGPTFirebaseMessagingService"
      android:exported="false">
      <intent-filter>
          <action android:name="com.google.firebase.MESSAGING_EVENT" />
      </intent-filter>
  </service>
  ```
- Activity launch mode configured to `android:launchMode="singleTop"` with intent filters for deep-linking.

### 2.3 Token Management & Masked Registration
- **Token Registration Endpoint:** `POST /api/v1/proactive/devices` consumes `RegisterDeviceRequestDto(token, platform, app_version, language, device_model)`.
- **Masking:** Tokens are masked in client logcat output (e.g., `eK9j...3x9z`) to satisfy security invariants.
- **Lifecycle Integration:** `PushTokenManager.syncTokenWithBackend()` is triggered on app launch in `WeatherGPTApplication` and on token rotation in `WeatherGPTFirebaseMessagingService.onNewToken()`.

### 2.4 Deep Link & Navigation Tap-Through
- Notifications posted to channel `weathergpt_proactive_decisions` carry an intent with:
  - `extra_event_id`: Identifies the authoritative backend decision event.
  - `extra_severity`: Maps to `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
  - `extra_action`: Farmer recommended action (e.g., `NO_GO`, `GO`).
  - `extra_target_screen`: Target route (`alerts`, `farmer`, `weather`, `home`).
- `MainActivity` processes `handleNotificationDeepLink(intent)` and dispatches to `MainViewModel.navigateTo(destination)`.
- Authoritative backend event ID ensures the client views the real server decision rather than calculating or fabricating weather locally.

---

## 3. Backend FCM Infrastructure Audit

### 3.1 Settings Configuration
In [`app/config.py`](../app/config.py):
- `fcm_project_id: str | None = None`
- `fcm_credentials_path: str | None = None`
- `fcm_credentials_json: str | None = None`
- `fcm_timeout_seconds: float = 10.0`
- `outbox_max_retries: int = 5`
- `outbox_worker_batch_size: int = 50`
- `outbox_retry_backoff_seconds: float = 2.0`

### 3.2 Outbox & Delivery Worker Invariants
- **Outbox Durability:** Proactive events generate durable records in `proactive_notification_outbox`.
- **Worker Execution:** Dispatches events with retry backoff and idempotency cooldown (3600 seconds).
- **Invalid Token Handling:** HTTP 404 / `UNREGISTERED` errors automatically deactivate device records in `device_tokens` table.
- **LLM Independence:** Notification delivery and outbox dispatch function without Ollama/Gemma running.

---

## 4. Physical Device Verification Results

| Step | Target | Result | Evidence / Log |
| :--- | :--- | :--- | :--- |
| **Device Connection** | Physical Android Device | **PASS** | ADB device `US4L6H5HMNJZR8YT` attached |
| **Compilation** | Debug APK (`assembleDebug`) | **PASS** | `BUILD SUCCESSFUL in 3m 51s` |
| **Unit Tests** | Android JVM Unit Tests | **PASS** | `BUILD SUCCESSFUL in 27s` (26 tasks) |
| **Installation** | Physical Device Streamed Install | **PASS** | `Performing Streamed Install` -> `Success` |
| **Launch & Graceful Init**| `com.weathergpt/.presentation.MainActivity` | **PASS** | `PushTokenManager: FirebaseApp is not initialized (google-services.json not configured). Push sync skipped.` |
| **Permission Handling** | Android 13+ `POST_NOTIFICATIONS` | **PASS** | `MainActivity: POST_NOTIFICATIONS permission granted by user` |
| **Backend Push Tests** | Pytest Phase 9 & Phase 11 Suites | **PASS** | 50 passed in 47.50s |
| **Backend Personalization** | Pytest Phase 8 & Phase 10 Suites | **PASS** | 53 passed in 16.45s |
| **Live Google FCM Push** | Physical Android E2E Push | **BLOCKED** | Staging Firebase credentials (`google-services.json` and `FCM_CREDENTIALS_PATH`) not provided |

---

## 5. Security & Credentials Audit

- **Zero Secrets Committed:** Git status confirms no `.env`, service-account JSON, or API keys staged.
- **Private Key Grep:** Searched entire workspace for `BEGIN PRIVATE KEY` — **0 matches**.
- **Google API Key Grep:** Searched workspace for `AIzaSy` — **0 matches**.
- **Token Masking:** No unmasked tokens printed in client logcat or backend logs.

---

## 6. Staging Prerequisite Action Items

To unblock physical FCM push on staging:
1. **Firebase Android Client:**
   - Download `google-services.json` for package `com.weathergpt` from the Firebase Console.
   - Place in `android/app/google-services.json` (do not commit to Git).
2. **Backend Server Service Account:**
   - Generate Firebase Admin SDK service account key JSON from Firebase Console.
   - Place on staging host at `/etc/weathergpt/firebase-service-account.json`.
   - Configure environment variable: `FCM_CREDENTIALS_PATH=/etc/weathergpt/firebase-service-account.json`.
3. **Execution:**
   - Re-run `./gradlew.bat assembleDebug` and dispatch controlled staging RED alert test event.
