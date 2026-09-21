# VAYUBODHAK — DATA CLASSIFICATION POLICY

**Document**: Data Classification & Operational Taxonomy  
**Status**: Canonical Standard  
**Scope**: All Ingested, Processed, and Stored Records in VAYUBODHAK  

---

## 1. Data Classification Tiers

To ensure complete legal defensibility, scientific integrity, and operational transparency, all data in VAYUBODHAK is assigned to one of six mutually exclusive classifications:

| Classification | Definition | Examples in System | Can Trigger Statutory Override? | Real-Time Live Claim Permitted? |
| :--- | :--- | :--- | :--- | :--- |
| **LIVE** | Real-time observation or forecast fetched directly from active operational APIs during current session. | Open-Meteo REST API observation fetched within 15 minutes. | No (unless issuing body is verified E0/E1 statutory authority). | **YES** |
| **RECORDED** | Authenticated historical observation or official bulletin captured from an authoritative feed and stored with original provenance. | Historical 30-year IMD district rainfall normals; recorded flood hydrograph. | Yes (if recorded statutory order was active for that historical timestamp). | **NO** (Must specify observation/issue timestamp). |
| **FIXTURE** | Static testing payload used exclusively in unit, integration, and regression test suites. | `tests/fixtures/mock_gfs_grib.json`, test DTOs. | Only within test harnesses. | **NO** (Never in user UI). |
| **CONTROLLED SCENARIO** | Multi-step demonstrative dataset engineered as structured input to evaluate the real analytical pipeline deterministically. | `data/showcase/*.json` (Gwalior monsoon escalation benchmark). | Evaluated by pipeline, but attributed as a Scenario Benchmark. | **NO** (Strictly labeled as Scenario Reference / Controlled Benchmark). |
| **REFERENCE** | Static geographic, spatial, or agronomic baseline parameters used for calculations. | Crop coefficients ($K_c$), soil water holding capacities, road network centerlines. | No (Reference parameters bound calculations). | **NO** (Static model parameters). |
| **DERIVED** | Numerical product computed directly by VAYUBODHAK analytical engines from Evidence Foundation inputs. | Composite Risk Index, Action Window, `NirnayCard`, Decision Revision. | Yes (Internal operational verdict). | **YES** (Represents system's latest verified evaluation). |

---

## 2. Statutory Authority Governance

* **E0 National Statutory**: India Meteorological Department (IMD), Central Water Commission (CWC), National Disaster Management Authority (NDMA).
* **E1 State / District Statutory**: State Disaster Management Authorities (SDMA), District Disaster Management Authorities (DDMA).
* **E2 Supporting Telemetry**: Open-Meteo, OpenAQ, GFS, WRF, ECMWF.
* **Prohibition**: E2 supporting telemetry is strictly prohibited from generating `EvidenceClass.OFFICIAL_WARNING`. Any attempt to register an official warning under an E2 source is rejected at the schema level by `SourceRegistry`.

---

## 3. Truthful Display Rules in User Interface

1. **Controlled Scenario Data**:
   * Must display neutral, truthful descriptors: `Controlled Scenario`, `Verified Offline Cache`, `Local Intelligence Engine`.
   * Must **NEVER** display `IMD LIVE`, `CWC LIVE`, or `NDMA LIVE` unless authenticated live connectivity to government APIs is operational.
2. **Offline Resilience State**:
   * When network connectivity is lost, the client transitions to `OFFLINE`.
   * It displays the last verified assessment with its exact historical timestamp and `Source Status: Verified Offline Cache`.
   * Stale cached data is **never** disguised as fresh or live.
