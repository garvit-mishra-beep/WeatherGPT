# VAYUBODHAK — DATA PROVENANCE & ATTRIBUTION

**Document**: Data Provenance, Licensing & Redistribution Audit  
**Status**: Canonical Standard  

---

## 1. Provenance Inventory

| Dataset / Source Name | Issuing Authority / Provider | Data Type | Usage in VAYUBODHAK | License / Terms of Service | Classification | Redistribution Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Open-Meteo Weather API** | Open-Meteo GmbH | Surface hourly observations & NWP forecast | Operational real-time meteorological input | CC-BY 4.0 | LIVE / SUPPORTING | Permitted with attribution |
| **OpenAQ Platform** | OpenAQ Community | Ambient air quality observations ($PM_{2.5}, PM_{10}$) | Environmental health hazard evaluation | Open Data Commons (ODC-BY) | LIVE / SUPPORTING | Permitted with attribution |
| **NOAA GFS 0.25°** | National Oceanic and Atmospheric Admin (NOAA) | Global numerical weather prediction grids | Multi-model divergence & synoptic forecasting | U.S. Public Domain | LIVE / REFERENCE | Unrestricted public domain |
| **Gwalior Showcase Scenario** | VAYUBODHAK Engineering Team | Multi-step deterministic monsoon scenario | Video showcase & automated regression testing | Proprietary Project Asset | CONTROLLED SCENARIO | Included with project |
| **Gwalior Road & Hospital Snapshot** | OpenStreetMap Contributors / Public Geodata | Vector lines and points of interest | Spatial exposure modeling in showcase | ODbL 1.0 | REFERENCE | Permitted with attribution |
| **FAO-56 Crop Coefficients** | Food and Agriculture Organization (FAO) | Agronomic evapotranspiration lookup tables | Irrigation water balance modeling | UN Open Access / Public | REFERENCE | Permitted for public reference |
| **IMD Bulletin Format (CAP 1.2)** | India Meteorological Department (IMD) | Structured CAP alert XML/JSON template | Warning parsing schema & benchmark modeling | Government Open Data License (India) | REFERENCE / FIXTURE | Structured format benchmark |
| **District Climate Normals** | IMD Climatological Summaries | Historical monthly mean temperature and rainfall | 30-year climate anomaly calculations | REVIEW REQUIRED | RECORDED | Academic / Research Reference |

---

## 2. Redistribution & Commercial Licensing Notes

* All third-party operational APIs used in VAYUBODHAK require either open-access adherence (Open-Meteo non-commercial / commercial tiers) or API key provisioning (Tomorrow.io, OpenWeatherMap).
* No proprietary restricted government data is packaged within the Git repository.
* The showcase dataset (`data/showcase/`) was synthetically generated using realistic geographic coordinates and calibrated meteorological curves; it contains no classified, embargoed, or private personal data.
