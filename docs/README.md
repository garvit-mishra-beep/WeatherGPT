# WeatherGPT Technical Documentation Index

This directory contains the authoritative technical specifications, architectural designs, input/output contracts, implementation reports, and operating requirements for WeatherGPT.

## Documentation Index (35 Specifications & Reports)

| Document | Title / Purpose | Target Audience | Status |
| :--- | :--- | :--- | :--- |
| [`01_PRD.md`](01_PRD.md) | Product Requirements Document (Baseline product authority) | Product & Engineering | Implemented / Verified |
| [`02_SYSTEM_ARCHITECTURE.md`](02_SYSTEM_ARCHITECTURE.md) | System Topology & End-to-End Component Flow | System Architects | Implemented / Verified |
| [`03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md) | LLM Orchestration & Four Brain Workflows | LLM Engineers | Implemented / Verified |
| [`04_INPUT_OUTPUT_CONTRACT.md`](04_INPUT_OUTPUT_CONTRACT.md) | Pydantic Schema Contracts & Boundary Validations | Backend Engineers | Implemented / Verified |
| [`05_TOOL_REGISTRY.md`](05_TOOL_REGISTRY.md) | Tool Signatures & Brain-to-Tool Permissions Matrix | Backend & Tool Devs | Implemented / Verified |
| [`06_API_CONTRACT.md`](06_API_CONTRACT.md) | FastAPI REST Endpoints & RFC 7807 Errors | API Developers | Implemented / Verified |
| [`07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md) | Ingestion Strategy & IMD / Open-Meteo Integration | Data Engineers | Implemented / Verified |
| [`08_NWP_SPEC.md`](08_NWP_SPEC.md) | Numerical Weather Prediction (GFS 0.25° / ECMWF) | Climatologists | Implemented / Verified |
| [`09_GIS_SPEC.md`](09_GIS_SPEC.md) | GIS & PostGIS Spatial Operations & Gazetteer | GIS Specialists | Implemented / Verified |
| [`10_DATABASE_SCHEMA.md`](10_DATABASE_SCHEMA.md) | PostgreSQL + PostGIS Schema & Migrations | Database Engineers | Implemented / Verified |
| [`11_ANALYTICS_ENGINE.md`](11_ANALYTICS_ENGINE.md) | Deterministic Analytics (FAO-56 ET0, Mann-Kendall) | Science Engineers | Implemented / Verified |
| [`12_PERSONALIZATION_SPEC.md`](12_PERSONALIZATION_SPEC.md) | Progressive Personalization & Follow-Up Question Logic | Product & UX | Implemented / Verified |
| [`13_MULTILINGUAL_SPEC.md`](13_MULTILINGUAL_SPEC.md) | Multilingual Glossaries & Localization (5 Languages) | Localization Devs | Implemented / Verified |
| [`14_MOBILE_UI_SPEC.md`](14_MOBILE_UI_SPEC.md) | Mobile Conversational UX & Weather Cards | Frontend Engineers | Implemented / Verified |
| [`15_ERROR_GUARDRAILS.md`](15_ERROR_GUARDRAILS.md) | Safety Guardrails, Grounding & Error Taxonomy | AI Safety Engineers | Implemented / Verified |
| [`16_TESTING_EVALUATION.md`](16_TESTING_EVALUATION.md) | Testing Protocols, Quality Gates & Benchmarks | QA Engineers | Implemented / Verified |
| [`17_SETUP_DEPLOYMENT.md`](17_SETUP_DEPLOYMENT.md) | Development Setup, Two-Laptop Topology & Services | DevOps Engineers | Implemented / Verified |
| [`18_VOICE_SPEC.md`](18_VOICE_SPEC.md) | Optional Peripheral Voice Ingress/Egress (ASR/TTS) | Voice Engineers | Specified |
| [`19_ARCHITECTURE_REVIEW.md`](19_ARCHITECTURE_REVIEW.md) | Comprehensive Architecture Audit & Matrix | Lead Engineers | Implemented / Verified |
| [`20_PERFORMANCE.md`](20_PERFORMANCE.md) | Performance Latency Optimization & Connection Pooling | Performance Devs | Implemented / Verified |
| [`21_BRAINS_IMPLEMENTATION.md`](21_BRAINS_IMPLEMENTATION.md) | Concrete Domain Brain Implementations & Prompts | Core Devs | Implemented / Verified |
| [`22_BACKEND_FOUNDATION.md`](22_BACKEND_FOUNDATION.md) | Backend Foundation: Factory, /health + /ready, Logging, RFC 7807 | Backend Engineers | Implemented / Verified (B1) |
| [`22_DATABASE_POSTGIS_FOUNDATION.md`](22_DATABASE_POSTGIS_FOUNDATION.md) | PostgreSQL + PostGIS Foundation: Async ORM, Migrations, Probe | Database Engineers | Implemented / Verified (B2) |
| [`23_GIS_ADMINISTRATIVE_BOUNDARIES.md`](23_GIS_ADMINISTRATIVE_BOUNDARIES.md) | Administrative Hierarchy (Country, State, District, SubDistrict) | GIS Engineers | Implemented / Verified (B3) |
| [`24_ANALYTICS_ENGINE_IMPLEMENTATION.md`](24_ANALYTICS_ENGINE_IMPLEMENTATION.md) | Deterministic Analytics: FAO-56, Mann-Kendall, Sen's Slope, Spray | Science Engineers | Implemented / Verified (B4) |
| [`25_METEOROLOGICAL_DATA_ADAPTERS.md`](25_METEOROLOGICAL_DATA_ADAPTERS.md) | Meteorological Ingestion: IMD CAP XML, GFS 0.25°, Open-Meteo | Data Engineers | Implemented / Verified (B5) |
| [`26_END_TO_END_BACKEND_INTEGRATION.md`](26_END_TO_END_BACKEND_INTEGRATION.md) | End-to-End Chat & Domain REST APIs Integration | Fullstack Engineers | Implemented / Verified (B6) |
| [`27_SPATIAL_ENGINE.md`](27_SPATIAL_ENGINE.md) | Spatial Engine: Containment, Intersections, Proximity, BBox | GIS Engineers | Implemented / Verified (B4) |
| [`28_NWP_GRID_PROCESSING.md`](28_NWP_GRID_PROCESSING.md) | NWP Processing: Interpolation, Aggregation, Divergence Ratio | Science Engineers | Implemented / Verified (B5) |
| [`29_WEATHER_GIS_INTEGRATION.md`](29_WEATHER_GIS_INTEGRATION.md) | Weather × GIS: District Zonal NWP & Hazard Intersections | Spatial Devs | Implemented / Verified (B6) |
| [`30_GIS_ANALYSIS.md`](30_GIS_ANALYSIS.md) | GIS Analysis: Hazard Characterization, Exposure, Vulnerability | Risk Analysts | Implemented / Verified (B7) |
| [`31_MAP_READY_DATA.md`](31_MAP_READY_DATA.md) | Map-Ready Data: Declarative Map Specs, Mobile GeoJSON | Frontend / GIS Devs| Implemented / Verified (B8) |
| [`32_FASTAPI_API.md`](32_FASTAPI_API.md) | Complete REST API Reference (/api/v1) & Schemas | API Engineers | Implemented / Verified (B9) |
| [`33_TOOL_GATEWAY.md`](33_TOOL_GATEWAY.md) | Central Deterministic Tool Gateway & 15 Tools Catalog | Core Engineers | Implemented / Verified (B10) |
| [`34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md) | Native Production Deployment (Systemd + Nginx + Uvicorn) | DevOps Engineers | Implemented / Verified (B11) |
| [`35_PRODUCTION_VERIFICATION.md`](35_PRODUCTION_VERIFICATION.md) | Final Production Verification & Concurrency Tests | Quality Engineers | Implemented / Verified (B12) |

---

## Navigation Guidance
- **System Architecture & Baseline PRD:** [`01_PRD.md`](01_PRD.md) and [`02_SYSTEM_ARCHITECTURE.md`](02_SYSTEM_ARCHITECTURE.md).
- **REST Endpoints & Data Contracts:** [`04_INPUT_OUTPUT_CONTRACT.md`](04_INPUT_OUTPUT_CONTRACT.md) and [`32_FASTAPI_API.md`](32_FASTAPI_API.md).
- **Domain Brains & Tool Gateway:** [`03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md) and [`33_TOOL_GATEWAY.md`](33_TOOL_GATEWAY.md).
- **Native Deployment Manual:** [`34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md) and [`deploy/README.md`](../deploy/README.md).
