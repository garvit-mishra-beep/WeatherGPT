# Phase 4 — Exposure Method Catalog

## Overview

This catalog documents all deterministic, spatially-grounded exposure quantification
methodologies implemented in the VAYUBODHAK Phase 4 Exposure Engine. Every method is
versioned, governed by lifecycle status (`ACTIVE`, `DRAFT`, `RETIRED`), and bounded by
strict scientific definitions.

---

## 1. Method: `EXP-METH-POP-ADMIN-001`

- **Method ID:** `EXP-METH-POP-ADMIN-001`
- **Exposure Type:** `POPULATION_ADMIN`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** Administrative Boundary Polygon + Decennial Census Population Record
- **Source:** Census of India 2011 (`SRC-CENSUS-INDIA-2011`)
- **Spatial Operation:** Geodesic Spherical Polygon Clipping & Area Proportionality
- **Formula / Calculation:**
  $$\text{Exposed Population} = \text{Total Admin Population} \times \left( \frac{\text{Intersects Area (km}^2\text{)}}{\text{Total Admin Area (km}^2\text{)}} \right)$$
- **Assumptions:**
  1. Population is assumed uniformly distributed across the administrative unit.
  2. Administrative boundaries between the census record and hazard geometry align topologically.
- **Spatial Resolution:** `ADMINISTRATIVE_POLYGON` (District or Sub-district)
- **Temporal Basis:** Decennial Census Baseline (2011)
- **Quality Handling:** Returns `0.0` with `QualityState.MISSING` if census record is absent or corrupted.
- **Uncertainty:** Moderate to high in non-homogeneous districts; labeled explicitly as an **area-weighted administrative estimate** with $\pm 30\%$ illustrative uncertainty bounds.
- **What It Measures:** Estimated number of residents whose administrative jurisdiction geographically intersects the hazard footprint.
- **What It Does NOT Measure:** Real-time headcounts, evacuation status, casualties, injuries, demographic vulnerability, or displacement.
- **Limitations:**
  - Cannot detect settlement clustering (urban nodes vs uninhabited rural/forest tracts).
  - Based on 2011 decennial figures, not live population.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestPopulationExposure`

---

## 2. Method: `EXP-METH-POP-GRID-001`

- **Method ID:** `EXP-METH-POP-GRID-001`
- **Exposure Type:** `POPULATION_GRIDDED`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** Gridded Population Surface (e.g. WorldPop / LandScan 1km mesh)
- **Source:** WorldPop / Global Human Settlement Layer (`SRC-WORLDPOP-GRID`)
- **Spatial Operation:** Point-in-Polygon Cell Centroid Containment and Zonal Summation
- **Formula / Calculation:**
  $$\text{Exposed Population} = \sum_{c \in \text{Intersecting Cells}} \text{Population}(c)$$
- **Assumptions:**
  1. Dasymetrically modeled surface accurately captures settlement density.
  2. Cell centroids falling inside the hazard polygon provide valid zonal inclusion.
- **Spatial Resolution:** `POPULATION_GRID_CELL` ($1\text{ km} \times 1\text{ km}$ or $100\text{ m} \times 100\text{ m}$)
- **Temporal Basis:** Modeled annual or multi-year demographic projection
- **Quality Handling:** Missing or unpopulated cells are treated as zero residents; cells with invalid coordinates are flagged with `QualityState.INVALID`.
- **Uncertainty:** Low to moderate based on raster cell spatial resolution ($\pm 15\%$).
- **What It Measures:** Estimated count of residential population located inside raster cells overlapping the hazard perimeter.
- **What It Does NOT Measure:** Diurnal/commuter movements, dynamic daytime presence, casualties, or structural shelter quality.
- **Limitations:** Edge-cell boundary clipping approximation.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestPopulationExposure`

---

## 3. Method: `EXP-METH-ASSET-POINT-001`

- **Method ID:** `EXP-METH-ASSET-POINT-001`
- **Exposure Type:** `CRITICAL_INFRASTRUCTURE`, `HOSPITAL`, `SCHOOL`, `POLICE_EMERGENCY`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** GPS Coordinate Registry of Critical Facilities
- **Source:** MoHFW, State Disaster Management Authorities, OpenStreetMap (`SRC-MOHFW-FACILITIES`, `SRC-OSM-INDIA`)
- **Spatial Operation:** Geodesic Point-in-Polygon Ray Casting with Boundary Inclusion
- **Formula / Calculation:**
  $$\text{Exposed Assets} = \{ a \in \text{Assets} \mid \text{PointInPolygon}(a.\text{lon}, a.\text{lat}, \text{HazardPolygon}) = \text{True} \}$$
- **Assumptions:** Point coordinates accurately represent the physical facility location.
- **Spatial Resolution:** `POINT`
- **Temporal Basis:** Semi-static institutional registry
- **Quality Handling:** Coordinates outside $[-180, 180], [-90, 90]$ are rejected with `QualityState.INVALID`.
- **Uncertainty:** Sub-meter geometric precision for surveyed GPS locations.
- **What It Measures:** Physical facilities geographically situated within the hazard perimeter.
- **What It Does NOT Measure:** Facility operational status, structural damage, capacity reduction, power failure, or emergency accessibility.
- **Limitations:** Large institutional campuses represented by a single point centroid may experience boundary clipping variance.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestCriticalAssetExposure`

---

## 4. Method: `EXP-METH-INFRA-ROAD-001`

- **Method ID:** `EXP-METH-INFRA-ROAD-001`
- **Exposure Type:** `ROAD`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** Vector LineString Centerline Geometry
- **Source:** National Highways Authority of India (NHAI), OpenStreetMap (`SRC-NHAI-HIGHWAYS`)
- **Spatial Operation:** LineString Polygon Clipping and Geodesic Metric Length Summation
- **Formula / Calculation:**
  $$\text{Exposed Length (km)} = \sum_{s \in \text{Roads}} \text{HaversineLength}(\text{Clip}(s, \text{HazardPolygon}))$$
- **Assumptions:** Vector centerlines reflect true ground alignment of highways.
- **Spatial Resolution:** `ROAD_SEGMENT`
- **Temporal Basis:** Static transport network layer
- **Quality Handling:** Corrupted or unclosed geometries rejected; missing roads reported as unmonitored.
- **Uncertainty:** Geodesic length precision $\pm 5\%$.
- **What It Measures:** Centerline kilometers of highway infrastructure located inside the hazard zone.
- **What It Does NOT Measure:** **Exposure $\ne$ Disruption.** Does NOT mean roads are closed, flooded, impassable, or washed out.
- **Limitations:** Does not account for bridges, flyovers, or elevated embankments.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestRoadExposure`

---

## 5. Method: `EXP-METH-ASSET-POLY-001`

- **Method ID:** `EXP-METH-ASSET-POLY-001`
- **Exposure Type:** `BUILDING`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** Vector Building Footprint Polygons
- **Source:** Municipal GIS portals, OpenStreetMap (`SRC-MUNICIPAL-GIS`)
- **Spatial Operation:** Polygon-Polygon Geometric Intersection (Sutherland-Hodgman)
- **Formula / Calculation:**
  $$\text{Exposed Buildings} = \text{Count}(\{ b \in \text{Buildings} \mid \text{Intersects}(b.\text{geom}, \text{HazardPolygon}) \})$$
  $$\text{Total Footprint Area} = \sum b.\text{area}$$
- **Assumptions:** Building footprints represent structural ground boundary.
- **Spatial Resolution:** `BUILDING_FOOTPRINT`
- **Temporal Basis:** Cadastral / municipal survey
- **Quality Handling:** Incomplete footprints treated as data gap, not zero structures.
- **Uncertainty:** High variability based on municipal digitizing completeness.
- **What It Measures:** Count and ground footprint area ($\text{m}^2$) of physical structures intersecting the hazard footprint.
- **What It Does NOT Measure:** Building occupancy, structural integrity, wall failure, roof damage, or economic monetary loss.
- **Limitations:** Height / story count not factored into footprint area.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestBuildingExposure`

---

## 6. Method: `EXP-METH-AGRI-PLOT-001`

- **Method ID:** `EXP-METH-AGRI-PLOT-001`
- **Exposure Type:** `AGRICULTURE`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** Registered Farmer Plots & Cultivated Parcels
- **Source:** VAYUBODHAK Farmer Registry (`SRC-FARMER-REGISTRY`), ICAR Agro-Ecological Zones
- **Spatial Operation:** Farm Centroid Containment and Acreage Summation
- **Formula / Calculation:**
  $$\text{Exposed Crop Area (acres)} = \sum_{p \in \text{Contained Plots}} p.\text{area\_acres}$$
- **Assumptions:** Registered plots represent active agricultural cultivation.
- **Spatial Resolution:** `POINT` (Centroid) / `POLYGON` (Parcel)
- **Temporal Basis:** Current agricultural season (Kharif / Rabi / Zaid)
- **Quality Handling:** Zero-acreage or unregistered areas not assumed to be uncultivated.
- **Uncertainty:** Acreage precision based on farmer self-reporting or GPS mapping.
- **What It Measures:** Total cultivated acres and crop types located in the hazard footprint.
- **What It Does NOT Measure:** Crop yield loss, crop damage, lodging, inundation mortality, or financial compensation.
- **Limitations:** Fallow land within plots is not differentiated without satellite indices.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestAgriculturalExposure`

---

## 7. Method: `EXP-METH-ADMIN-AREA-001`

- **Method ID:** `EXP-METH-ADMIN-AREA-001`
- **Exposure Type:** `ADMINISTRATIVE_ASSET`
- **Method Version:** `1.0.0`
- **Status:** `ACTIVE`
- **Input Dataset:** Administrative Boundaries (Country, State, District, Sub-district)
- **Source:** Survey of India, Local Government Directory (`SRC-SURVEY-OF-INDIA`)
- **Spatial Operation:** PostGIS / Geodesic Spherical Polygon Clipping (ST_Intersection, ST_Area)
- **Formula / Calculation:**
  $$\text{Exposed Area (km}^2\text{)} = \text{SphericalArea}(\text{Intersection}(\text{AdminGeom}, \text{HazardGeom}))$$
  $$\text{Overlap \%} = \frac{\text{Exposed Area}}{\text{Total Admin Area}} \times 100$$
- **Assumptions:** Official survey boundaries are topologically valid.
- **Spatial Resolution:** `ADMINISTRATIVE_POLYGON`
- **Temporal Basis:** Static administrative boundary layer (2024 LGD)
- **Quality Handling:** Non-closed rings auto-closed; self-intersections validated.
- **Uncertainty:** Sub-meter boundary precision.
- **What It Measures:** Geographic square kilometers and percentage of an administrative boundary covered by the hazard.
- **What It Does NOT Measure:** Impact severity or population distribution within the boundary.
- **Limitations:** Coarse geographic boundary metric.
- **Test Coverage:** `tests/test_exposure_modeling.py::TestSpatialEngine`
