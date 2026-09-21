# Phase 9B — Data Governance, Licensing & Authority Protocols

## 1. Statutory Authority & Classification Hierarchy

The VAYUBODHAK architecture enforces strict statutory classification boundaries:
- **`E0` — Operational Statutory Authority**:
  - Reserved exclusively for legally authorized Indian national institutions: **India Meteorological Department (IMD)**, **Central Water Commission (CWC)**, and **National Disaster Management Authority (NDMA)**.
  - Only E0 sources are legally and systemically permitted to produce `EvidenceClass.OFFICIAL_WARNING`.
- **`E1` — International Authority**:
  - Intergovernmental bodies such as **WMO**, **ECMWF**, and **UNDRR**.
  - Authoritative for international meteorological standards, global Medium-Range NWP, and Sendai disaster reduction frameworks.
  - Under Indian jurisdiction, E1 sources serve strictly as guidance; they possess NO authority to issue emergency warnings for India.
- **`E2` — Government & Verified Scientific Datasets**:
  - National scientific agencies and verified datasets: **NOAA GFS**, **NASA IMERG**, **GSI (Geological Survey of India)**, and **Open-Meteo**.
  - Authoritative for numerical fields, physical grid points, and static susceptibility baselines.
- **`E3` to `E5` — Research, Manuals & Prototypes**:
  - Peer-reviewed research, engineering design manuals, and prototype assumptions.

---

## 2. Licensing & Terms of Use Compliance

| Data Provider | Governing License | Terms Reference | Commercial / Redistribution Rights | Mandatory Attribution Statement |
| :--- | :--- | :--- | :--- | :--- |
| **IMD** | Government Open Data License - India (GODL) | `https://mausam.imd.gov.in` | Unrestricted for government and decision support systems in India. | *"Data sourced from India Meteorological Department (IMD), Ministry of Earth Sciences, Govt. of India."* |
| **CWC** | Government Open Data License - India (GODL) | `http://ffs.tamcwc.gov.in` | Public hydrological telemetry for non-commercial disaster risk reduction. | *"Hydrological telemetry provided by Central Water Commission (CWC), Ministry of Jal Shakti."* |
| **NDMA SACHET** | Official Government Disaster Dissemination | `https://sachet.ndma.gov.in` | Emergency alert dissemination across public channels. | *"Alerts aggregated via NDMA SACHET Early Warning Dissemination Portal."* |
| **Open-Meteo** | Creative Commons Attribution 4.0 International (CC BY 4.0) | `https://open-meteo.com/terms` | Free and commercial use permitted with mandatory attribution. | *"Weather data provided by Open-Meteo (open-meteo.com) under CC BY 4.0."* |
| **NOAA GFS** | US Government Open Data (Public Domain) | `https://www.weather.gov` | Unrestricted worldwide public domain reuse. | *"Atmospheric prognostic data from NOAA / National Weather Service Global Forecast System (GFS)."* |
| **NASA IMERG** | NASA Open Data Policy | `https://gpm.nasa.gov` | Free and open data access for scientific and operational applications. | *"Precipitation estimates from NASA GPM Integrated Multi-satellitE Retrievals for GPM (IMERG)."* |
| **ECMWF** | ECMWF Open Data Licence | `https://www.ecmwf.int` | Open access medium-range prognostic guidance. | *"ECMWF Open Data products."* |
| **GSI** | Academic / Research Data Access | `https://bhukosh.gsi.gov.in` | National Landslide Susceptibility Mapping baseline access. | *"Landslide susceptibility baselines derived from Geological Survey of India (GSI) NLSM."* |

---

## 3. Secret Management & Key Rotation Protocol
1. **Zero Credential Ingestion**: API keys, Bearer tokens, and client secrets must never be committed to source control or logged in runtime stdout/stderr.
2. **Environment Variable Decoupling**: External API secrets are loaded through `app.config.Settings` from environment variables (e.g. `IMD_API_KEY`, `OPENWEATHER_API_KEY`, `WEATHERAPI_KEY`, `TOMORROW_IO_KEY`).
3. **Log Sanitization**: Outbound URL query parameters (such as `?appid=...`, `?key=...`) are automatically stripped or masked as `***REDACTED***` by `ResilientHTTPExecutor`.
4. **Key Rotation Without Code Changes**: Keys can be rotated by updating environment variables or Kubernetes secrets followed by container restart or zero-downtime rolling deployment.

---

## 4. Zero Silent Conversion Principle
To guarantee scientific honesty:
- **`MISSING`** data must NEVER be silently filled with `0.0`. Missing precipitation means *unmeasured*, not *dry weather*.
- **`STALE`** data must NEVER be passed off as current real-time telemetry. If a sensor or bulletin has expired its freshness window, it is flagged as `STALE`.
- **`INVALID`** data (e.g. humidity > 100%, negative pressure, non-physical temperatures) must NEVER be clamped silently to boundary limits. It is rejected and logged.
- **`CONFLICT`** between different providers must NEVER be averaged into a fictitious synthetic mean. Divergence is flagged for human analyst review.

---

## 5. Decision & Scientific Boundaries
- **Real Data $\neq$ Scientifically Validated Consequence**:
  Real rainfall measurements ingested into a prototype vulnerability curve produce a *real input with a prototype consequence*. It must not be presented to emergency authorities as an empirically validated damage forecast.
- **Real Data $\neq$ Autonomous Action**:
  The VAYUBODHAK pipeline provides decision support, structured reasoning, and auditable evidence ledgers. It NEVER triggers autonomous municipal or law enforcement actions. All final operational commands remain strictly with the human incident commander.
