# Phase 7 — Potential Impact Method Catalog

## 1. Catalog Overview & Governance Framework
This document provides the authoritative, governed catalog of deterministic Potential Impact calculation methods implemented in VAYUBODHAK Phase 7.

Every method in this catalog is strictly registered in `app/impact/method_registry.py` and adheres to the following governance rules:
1. **Lifecycle Gating**: Only methods with status `ACTIVE` may execute in production. `DRAFT` and `RETIRED` methods are rejected at runtime.
2. **Scientific Classification**: Every method is explicitly categorized (`SOURCE-DEFINED`, `RESEARCH-SUPPORTED`, `VAYUBODHAK-PROTOTYPE`, or `UNRESOLVED`). Software test passage verifies mathematical implementation correctness only; it does not validate real-world empirical loss calibration.
3. **Explicit Parameter Separation**:
   - `Source-supported inputs`: Identifies external meteorological, physical, or policy inputs directly grounded in authoritative sources.
   - `Prototype parameters`: Explicitly documents consequence heuristics, damage ratios, disruption percentages, durations, and scalars assigned via VAYUBODHAK engineering prototypes.
   - `Exact source-defined consequences`: Explicitly states whether any consequence formula or percentage is directly defined by a source (or `None`).
   - `Scientific validation status`: Audited scientific fidelity status.
   - `Prototype disclosure`: Mandatory user-facing transparency label.
4. **Strict Negative Boundaries**:
   - Zero casualty or fatality predictions.
   - Zero evacuation orders, rescue commands, or relief resource dispatching.
   - Zero LLM-generated consequence calculations.
   - Zero unmodeled indirect macroeconomic loss estimation.

---

## 2. Method Catalog Specifications

### Method 1: IMPACT-METH-PHYS-BLDG-001

* **Method ID**: `IMPACT-METH-PHYS-BLDG-001`
* **Method Name**: BMTPC Typology Building Physical Damage State & Ratio Prototype
* **Impact Type**: `PHYSICAL_DAMAGE`
* **Hazard Types**: `FLOOD`, `HEAVY_RAINFALL`, `CYCLONE`, `STRONG_WIND`, `LANDSLIDE_SUSCEPTIBILITY`
* **Entity Types**: `BUILDING`
* **Method Version**: `1.0.0`
* **Status**: `ACTIVE`
* **Formula / Logic**:
  $$\text{DamageState}, \text{BaseDamageRatio} = \text{Lookup}(\text{StructuralClass}, \text{HazardSeverityTier})$$
  $$\text{FinalDamageRatio} = \min\left(1.0, \max\left(0.0, \text{BaseDamageRatio} \times (0.5 + 0.5 \times V_{\text{score}})\right)\right)$$
  - *Zero-Boundary Condition*:
    $$\text{Severity} = \text{NONE} \quad \lor \quad V_{\text{score}} = 0.0 \implies \text{DamageState} = \text{NONE}, \text{DamageRatio} = 0.00$$
  - *Missing Data Gating*:
    $$\text{StructuralClass} = \text{UNSPECIFIED} \implies \text{DamageState} = \text{UNDETERMINED}, \text{DamageRatio} = \text{None}$$
* **Inputs**:
  - `hazard_severity` (string: NONE, WATCH, WARNING, SEVERE, EXTREME)
  - `structural_class` (`BuildingStructuralClass`: KUTCHA_MUD_THATCH, SEMI_PUCCA_BRICK_UNBURNT, PUCCA_BRICK_BURNT, PUCCA_RCC, STEEL_FRAME)
  - `footprint_area_sqm` (float $\ge 0.0$)
  - `vulnerability_score` (optional float $\in [0.0, 1.0]$)
* **Units**:
  - Affected quantity: square meters (`sqm`)
  - Damage ratio: dimensionless ratio $\in [0.0, 1.0]$
* **Source Basis**: BMTPC Vulnerability Atlas of India construction typologies and NBC 2016 building construction classification (Authority Level: E2).
* **Claim Basis**: `CLM-IMPACT-MODEL-001`
* **Classification**: `VAYUBODHAK-PROTOTYPE`
* **Source-supported inputs**:
  - BMTPC Vulnerability Atlas building typology definitions (Kutcha, Semi-Pucca, Pucca, Steel Frame) (source-supported input classification).
  - NBC 2016 building construction classification and material vulnerability context (source-supported standard).
* **Prototype parameters**:
  - Discrete continuous damage ratios ($0.02, 0.10, 0.25, 0.50, 0.90$) mapped across hazard tiers and structural typologies (VAYUBODHAK prototype engineering heuristic; not an empirical fragility curve).
  - Categorical qualitative damage state mapping (VAYUBODHAK prototype heuristic).
* **Exact source-defined consequences**:
  - None: Neither BMTPC nor NBC defines mathematical damage ratios, depth-damage functions, or continuous post-disaster physical loss curves.
* **Scientific validation status**:
  - `UNVALIDATED_PROTOTYPE`: Engineering heuristic discrete damage matrix; verified via unit testing for deterministic boundary correctness, but not an empirically calibrated post-disaster insurance loss curve.
* **Prototype disclosure**:
  - `Prototype building physical damage approximation based on BMTPC typology archetypes; scenario-based consequence approximation, not an empirical fragility curve; software-verified, not empirically loss-calibrated.`
* **Prototype Status**: True
* **Spatial Applicability**: `BUILDING_FOOTPRINT`
* **Temporal Applicability**: Contemporaneous with active hazard evaluation window.
* **Uncertainty**:
  - Data coverage: 1.0 if typology recorded; 0.0 if missing.
  - Confidence bounds: $\pm 10\%$ to $15\%$ on estimated damage ratio.
* **Assumptions**:
  - Building structural attributes conform to standardized BMTPC construction archetypes.
  - Damage ratio reflects potential physical structural degradation relative to total replacement cost.
* **Limitations**:
  - *Exposure != Collapse*: Categorical damage states do not indicate imminent structural failure.
  - Foundation depth, building age, unpermitted additions, and maintenance condition are unmodeled.
* **What It Measures**: Potential structural damage state and estimated physical damage ratio for exposed buildings.
* **What It Does Not Measure**: Building collapse certainty, occupant casualty counts, or exact post-disaster contractor repair bills.
* **Test Coverage**: Tested in `tests/test_impact_modeling.py` (`test_physical_damage_evaluation_kutcha_vs_pucca`, `test_physical_damage_zero_boundary_conditions`, `test_physical_damage_missing_structural_class_yields_undetermined`).

---

### Method 2: IMPACT-METH-INFRA-ROAD-001

* **Method ID**: `IMPACT-METH-INFRA-ROAD-001`
* **Method Name**: Road Infrastructure Transport Disruption Prototype
* **Impact Type**: `INFRASTRUCTURE_DISRUPTION`
* **Hazard Types**: `FLOOD`, `HEAVY_RAINFALL`
* **Entity Types**: `ROAD`
* **Method Version**: `1.0.0`
* **Status**: `ACTIVE`
* **Formula / Logic**:
  - *Disruption Trigger Check*:
    $$\text{Triggered} = (\text{Rainfall} \ge 64.5\,\text{mm}) \quad \lor \quad (\text{WaterDepth} \ge 0.3\,\text{m}) \quad \lor \quad (\text{Severity} \in \{\text{SEVERE}, \text{EXTREME}\})$$
  - *Disruption Metrics*:
    $$\text{Severe Trigger} (\text{Rainfall} \ge 115.6\,\text{mm} \lor \text{Depth} \ge 0.5\,\text{m}) \implies \text{DisruptedLength} = L_{\text{total}}, \text{Duration} = 12.0\,\text{h}, \text{State} = \text{MAJOR}$$
    $$\text{Moderate Trigger} (\text{Rainfall} \ge 64.5\,\text{mm} \lor \text{Depth} \ge 0.3\,\text{m}) \implies \text{DisruptedLength} = 0.50 \cdot L_{\text{total}}, \text{Duration} = 4.0\,\text{h}, \text{State} = \text{MODERATE}$$
    $$\text{No Trigger Met} \implies \text{DisruptedLength} = 0.0\,\text{km}, \text{Duration} = 0.0\,\text{h}, \text{State} = \text{MINOR} / \text{NONE}$$
* **Inputs**:
  - `road_length_km` (float $\ge 0.0$)
  - `road_classification` (string: National Highway, State Highway, Major District Road)
  - `observed_rainfall_mm` (optional float)
  - `inundation_depth_m` (optional float)
  - `hazard_severity` (string)
* **Units**:
  - Affected quantity: kilometers (`km`)
  - Disrupted quantity: kilometers (`km`)
  - Duration: hours (`hours`)
* **Source Basis**: IMD National Weather Forecasting Centre rainfall classification criteria and Indian Roads Congress (IRC:SP:42 & IRC:SP:50) / MoRTH road drainage guidelines (Authority Level: E2).
* **Claim Basis**: `CLM-IMPACT-MODEL-001`
* **Classification**: `VAYUBODHAK-PROTOTYPE`
* **Source-supported inputs**:
  - IMD 24h rainfall classification thresholds: Heavy Rainfall $\ge 64.5$ mm/24h, Very Heavy Rainfall $\ge 115.6$ mm/24h (`SOURCE_SUPPORTED_INPUT_THRESHOLD`).
  - IRC road drainage guidelines (IRC:SP:42 & IRC:SP:50) trafficability water depth considerations: $0.3$ m passenger vehicle exhaust clearance, $0.5$ m heavy vehicle axle clearance (`SOURCE-ALIGNED ENGINEERING INPUT`).
* **Prototype parameters**:
  - $50\%$ corridor disruption length for moderate trigger (VAYUBODHAK prototype consequence assumption).
  - $100\%$ corridor disruption length for severe trigger (VAYUBODHAK prototype consequence assumption).
  - $4.0$ hours drainage duration window for moderate trigger (VAYUBODHAK prototype consequence assumption).
  - $12.0$ hours drainage duration window for severe trigger (VAYUBODHAK prototype consequence assumption).
* **Exact source-defined consequences**:
  - None: Neither IMD nor IRC defines percentage corridor disruption fractions, road closure mandates, or post-storm traffic reopening delay hours.
* **Scientific validation status**:
  - `UNVALIDATED_PROTOTYPE`: Engineering heuristic combining source-supported input thresholds with prototype disruption consequence rules; not hydrodynamically calibrated to micro-topography.
* **Prototype disclosure**:
  - `Prototype road transport disruption approximation based on IMD input thresholds and IRC-aligned water depth inputs; disrupted corridor fractions and durations are uncalibrated VAYUBODHAK prototype rules, not observed traffic closures.`
* **Prototype Status**: True
* **Spatial Applicability**: `ROAD_SEGMENT`
* **Temporal Applicability**: Contemporaneous with observed or forecast rainfall event.
* **Uncertainty**:
  - Drainage duration window carries confidence bounds $[-50\%, +80\%]$.
* **Assumptions**:
  - Road segment lacks active high-capacity municipal stormwater pumping.
  - Precipitation $\ge 64.5$ mm (IMD Heavy) creates localized waterlogging on surface corridors.
* **Limitations**:
  - *Exposure != Disruption*: Crossing hazard boundary does NOT mean the road is closed unless threshold is exceeded.
  - Micro-topography, flyovers, culvert maintenance, and real-time traffic diversions are unmodeled.
* **What It Measures**: Potential roadway waterlogging disruption length and estimated drainage delay window.
* **What It Does Not Measure**: Traffic accident casualties, vehicle damages, or official police road closures.
* **Test Coverage**: Tested in `tests/test_impact_modeling.py` (`test_road_disruption_threshold_enforcement`, `test_classification_semantics_input_threshold_vs_prototype_consequence`).

---

### Method 3: IMPACT-METH-SERV-HOSP-001

* **Method ID**: `IMPACT-METH-SERV-HOSP-001`
* **Method Name**: Healthcare Facility Operational Capacity at Risk Prototype
* **Impact Type**: `SERVICE_DISRUPTION`
* **Hazard Types**: `FLOOD`, `CYCLONE`, `HEAT`, `HEAVY_RAINFALL`
* **Entity Types**: `HOSPITAL`
* **Method Version**: `1.0.0`
* **Status**: `ACTIVE`
* **Formula / Logic**:
  $$\text{StrainRatio} = \begin{cases} 
  0.80 & \text{if Extreme Hazard or (Severe Hazard and Access Road Disrupted)} \\
  0.50 & \text{if Severe Hazard} \\
  0.25 & \text{if Warning Hazard} \\
  0.05 & \text{if Watch Hazard} \\
  0.00 & \text{if None Hazard}
  \end{cases}$$
  $$\text{CapacityAtRiskBeds} = \text{round}(\text{RegisteredBeds} \times \text{StrainRatio})$$
* **Inputs**:
  - `hospital_bed_capacity` (float $\ge 0.0$)
  - `access_road_disrupted` (boolean)
  - `hazard_severity` (string)
* **Units**:
  - Inpatient capacity: beds (`beds`)
* **Source Basis**: WHO Hospital Safety Index (HSI 2015) and NDMA Hospital Safety Guidelines (Authority Level: E1).
* **Claim Basis**: `CLM-IMPACT-MODEL-001`
* **Classification**: `VAYUBODHAK-PROTOTYPE`
* **Source-supported inputs**:
  - WHO Hospital Safety Index (HSI 2015) operational lifeline dependency principles (`RESEARCH-SUPPORTED CONCEPT`).
  - NDMA Hospital Safety Guidelines multi-hazard operational criteria (`RESEARCH-SUPPORTED CONCEPT`).
* **Prototype parameters**:
  - Discrete operational capacity strain multipliers ($0.05, 0.25, 0.50, 0.80$) mapped to hazard tiers (VAYUBODHAK prototype heuristic).
  - External feeder road cut capacity strain amplification ($50\%$ to $80\%$) (VAYUBODHAK prototype heuristic).
* **Exact source-defined consequences**:
  - None: Neither WHO nor NDMA defines quantitative bed strain percentages, patient diversion formulas, or mortality equations.
* **Scientific validation status**:
  - `UNVALIDATED_PROTOTYPE`: Operational service strain indicator; scenario-based heuristic, strictly does NOT model patient mortality, morbidity, or clinical harm.
* **Prototype disclosure**:
  - `Prototype healthcare operational strain approximation; scenario-based consequence approximation, strictly does NOT model patient mortality or casualties.`
* **Prototype Status**: True
* **Spatial Applicability**: `POINT`
* **Temporal Applicability**: Contemporaneous emergency operational window.
* **Uncertainty**:
  - Data coverage: 1.0 if official bed capacity recorded; 0.60 if fallback archetype used.
* **Assumptions**:
  - Healthcare facility acts as a critical lifeline during severe meteorological emergencies.
  - Severe surrounding waterlogging impedes ambulance transit and outpatient admission.
* **Limitations**:
  - *Exposure != Shutdown*: Backup diesel generators, emergency triage tents, and redundant access routes are unmodeled.
  - Strictly does NOT model patient mortality, hospital casualties, or disease outbreaks.
* **What It Measures**: Potential inpatient bed capacity at risk and facility operational access strain.
* **What It Does Not Measure**: Patient casualties, disease progression, or official hospital evacuation decrees.
* **Test Coverage**: Tested in `tests/test_impact_modeling.py` (`test_hospital_service_capacity_at_risk`).

---

### Method 4: IMPACT-METH-SERV-SCHL-001

* **Method ID**: `IMPACT-METH-SERV-SCHL-001`
* **Method Name**: Educational Facility Operational Disruption Prototype
* **Impact Type**: `SERVICE_DISRUPTION`
* **Hazard Types**: `FLOOD`, `CYCLONE`, `HEAVY_RAINFALL`
* **Entity Types**: `SCHOOL`
* **Method Version**: `1.0.0`
* **Status**: `ACTIVE`
* **Formula / Logic**:
  $$\text{Severity} \in \{\text{SEVERE}, \text{EXTREME}\} \implies \text{Disrupted} = 1.0, \text{State} = \text{MAJOR}, \text{ShelterPotential} = \text{True}$$
  $$\text{Severity} = \text{WARNING} \implies \text{Disrupted} = 1.0, \text{State} = \text{MODERATE}, \text{ShelterPotential} = \text{True}$$
  $$\text{Severity} \in \{\text{WATCH}, \text{NONE}\} \implies \text{Disrupted} = 0.0, \text{State} = \text{NONE}, \text{ShelterPotential} = \text{False}$$
* **Inputs**:
  - `enrollment_capacity` (float $\ge 0.0$)
  - `hazard_severity` (string)
* **Units**:
  - Affected quantity: enrolled students (`count`)
  - Disrupted quantity: facilities disrupted (`count`)
* **Source Basis**: NDMA School Safety Policy (2016) and Disaster Management Guidelines (Authority Level: E2).
* **Claim Basis**: `CLM-IMPACT-MODEL-001`
* **Classification**: `VAYUBODHAK-PROTOTYPE`
* **Source-supported inputs**:
  - NDMA School Safety Policy institutional disaster continuity guidelines (`RESEARCH-SUPPORTED CONCEPT`).
  - National Disaster Management Plan school shelter dual-use policy framework (`RESEARCH-SUPPORTED CONCEPT`).
* **Prototype parameters**:
  - Binary operational suspension trigger at WARNING hazard severity (VAYUBODHAK prototype heuristic).
  - Precautionary operational suspension ratio ($0.50$ at WARNING, $1.0$ at SEVERE) (VAYUBODHAK prototype heuristic).
  - Emergency relief shelter prototype suitability assessment (prototype heuristic; uncertified without facility-specific engineering audit).
* **Exact source-defined consequences**:
  - None: NDMA policies mandate safety precautions and identify dual-use potential, but do not provide automated facility-level mathematical closure equations.
* **Scientific validation status**:
  - `UNVALIDATED_PROTOTYPE`: Institutional administrative continuity heuristic; strictly does NOT model student injuries or casualties.
* **Prototype disclosure**:
  - `Prototype educational service disruption approximation; scenario-based consequence approximation, strictly does NOT model student injuries or casualties.`
* **Prototype Status**: True
* **Spatial Applicability**: `POINT`
* **Temporal Applicability**: Active school session operational window.
* **Uncertainty**:
  - Data coverage: 1.0 if official enrollment verified.
* **Assumptions**:
  - Severe meteorological warnings prompt institutional closure or conversion to emergency relief shelter.
* **Limitations**:
  - *Disruption != Harm*: Facility session suspension does NOT imply physical student injuries or building collapse.
* **What It Measures**: Educational institutional session disruption and potential relief shelter availability.
* **What It Does Not Measure**: Student injury prediction, structural failure, or official administrative school closure orders.
* **Test Coverage**: Tested in `tests/test_impact_modeling.py` (`test_school_service_disruption_and_shelter_potential`, `test_school_emergency_shelter_suitability_is_prototype_assessment`).

---

### Method 5: IMPACT-METH-AGRI-YIELD-001

* **Method ID**: `IMPACT-METH-AGRI-YIELD-001`
* **Method Name**: Crop Phenological Yield Consequence Prototype
* **Impact Type**: `AGRICULTURAL_IMPACT`
* **Hazard Types**: `FLOOD`, `HEAVY_RAINFALL`, `HEAT`, `STRONG_WIND`
* **Entity Types**: `AGRICULTURE`
* **Method Version**: `1.0.0`
* **Status**: `ACTIVE`
* **Formula / Logic**:
  $$\text{DamageState}, \text{BaseYieldLossPct} = \text{Lookup}(\text{GrowthStage}, \text{HazardSeverityTier})$$
  $$\text{FinalYieldLossRatio} = \min\left(1.0, \max\left(0.0, \text{BaseYieldLossPct} \times (0.6 + 0.4 \times V_{\text{score}})\right)\right)$$
  $$\text{ProductionLossTonnes} = \text{PlantedAcres} \times \text{BaselineYieldTonnesPerAcre} \times \text{FinalYieldLossRatio}$$
  - *Zero-Boundary Condition*:
    $$\text{Severity} = \text{NONE} \quad \lor \quad \text{PlantedAcres} = 0.0 \implies \text{YieldLossRatio} = 0.00, \text{ProductionLoss} = 0.00\,\text{t}$$
* **Inputs**:
  - `crop_name` (string: PADDY, WHEAT, MAIZE, COTTON, SOYBEAN)
  - `growth_stage` (`CropGrowthStage`: GERMINATION, VEGETATIVE, FLOWERING, MATURITY_HARVESTING)
  - `planted_acres` (float $\ge 0.0$)
  - `baseline_yield_tonnes_per_acre` (float default 1.5)
  - `vulnerability_score` (optional float $\in [0.0, 1.0]$)
  - `hazard_severity` (string)
* **Units**:
  - Affected quantity: planted area (`acres`)
  - Disrupted quantity: production deficit (`tonnes`)
  - Damage ratio: potential yield loss ratio $\in [0.0, 1.0]$
* **Source Basis**: ICAR / IMD Agromet Advisories and FAO-56 crop evapotranspiration / FAO Paper 66 crop yield response guidelines (Authority Level: E1).
* **Claim Basis**: `CLM-IMPACT-MODEL-001`
* **Classification**: `VAYUBODHAK-PROTOTYPE`
* **Source-supported inputs**:
  - ICAR Agromet Advisory phenological stage definitions (Germination, Vegetative, Flowering/Anthesis, Maturity) (`SOURCE-SUPPORTED INPUT CONCEPT`).
  - FAO-56 and FAO Paper 66 crop yield response principles and stage sensitivity concepts (`RESEARCH-SUPPORTED CONCEPT`).
* **Prototype parameters**:
  - Discrete phenological yield loss deficit ratio matrix ($0.00$ to $0.90$) across growth stages and hazard tiers (VAYUBODHAK prototype assumption; not an empirical equation).
  - $0.90$ yield-deficit scalar for extreme anthesis/flowering stress (VAYUBODHAK prototype assumption; not a universal ICAR/FAO yield-loss equation).
  - Baseline normal yield assumption (tonnes/acre) (prototype baseline assumption).
* **Exact source-defined consequences**:
  - None: Neither ICAR nor FAO defines a static universal percentage yield-loss equation across all cultivars, micro-climates, and soil types.
* **Scientific validation status**:
  - `UNVALIDATED_PROTOTYPE`: Phenological stress sensitivity index; scenario-based engineering prototype, NOT a calibrated biophysical dynamic crop simulation (e.g. DSSAT) or PMFBY loss curve.
* **Prototype disclosure**:
  - `Prototype agricultural phenological yield loss approximation; scenario-based consequence approximation, not calibrated against biophysical crop models (DSSAT) or PMFBY insurance claims; not a universal equation.`
* **Prototype Status**: True
* **Spatial Applicability**: `ADMINISTRATIVE_POLYGON`
* **Temporal Applicability**: Agricultural crop season (Kharif / Rabi).
* **Uncertainty**:
  - Yield loss ratio carries confidence bounds $[-25\%, +25\%]$.
* **Assumptions**:
  - Crop physiological vulnerability varies significantly across growth stages (anthesis/flowering most sensitive).
  - Waterlogging or thermal stress during flowering impairs pollination and fertilization.
* **Limitations**:
  - *Susceptibility != Yield Loss*: Model does not account for post-event agronomic rescue or drainage intervention.
  - Does NOT calculate crop insurance indemnity payments or government relief compensations.
* **What It Measures**: Potential crop yield loss percentage and estimated harvest production deficit in metric tonnes.
* **What It Does Not Measure**: Guaranteed crop failure, farmer financial distress, or statutory relief eligibility.
* **Test Coverage**: Tested in `tests/test_impact_modeling.py` (`test_agricultural_yield_impact_flowering_vs_vegetative`, `test_agricultural_090_parameter_is_prototype_not_universal_equation`).

---

### Method 6: IMPACT-METH-ECON-DIRECT-001

* **Method ID**: `IMPACT-METH-ECON-DIRECT-001`
* **Method Name**: Direct Asset Physical Damage Economic Valuation Prototype
* **Impact Type**: `ECONOMIC_LOSS`
* **Hazard Types**: `ALL_SUPPORTED`
* **Entity Types**: `BUILDING`, `AGRICULTURE`
* **Method Version**: `1.0.0`
* **Status**: `ACTIVE`
* **Formula / Logic**:
  $$\text{BuildingLossINR} = \text{FootprintAreaSqm} \times \text{UnitReplacementCostPerSqm} \times \text{DamageRatio}$$
  $$\text{AgriLossINR} = \text{ProductionLossTonnes} \times \text{MSPPerTonne}$$
  - *Missing Valuation Rate Gating*:
    $$\text{UnitCost} = \text{None} \implies \text{DamageState} = \text{UNDETERMINED}, \text{EstimatedLoss} = \text{None}$$
* **Inputs**:
  - `physical_impact` (`PotentialImpactAssessment`)
  - `unit_cost_override` (optional float)
  - `valuation_source` (optional string)
  - `valuation_date` (string default "2023-09-01")
  - `currency` (string default "INR")
* **Units**:
  - Monetary loss: Indian Rupees (`INR`)
* **Source Basis**: CPWD Delhi Schedule of Rates (DSR 2021) and CACP Minimum Support Prices (MSP 2023-24) (Authority Level: E2).
* **Claim Basis**: `CLM-IMPACT-MODEL-001`
* **Classification**: `VAYUBODHAK-PROTOTYPE`
* **Source-supported inputs**:
  - CPWD Delhi Schedule of Rates (DSR 2021) baseline plinth area reconstruction rate schedule in INR/sqm (`SOURCE REFERENCE`).
  - CACP Minimum Support Prices (MSP 2023-24) statutory procurement price benchmarks in INR/tonne (`SOURCE REFERENCE`).
* **Prototype parameters**:
  - Linear damage-ratio economic loss formulation: $\text{Loss} = \text{AssetValue} \times \text{DamageRatio}$ (VAYUBODHAK prototype assumption).
  - Indirect macroeconomic loss exclusion boundary (prototype analytical boundary).
  - Output classification as an indicative direct physical loss estimate (not actual loss or contractor tender bid) (VAYUBODHAK prototype assumption).
* **Exact source-defined consequences**:
  - None: Official schedules define reference unit rates and procurement price benchmarks; they do NOT define disaster damage ratios or dynamic loss models.
* **Scientific validation status**:
  - `UNVALIDATED_PROTOTYPE`: Linear damage-ratio economic multiplier; computes an indicative direct physical loss estimate, not actual market loss, official contractor tender bids, or insurance claim settlements.
* **Prototype disclosure**:
  - `Indicative direct physical replacement cost estimate based on official benchmark schedules (CPWD reference rate / CACP MSP benchmark) and prototype damage ratios; not actual market loss, official reconstruction cost, or insurance indemnity settlement.`
* **Prototype Status**: True
* **Spatial Applicability**: `BUILDING_FOOTPRINT` / `ADMINISTRATIVE_POLYGON`
* **Temporal Applicability**: Historical schedule reference baseline.
* **Uncertainty**:
  - Loss estimation carries bounds $[-20\%, +35\%]$ reflecting localized labor and material variance.
* **Assumptions**:
  - Reconstruction/repair cost scales linearly with estimated physical damage ratio.
  - Uses published standard schedules without dynamic post-disaster inflation.
* **Limitations**:
  - *Direct Physical Loss ONLY*: Strictly excludes indirect supply chain disruptions, wage losses, and GDP impacts.
  - Does NOT represent an insurance claim indemnity settlement or contractor tender bid.
* **What It Measures**: Estimated direct physical repair/replacement cost in Indian Rupees (INR).
* **What It Does Not Measure**: Indirect macroeconomic loss, business interruption, or legal liability compensation.
* **Test Coverage**: Tested in `tests/test_impact_modeling.py` (`test_direct_economic_loss_valuation_building`, `test_direct_economic_loss_missing_rate_yields_undetermined`, `test_economic_valuation_reference_schedule_semantics`).
