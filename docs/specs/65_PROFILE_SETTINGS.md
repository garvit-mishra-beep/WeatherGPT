# 65. Profile & Settings Screens — Milestone P6.10 Specification & Verification

**Document:** `docs/65_PROFILE_SETTINGS.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.10 — Profile & Settings Screen Implementation  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/12_PERSONALIZATION_SPEC.md`](12_PERSONALIZATION_SPEC.md), [`docs/42_PHYSICAL_DEVICE_E2E.md`](42_PHYSICAL_DEVICE_E2E.md)

---

## 1. Executive Summary

Milestone **P6.10** implements the **User Profile Screen** and the **Settings Screen** in Android Jetpack Compose, preserving persistent preferences and runtime backend connection configuration.

```
┌─────────────────────────────────────────────────────────────┐
│ 👤 User Profile (Garvit Mishra)                             │
├─────────────────────────────────────────────────────────────┤
│ Primary Region: Surat, Gujarat                              │
│ Operational Plan: WeatherGPT Enterprise Intelligence Plan    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Farmer Advisory Profile → Configure crops and acreage   │ │
│ │ Saved Regions & Watchlists → 3 active monitored areas   │ │
│ │ Preferences & Server Setup → Language, units, and URL   │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Implemented Features

1. **Profile Screen (`ProfileScreen.kt`)**:
   - User avatar header with primary district display.
   - Subscription tier card detailing analytical feature access.
   - Account navigation rows routing to Farmer Advisory and Settings.

2. **Settings Screen (`SettingsScreen.kt`)**:
   - Localization selection (English, Hindi, Marathi, Gujarati, Bengali).
   - Units toggle (Metric °C / km/h vs Imperial °F / mph).
   - Emergency severe weather push notification preferences.
   - Debug-only backend URL configuration with USB reverse (`http://127.0.0.1:8000/`) and LAN/QR support.
   - Release lockdown ensuring backend development controls are excluded in production builds.

---

## 3. Verification

- All unit tests passing cleanly in `ViewModelsTest.kt`.
- SharedPreferences persistence verified across app restart cycles.
