# WeatherGPT Technical Documentation Index

This directory contains the authoritative technical specifications, architectural designs, input/output contracts, and operating requirements for WeatherGPT.

## Documentation Index

| Document | Title / Purpose | Target Audience | Status |
| :--- | :--- | :--- | :--- |
| [`01_PRD.md`](01_PRD.md) | Product Requirements Document (Baseline product authority) | Product & Engineering | Implemented / Verified |
| [`02_SYSTEM_ARCHITECTURE.md`](02_SYSTEM_ARCHITECTURE.md) | System Topology & End-to-End Component Flow | System Architects | Implemented / Verified |
| [`03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md) | LLM Orchestration & Four Brain Workflows | LLM Engineers | Implemented / Verified |
| [`04_INPUT_OUTPUT_CONTRACT.md`](04_INPUT_OUTPUT_CONTRACT.md) | Pydantic Schema Contracts & Boundary Validations | Backend Engineers | Implemented / Verified |
| [`05_TOOL_REGISTRY.md`](05_TOOL_REGISTRY.md) | Tool Signatures & Brain-to-Tool Permissions Matrix | Backend & Tool Devs | Implemented / Verified |
| [`06_API_CONTRACT.md`](06_API_CONTRACT.md) | FastAPI REST Endpoints & RFC 7807 Errors | API Developers | Implemented / Verified |
| [`07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md) | Ingestion Strategy & IMD / Open-Meteo Integration | Data Engineers | Specified |
| [`08_NWP_SPEC.md`](08_NWP_SPEC.md) | Numerical Weather Prediction (GFS 0.25° / ECMWF) | Climatologists | Specified |
| [`09_GIS_SPEC.md`](09_GIS_SPEC.md) | GIS & PostGIS Spatial Operations & Gazetteer | GIS Specialists | Specified |
| [`10_DATABASE_SCHEMA.md`](10_DATABASE_SCHEMA.md) | PostgreSQL + PostGIS Schema & Migrations | Database Engineers | Specified |
| [`11_ANALYTICS_ENGINE.md`](11_ANALYTICS_ENGINE.md) | Deterministic Analytics (FAO-56 ET0, Mann-Kendall) | Science Engineers | Specified |
| [`12_PERSONALIZATION_SPEC.md`](12_PERSONALIZATION_SPEC.md) | Progressive Personalization & Follow-Up Question Logic | Product & UX | Implemented / Verified |
| [`13_MULTILINGUAL_SPEC.md`](13_MULTILINGUAL_SPEC.md) | Multilingual Glossaries & Localization (5 Languages) | Localization Devs | Implemented / Verified |
| [`14_MOBILE_UI_SPEC.md`](14_MOBILE_UI_SPEC.md) | Mobile Conversational UX & Weather Cards | Frontend Engineers | Specified |
| [`15_ERROR_GUARDRAILS.md`](15_ERROR_GUARDRAILS.md) | Safety Guardrails, Grounding & Error Taxonomy | AI Safety Engineers | Implemented / Verified |
| [`16_TESTING_EVALUATION.md`](16_TESTING_EVALUATION.md) | Testing Protocols, Quality Gates & Benchmarks | QA Engineers | Implemented / Verified |
| [`17_SETUP_DEPLOYMENT.md`](17_SETUP_DEPLOYMENT.md) | Two-Laptop Local Development & Docker Stack | DevOps Engineers | Specified |
| [`18_VOICE_SPEC.md`](18_VOICE_SPEC.md) | Optional Peripheral Voice Ingress/Egress (ASR/TTS) | Voice Engineers | Specified |
| [`19_ARCHITECTURE_REVIEW.md`](19_ARCHITECTURE_REVIEW.md) | Comprehensive Architecture Audit & Matrix | Lead Engineers | Implemented / Verified |
| [`20_PERFORMANCE.md`](20_PERFORMANCE.md) | Performance Latency Optimization & Connection Pooling | Performance Devs | Implemented / Verified |
| [`21_BRAINS_IMPLEMENTATION.md`](21_BRAINS_IMPLEMENTATION.md) | Concrete Domain Brain Implementations & Prompts | Core Devs | Implemented / Verified |

## Navigation Guidance
- **For Architecture Overview:** Start with [`01_PRD.md`](01_PRD.md) and [`02_SYSTEM_ARCHITECTURE.md`](02_SYSTEM_ARCHITECTURE.md).
- **For Data Models & API Contracts:** Consult [`04_INPUT_OUTPUT_CONTRACT.md`](04_INPUT_OUTPUT_CONTRACT.md) and [`06_API_CONTRACT.md`](06_API_CONTRACT.md).
- **For Domain Brain Specifications:** Review [`03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md) and [`21_BRAINS_IMPLEMENTATION.md`](21_BRAINS_IMPLEMENTATION.md).
