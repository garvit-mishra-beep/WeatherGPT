# WeatherGPT Technical Documentation Index

This directory contains the authoritative technical specifications, architectural designs, input/output contracts, implementation reports, audit logs, and operating requirements for **WeatherGPT**.

---

## 1. Primary Specifications & Architectural Blueprints (01 to 21)

| Document | Title / Purpose | Target Domain | Status |
| :--- | :--- | :--- | :--- |
| [`01_PRD.md`](01_PRD.md) | Product Requirements Document (Baseline product authority) | Product & Engineering | Implemented / Verified |
| [`02_SYSTEM_ARCHITECTURE.md`](02_SYSTEM_ARCHITECTURE.md) | System Topology & End-to-End Component Flow | System Architecture | Implemented / Verified |
| [`03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md) | LLM Orchestration & Four Brain Workflows | LLM Reasoning Layer | Implemented / Verified |
| [`04_INPUT_OUTPUT_CONTRACT.md`](04_INPUT_OUTPUT_CONTRACT.md) | Pydantic Schema Contracts & Boundary Validations | Backend Interfaces | Implemented / Verified |
| [`05_TOOL_REGISTRY.md`](05_TOOL_REGISTRY.md) | Tool Signatures & Brain-to-Tool Permissions Matrix | Tool Gateway | Implemented / Verified |
| [`06_API_CONTRACT.md`](06_API_CONTRACT.md) | FastAPI REST Endpoints & RFC 7807 Errors | Versioned REST API | Implemented / Verified |
| [`07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md) | Ingestion Strategy & IMD / Open-Meteo Integration | Meteorological Ingest | Implemented / Verified |
| [`08_NWP_SPEC.md`](08_NWP_SPEC.md) | Numerical Weather Prediction (GFS 0.25° / ECMWF) | Atmospheric Physics | Implemented / Verified |
| [`09_GIS_SPEC.md`](09_GIS_SPEC.md) | GIS & PostGIS Spatial Operations & Gazetteer | Spatial Analytics | Implemented / Verified |
| [`10_DATABASE_SCHEMA.md`](10_DATABASE_SCHEMA.md) | PostgreSQL + PostGIS Schema & Migrations | Database Foundation | Implemented / Verified |
| [`11_ANALYTICS_ENGINE.md`](11_ANALYTICS_ENGINE.md) | Deterministic Analytics (FAO-56 $ET_0$, Mann-Kendall, Sen's Slope) | Mathematical Analytics | Implemented / Verified |
| [`12_PERSONALIZATION_SPEC.md`](12_PERSONALIZATION_SPEC.md) | Progressive Personalization & Follow-Up Question Logic | Context Management | Implemented / Verified |
| [`13_MULTILINGUAL_SPEC.md`](13_MULTILINGUAL_SPEC.md) | Multilingual Glossaries & Localization (5 Languages) | Multilingual Support | Implemented / Verified |
| [`14_MOBILE_UI_SPEC.md`](14_MOBILE_UI_SPEC.md) | Mobile Conversational UX & Weather Cards | Frontend Architecture | Implemented / Verified |
| [`15_ERROR_GUARDRAILS.md`](15_ERROR_GUARDRAILS.md) | Safety Guardrails, Grounding & Error Taxonomy | AI Safety & Grounding | Implemented / Verified |
| [`16_TESTING_EVALUATION.md`](16_TESTING_EVALUATION.md) | Testing Protocols, Quality Gates & Benchmarks | QA & CI/CD | Implemented / Verified |
| [`17_SETUP_DEPLOYMENT.md`](17_SETUP_DEPLOYMENT.md) | Development Setup, Two-Laptop Topology & Services | DevOps & Deployment | Implemented / Verified |
| [`18_VOICE_SPEC.md`](18_VOICE_SPEC.md) | Voice Ingress/Egress Specification *(Removed from product scope)* | Historical Reference | Scope Removed |
| [`19_ARCHITECTURE_REVIEW.md`](19_ARCHITECTURE_REVIEW.md) | Comprehensive Architecture Audit & Matrix | Systems Engineering | Implemented / Verified |
| [`20_PERFORMANCE.md`](20_PERFORMANCE.md) | Performance Latency Optimization & Connection Pooling | Performance Engineering| Implemented / Verified |
| [`21_BRAINS_IMPLEMENTATION.md`](21_BRAINS_IMPLEMENTATION.md) | Concrete Domain Brain Implementations & Prompts | Domain Intelligence | Implemented / Verified |

---

## 2. Backend Implementation & Engineering Milestones (22 to 35)

| Document | Title / Purpose | Component | Milestone |
| :--- | :--- | :--- | :--- |
| [`22_BACKEND_FOUNDATION.md`](22_BACKEND_FOUNDATION.md) | Backend Foundation: Factory, `/health` + `/ready`, Logging, RFC 7807 | Backend Core | B1 |
| [`22_DATABASE_POSTGIS_FOUNDATION.md`](22_DATABASE_POSTGIS_FOUNDATION.md) | PostgreSQL + PostGIS Foundation: Async ORM, Migrations, Probe | Database Core | B2 |
| [`23_GIS_ADMINISTRATIVE_BOUNDARIES.md`](23_GIS_ADMINISTRATIVE_BOUNDARIES.md) | Administrative Hierarchy (Country, State, District, SubDistrict) | GIS Services | B3 |
| [`24_ANALYTICS_ENGINE_IMPLEMENTATION.md`](24_ANALYTICS_ENGINE_IMPLEMENTATION.md) | Deterministic Analytics: FAO-56, Mann-Kendall, Sen's Slope, Spray | Pure Analytics | B4 |
| [`25_METEOROLOGICAL_DATA_ADAPTERS.md`](25_METEOROLOGICAL_DATA_ADAPTERS.md) | Meteorological Ingestion: IMD CAP XML, GFS 0.25°, Open-Meteo | Data Adapters | B5 |
| [`26_END_TO_END_BACKEND_INTEGRATION.md`](26_END_TO_END_BACKEND_INTEGRATION.md) | End-to-End Chat & Domain REST APIs Integration | Fullstack Core | B6 |
| [`27_SPATIAL_ENGINE.md`](27_SPATIAL_ENGINE.md) | Spatial Engine: Containment, Intersections, Proximity, BBox | Spatial Engine | B4 |
| [`28_NWP_GRID_PROCESSING.md`](28_NWP_GRID_PROCESSING.md) | NWP Processing: Interpolation, Aggregation, Divergence Ratio | NWP Processing | B5 |
| [`29_WEATHER_GIS_INTEGRATION.md`](29_WEATHER_GIS_INTEGRATION.md) | Weather × GIS: District Zonal NWP & Hazard Intersections | Weather × GIS | B6 |
| [`30_GIS_ANALYSIS.md`](30_GIS_ANALYSIS.md) | GIS Analysis: Hazard Characterization, Exposure, Vulnerability | Risk Analysis | B7 |
| [`31_MAP_READY_DATA.md`](31_MAP_READY_DATA.md) | Map-Ready Data: Declarative Map Specs, Mobile GeoJSON | Map Specifications | B8 |
| [`32_FASTAPI_API.md`](32_FASTAPI_API.md) | Complete REST API Reference (`/api/v1`) & Schemas | REST API Layer | B9 |
| [`33_TOOL_GATEWAY.md`](33_TOOL_GATEWAY.md) | Central Deterministic Tool Gateway & 15 Tools Catalog | Central Gateway | B10 |
| [`34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md) | Native Production Deployment (Systemd + Nginx + Uvicorn) | Native Deployment | B11 |
| [`35_PRODUCTION_VERIFICATION.md`](35_PRODUCTION_VERIFICATION.md) | Final Production Verification & Concurrency Tests | Production Audit | B12 |

---

## 3. Staging, Physical Device & Hardening Milestones (36 to 56)

| Document | Title / Purpose | Domain | Milestone |
| :--- | :--- | :--- | :--- |
| [`36_FULL_INTEGRATION_QA.md`](36_FULL_INTEGRATION_QA.md) | Full Integration QA & Regression Verification | Quality Assurance | QA Gate |
| [`37_RELEASE_PREPARATION.md`](37_RELEASE_PREPARATION.md) | Release Preparation & Staging Handoff | Release Engineering | P5.8 |
| [`38_STAGING_VALIDATION.md`](38_STAGING_VALIDATION.md) | Staging Integration & Physical Device Validation | Staging Validation | P5.9 |
| [`39_STAGING_READINESS_HARDENING.md`](39_STAGING_READINESS_HARDENING.md) | Provider Hierarchy & Staging Readiness Hardening | Staging Readiness | P5.10 |
| [`40_EXTERNAL_PROVIDER_INTEGRATION.md`](40_EXTERNAL_PROVIDER_INTEGRATION.md) | External Provider Integration Truth Matrix & Retries | Data Resilience | P5.11 |
| [`41_STAGING_INFRASTRUCTURE.md`](41_STAGING_INFRASTRUCTURE.md) | Staging Infrastructure Provisioning & Probe Latencies | Infrastructure | P5.12 |
| [`42_PHYSICAL_DEVICE_E2E.md`](42_PHYSICAL_DEVICE_E2E.md) | Physical Android Device E2E & Local Connection (ADB / QR) | Android Physical E2E | P5.13 |
| [`43_EXTERNAL_WEATHER_PROVIDER_INTEGRATION.md`](43_EXTERNAL_WEATHER_PROVIDER_INTEGRATION.md) | Multi-Provider Ingestion (OpenWeather, WeatherAPI, Tomorrow, OpenAQ) | Provider Ingestion | P5.14 |
| [`44_PROVIDER_RESILIENCE_CIRCUIT_BREAKERS.md`](44_PROVIDER_RESILIENCE_CIRCUIT_BREAKERS.md) | Provider Resilience, Circuit Breakers & Observability | Fault Tolerance | B13.1-B13.3 |
| [`45_API_OBSERVABILITY.md`](45_API_OBSERVABILITY.md) | API Observability, Metrics Registry & Monotonic Telemetry | Telemetry | B13.4 |
| [`46_DATABASE_HARDENING.md`](46_DATABASE_HARDENING.md) | Database Connection Pool Hardening & Slow-Query Probes | Database Ops | B13.5 |
| [`47_CACHE_ARCHITECTURE.md`](47_CACHE_ARCHITECTURE.md) | Cache Architecture & In-Memory Redis Fallback Layer | Caching Layer | B13.6 |
| [`48_REQUEST_DEDUPLICATION.md`](48_REQUEST_DEDUPLICATION.md) | Request Deduplication & Concurrent Inflight Coalescing | Concurrency Ops | B13.7 |
| [`49_LLM_TOOL_RELIABILITY.md`](49_LLM_TOOL_RELIABILITY.md) | LLM Tool Reliability, JSON Healing & Schema Fallbacks | LLM Robustness | B13.8 |
| [`50_API_RATE_LIMITING.md`](50_API_RATE_LIMITING.md) | API Rate Limiting, Sliding Window & Token Bucket Middleware | Security & Traffic | B13.9 |
| [`51_ERROR_CONTRACTS.md`](51_ERROR_CONTRACTS.md) | Canonical Error Contracts & RFC 7807 Error Catalog | API Standards | B13.10 |
| [`52_HEALTH_READINESS.md`](52_HEALTH_READINESS.md) | Industrial Health & Multi-Component Readiness Probes | Reliability | B13.11 |
| [`53_BACKEND_PERFORMANCE.md`](53_BACKEND_PERFORMANCE.md) | Backend Performance Benchmarking & Memory Optimization | Performance | B13.12 |
| [`54_SECURITY_HARDENING.md`](54_SECURITY_HARDENING.md) | Security Hardening: Headers, Secrets, SQL & Path Sanitization | Security | B13.13 |
| [`55_BACKUP_RECOVERY.md`](55_BACKUP_RECOVERY.md) | Database Backup, Point-In-Time Recovery & Restore Automation | Data Recovery | B13.14 |
| [`56_FINAL_BACKEND_PRODUCTION_GATE.md`](56_FINAL_BACKEND_PRODUCTION_GATE.md) | Final Backend Production Gate & Architectural Sign-off | Architecture Gate | B13.15 |

---

## 4. Android Frontend Architecture, Localization & Prototype Fidelity (57 to 73)

| Document | Title / Purpose | Subsystem | Milestone |
| :--- | :--- | :--- | :--- |
| [`57_ANDROID_FRONTEND_SKELETON.md`](57_ANDROID_FRONTEND_SKELETON.md) | Jetpack Compose Architecture, Navigation Shell & Theme Tokens | Mobile Core | P6.1 |
| [`58_ANDROID_API_INTEGRATION.md`](58_ANDROID_API_INTEGRATION.md) | Retrofit Client, OkHttp Interceptors, Use Cases & Repository | Mobile Network | P6.2 |
| [`59_HOME_SCREEN.md`](59_HOME_SCREEN.md) | Home Screen: Dynamic Weather Summary, Quick Cards & Live Badge | Mobile UI | P6.3 |
| [`60_BRAIN_SELECTION.md`](60_BRAIN_SELECTION.md) | Brain Selection Sheet: Auto, General, Farmer, Researcher, Analyst | Mobile Reasoning | P6.4 |
| [`61_WEATHER_FORECAST_SCREEN.md`](61_WEATHER_FORECAST_SCREEN.md) | Multi-Interval Forecasts (Hourly, 3-Day, 5-Day, 10-Day) & Cards | Mobile UI | P6.5 |
| [`62_ALERTS_SCREEN.md`](62_ALERTS_SCREEN.md) | Official Severe Weather Warnings & IMD CAP Alert Severity Cards | Mobile Safety | P6.6 |
| [`63_FARMER_SCREEN.md`](63_FARMER_SCREEN.md) | Farmer Profile, Crop Growth Stages & Irrigation Advisories | Mobile Agronomy | P6.7 |
| [`64_DATA_ANALYST_SCREEN.md`](64_DATA_ANALYST_SCREEN.md) | Data & Research Screen: Temperature Trends, GFS & Mann-Kendall | Mobile Science | P6.8 |
| [`65_PROFILE_SETTINGS.md`](65_PROFILE_SETTINGS.md) | User Profile, Plan Upgrade, Saved Locations & Settings Dialogs | Mobile Settings | P6.9 |
| [`66_CHAT_VOICE.md`](66_CHAT_VOICE.md) | Conversational Chat Flow, Message Stream & Grounded Cards | Mobile Chat | P6.10 |
| [`67_UI_POLISH_PHYSICAL_E2E.md`](67_UI_POLISH_PHYSICAL_E2E.md) | Mobile UI Polish, Physical Device Verification & Connectivity | Physical E2E | P6.11 |
| [`68_RELEASE_UI_QA.md`](68_RELEASE_UI_QA.md) | Release UI QA, Design System Alignment & Color Tokens | UI Quality Gate | P6.12 |
| [`69_VOICE_SCOPE_REMOVAL.md`](69_VOICE_SCOPE_REMOVAL.md) | Clean Removal of Voice/STT/TTS and Whisper Dependencies | Scope Audit | M69 |
| [`70_FUNCTIONAL_COMPLETION.md`](70_FUNCTIONAL_COMPLETION.md) | Interactive Component Audit & End-to-End Action Verification | UI Interaction | P7.1 |
| [`70_UI_VISUAL_FIDELITY_AUDIT.md`](70_UI_VISUAL_FIDELITY_AUDIT.md) | Visual Fidelity Audit Against Pragya's Approved Prototype | UI Fidelity | P7.1 |
| [`71_ENGLISH_HINDI_LOCALIZATION.md`](71_ENGLISH_HINDI_LOCALIZATION.md) | Centralized String Architecture for English and Hindi UI | Localization | P7.2 |
| [`71_UI_CORRECTION_REPORT.md`](71_UI_CORRECTION_REPORT.md) | Complete Visual UI Correction Report (All Screens Matching Prototype) | Visual Audit | P7.2 |
| [`72_FUNCTIONAL_COMPLETION_AUDIT.md`](72_FUNCTIONAL_COMPLETION_AUDIT.md) | Final Android Frontend Functional & Interactive Audit | Functional Audit | P7.3 |
| [`73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md`](73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md) | Complete English & Hindi Reactive Localization Verification | Localization Gate | P7.4 |

---

## 5. Navigation & Quick Reference

- **Core Product Definition:** [`01_PRD.md`](01_PRD.md)
- **FastAPI Endpoints & Contracts:** [`04_INPUT_OUTPUT_CONTRACT.md`](04_INPUT_OUTPUT_CONTRACT.md) & [`32_FASTAPI_API.md`](32_FASTAPI_API.md)
- **Tool Gateway Catalog:** [`05_TOOL_REGISTRY.md`](05_TOOL_REGISTRY.md) & [`33_TOOL_GATEWAY.md`](33_TOOL_GATEWAY.md)
- **Native Production Deployment:** [`34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md) & [`deploy/README.md`](../deploy/README.md)
- **Android Architecture & Localization:** [`57_ANDROID_FRONTEND_SKELETON.md`](57_ANDROID_FRONTEND_SKELETON.md), [`71_UI_CORRECTION_REPORT.md`](71_UI_CORRECTION_REPORT.md) & [`73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md`](73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md)
