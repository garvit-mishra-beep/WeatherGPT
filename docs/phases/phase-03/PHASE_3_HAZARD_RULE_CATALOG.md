# Phase 3 — Hazard Rule Catalog

## Overview

This catalog documents every deterministic hazard rule registered in the
VAYUBODHAK Phase 3 Hazard Rule Registry. Rules are versioned, source-cited,
and classified by evidentiary basis.

---

## Basis Type Classification

| Basis Type | Meaning |
|---|---|
| **OFFICIAL_SOURCE_DERIVED** | Threshold directly derived from an authoritative statutory source (IMD, CWC, NDMA, GSI) |
| **RESEARCH_SUPPORTED** | Threshold supported by published scientific research or WMO guidance |
| **ENGINEERING_PROTOTYPE** | Operational heuristic or prototype — must NOT be presented as authoritative |
| **UNRESOLVED** | No authoritative or research basis available — evaluation deferred |

> **CRITICAL SAFETY RULE:** An ENGINEERING_PROTOTYPE must NEVER silently become an
> OFFICIAL_SOURCE_DERIVED threshold. Every basis change requires explicit documentation.

---

## Non-Compound Rules

### HZR-RAIN-IMD-24H-v1 — Heavy Rainfall (IMD 24h)

| Field | Value |
|---|---|
| **Rule ID** | `HZR-RAIN-IMD-24H-v1` |
| **Hazard Type** | HEAVY_RAINFALL |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD Standard Operational Guidelines for Severe Weather Warnings (2024) |
| **Thresholds** | Heavy: 64.5-115.5mm, Very Heavy: 115.6-204.4mm, Extremely Heavy: ≥204.5mm |
| **Required Inputs** | `precipitation_mm_24h` |
| **Applicability** | India; 24-hour accumulation |
| **What It Proves** | Precipitation accumulation meets IMD classification |
| **What It Does NOT Prove** | Does NOT prove flooding, waterlogging, infrastructure failure |
| **Claim ID** | `CLM-HAZARD-HEAVY-RAIN-IMD` |

---

### HZR-HEAT-IMD-PLAINS-v1 — Heat (IMD Plains)

| Field | Value |
|---|---|
| **Rule ID** | `HZR-HEAT-IMD-PLAINS-v1` |
| **Hazard Type** | HEAT |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD Heatwave Criteria (Plains) |
| **Thresholds** | Heatwave: ≥40°C, Severe: ≥45°C |
| **Required Inputs** | `temperature_max_c` |
| **Applicability** | India Plains region only |
| **What It Proves** | Temperature meets IMD heatwave classification threshold |
| **What It Does NOT Prove** | Does NOT prove official IMD heatwave declaration |
| **Claim ID** | `CLM-HAZARD-HEAT-IMD` |

---

### HZR-WIND-GALE-v1 — Strong Wind / Gale

| Field | Value |
|---|---|
| **Rule ID** | `HZR-WIND-GALE-v1` |
| **Hazard Type** | STRONG_WIND |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD Wind Hazard Scale |
| **Thresholds** | Strong: 40-61km/h, Gale: 62-88km/h, Severe Gale: ≥89km/h |
| **Required Inputs** | `wind_speed_kmh` |
| **What It Proves** | Surface wind speed meets IMD gale/squall thresholds |
| **What It Does NOT Prove** | Does NOT prove cyclonic circulation |

---

### HZR-CYCLONE-IMD-8STAGE-v1 — Tropical Cyclone

| Field | Value |
|---|---|
| **Rule ID** | `HZR-CYCLONE-IMD-8STAGE-v1` |
| **Hazard Type** | CYCLONE |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD 8-Stage Tropical Cyclone Intensity Scale |
| **Required Inputs** | `wind_speed_kmh` (+ official IMD warning) |
| **Required Evidence** | OFFICIAL_WARNING class |
| **What It Proves** | Classifies cyclonic intensity per IMD 8-stage scale |
| **What It Does NOT Prove** | Does NOT replace official IMD cyclone bulletins |
| **Claim ID** | `CLM-HAZARD-CYCLONE-IMD` |

---

### HZR-FOG-DENSE-v1 — Dense Fog

| Field | Value |
|---|---|
| **Rule ID** | `HZR-FOG-DENSE-v1` |
| **Hazard Type** | FOG |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD Fog Classification |
| **Thresholds** | Moderate: 200-500m, Dense: 50-200m, Very Dense: <50m |
| **Required Inputs** | `visibility_m` |
| **What It Proves** | Observed visibility meets IMD fog classification |
| **What It Does NOT Prove** | Does NOT prove transport disruption |

---

### HZR-LIGHTNING-CONV-v1 — Lightning (Engineering Prototype)

| Field | Value |
|---|---|
| **Rule ID** | `HZR-LIGHTNING-CONV-v1` |
| **Hazard Type** | LIGHTNING |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | ⚠️ ENGINEERING_PROTOTYPE |
| **Source** | CAPE/LI convective instability heuristic (WMO diagnostic guidance) |
| **Thresholds** | CAPE: Moderate ≥1000, Severe ≥2500 J/kg; LI: Unstable ≤-3, Very Unstable ≤-6 |
| **Required Inputs** | `cape_jkg`, `lifted_index` |
| **What It Proves** | Convective instability potential from NWP diagnostics |
| **What It Does NOT Prove** | Does NOT prove observed lightning. Diagnostic potential ≠ observed strike. |
| **Known Limitations** | High false alarm rate; no direct lightning detection network |

---

### HZR-FLOOD-CWC-OFFICIAL-v1 — Flood (CWC Official)

| Field | Value |
|---|---|
| **Rule ID** | `HZR-FLOOD-CWC-OFFICIAL-v1` |
| **Hazard Type** | FLOOD |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | Central Water Commission (CWC) official flood forecasts |
| **Required Inputs** | `cwc_flood_warning` |
| **Required Evidence** | OFFICIAL_WARNING class |
| **What It Proves** | CWC has issued an official flood warning for specified station/basin |
| **What It Does NOT Prove** | Does NOT prove nationwide flooding |
| **Claim ID** | `CLM-HAZARD-FLOOD-CWC` |

---

### HZR-OFFICIAL-WARNING-v1 — Official Warning Passthrough

| Field | Value |
|---|---|
| **Rule ID** | `HZR-OFFICIAL-WARNING-v1` |
| **Hazard Type** | OFFICIAL_WARNING |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD/CWC/NDMA-SACHET official warning bulletins |
| **What It Proves** | Preserves and passes through the official warning exactly as issued |
| **What It Does NOT Prove** | VAYUBODHAK does not validate or override the official warning |

---

### HZR-LANDSLIDE-GSI-SUSCEPT-v1 — Landslide Susceptibility

| Field | Value |
|---|---|
| **Rule ID** | `HZR-LANDSLIDE-GSI-SUSCEPT-v1` |
| **Hazard Type** | LANDSLIDE_SUSCEPTIBILITY |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | GSI National Landslide Susceptibility Mapping |
| **What It Proves** | Geological susceptibility classification of the terrain |
| **What It Does NOT Prove** | Does NOT prove landslide event occurrence |

---

### HZR-COLD-WAVE-IMD-v1 — Cold Wave

| Field | Value |
|---|---|
| **Rule ID** | `HZR-COLD-WAVE-IMD-v1` |
| **Hazard Type** | COLD_WAVE |
| **Version** | 1.0 |
| **Status** | ACTIVE |
| **Basis** | OFFICIAL_SOURCE_DERIVED |
| **Source** | IMD Coldwave Criteria |
| **Thresholds** | Cold Wave: ≤10°C, Severe: ≤4°C |
| **What It Proves** | Minimum temperature meets IMD cold wave threshold |

---

## Compound Rules

### HZR-CMP-RAIN-WIND-v1 — Rain + Wind

| Field | Value |
|---|---|
| **Rule ID** | `HZR-CMP-RAIN-WIND-v1` |
| **Basis** | RESEARCH_SUPPORTED |
| **Source** | WMO Multi-Hazard EWS Guidelines (No. 1150) |
| **Requirements** | HEAVY_RAINFALL active + STRONG_WIND active + temporal/spatial overlap |
| **What It Proves** | Concurrent heavy rain and strong wind exposure |

### HZR-CMP-HEAT-HUMID-v1 — Heat + Humidity

| Field | Value |
|---|---|
| **Rule ID** | `HZR-CMP-HEAT-HUMID-v1` |
| **Basis** | RESEARCH_SUPPORTED |
| **Source** | WMO Heat-Health Warning Systems guidance |
| **Requirements** | Temperature ≥35°C + Humidity ≥65% + overlap |
| **Status** | Architecture-ready (requires humidity evidence integration) |

### HZR-CMP-RAIN-SATURATED-v1 — Rain + Saturated Soil

| Field | Value |
|---|---|
| **Rule ID** | `HZR-CMP-RAIN-SATURATED-v1` |
| **Basis** | ⚠️ ENGINEERING_PROTOTYPE |
| **Source** | VAYUBODHAK engineering heuristic |
| **Requirements** | Precipitation ≥35mm + Soil moisture ≥75% |
| **Status** | Architecture-ready (requires soil moisture evidence integration) |
