# 62. Alerts Screen — Milestone P6.7 Specification & Verification

**Document:** `docs/62_ALERTS_SCREEN.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.7 — Alerts Screen Visual & Functional Implementation  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint (Screen: सक्रिय अलर्ट / Official Alerts)  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md), [`docs/14_MOBILE_UI_SPEC.md`](14_MOBILE_UI_SPEC.md), [`docs/15_ERROR_GUARDRAILS.md`](15_ERROR_GUARDRAILS.md), [`docs/58_ANDROID_API_INTEGRATION.md`](58_ANDROID_API_INTEGRATION.md)

---

## 1. Executive Summary

Milestone **P6.7** delivers the complete visual and functional implementation of the **ALERTS SCREEN (सक्रिय अलर्ट)** in Android Jetpack Compose, consuming verified authoritative OASIS CAP warnings from the FastAPI backend service (`GET /api/v1/weather/alerts`).

```
┌─────────────────────────────────────────────────────────────┐
│ 📍 Jhansi, Uttar Pradesh                    [ 1 सक्रिय अलर्ट ] │
├─────────────────────────────────────────────────────────────┤
│ [ सभी (All) ] [ मौसम (Weather) ] [ कृषि ] [ सरकारी (Gov) ]   │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ● ORANGE ALERT                         Heavy Rain Risk  │ │
│ │ Heavy Rainfall Warning                                  │ │
│ │ Jhansi and surrounding Bundelkhand district             │ │
│ │ Intense convective thunderstorm with localized flooding │ │
│ │                                                         │ │
│ │ Action Advisory: Avoid low-lying waterlogged areas      │ │
│ │ Valid: 2026-08-31T09:00:00Z to 2026-08-31T21:00:00Z     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Real API Endpoint Mapping

| Section | Backend API Endpoint | Android Domain Model | Displayed Fields |
|---|---|---|---|
| **Alerts Report** | `GET /api/v1/weather/alerts` | `WeatherAlertsReport` | `authority`, `activeAlertsCount`, `retrievedAt`, `alerts` |
| **Official Alert Items** | `OfficialAlert` (nested in report) | `OfficialAlert` | `alertId`, `warningColor` (Green/Yellow/Orange/Red), `hazard`, `severity`, `headline`, `description`, `areaDescription`, `instructions`, `effectiveFrom`, `expiresAt` |

---

## 3. Features & Architecture

1. **Category Filtering**:
   - `सभी (All)`: Displays all official active alerts.
   - `मौसम (Weather)`: Filters rain, storm, wind, heat hazards.
   - `कृषि (Agriculture)`: Filters crop risk and agricultural advisories.
   - `सरकारी (Government)`: Authoritative CAP feeds from IMD and NDMA Sachet.
2. **Severity Immutability**:
   - Strictly enforces official warning levels (`Green`, `Yellow`, `Orange`, `Red`) without modification.
3. **Empty State (`EmptyAlertsCard`)**:
   - Displays green shield (`🛡️`) with message: "वर्तमान में कोई सक्रिय चेतावनी नहीं है। सभी मौसम पैरामीटर सामान्य सीमा (Green) के भीतर हैं।"
4. **Lifecycle & State Resilience**:
   - Full support for `LoadingState`, `ErrorState` (RFC 7807 with retry action), and offline network detection.

---

## 4. Verification & Testing

- **Tests:** 127/127 unit tests passing cleanly.
- **Scenarios:** `alertsViewModel_loadsRealAlertsAndFiltersByCategory`, `alertsViewModel_offlineErrorHandling`, and location updates.
