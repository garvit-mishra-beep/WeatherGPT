# VAYUBODHAK Phase 5 — Vulnerability Methodology Verification Matrix

## 1. Executive Summary & Governance Authority

This document provides the definitive, scientifically honest **Methodology Verification Matrix** for Phase 5 (Quantified Vulnerability Modeling) in the VAYUBODHAK architecture.

Following the core directive of Phase 5 Methodology Verification:
> *"Is the implemented method genuinely supported by the cited research/standard, or is it a VAYUBODHAK engineering/prototype choice that must be labeled accordingly?"*

Every formula, threshold, matrix entry, and indicator in Phase 5 has been audited against statutory guidelines, peer-reviewed scientific literature, and official government data tables.

### Methodology Classification Taxonomy
- **`SOURCE-DEFINED`**: The exact formula, threshold, categorization, or numerical mapping is explicitly specified in an authoritative statutory or regulatory standard (e.g., Census 2011 raw tables, IRC pavement categories, BMTPC construction typologies).
- **`RESEARCH-SUPPORTED`**: The underlying physical, biological, or socioeconomic relationship is documented in scientific literature or institutional advisories (e.g., WHO Hospital Safety Index lifeline concepts, FAO-56 / ICAR phenological stages), but specific numerical parameterizations require local adaptation.
- **`VAYUBODHAK-PROTOTYPE`**: The specific numerical scoring, weights, 2D discrete rating matrices, and penalty algorithms are engineering choices developed by the VAYUBODHAK engineering team to operationalize qualitative guidelines into deterministic computation.
- **`UNRESOLVED`**: The methodological basis is unsupported, unvalidated, or speculative, and must remain unexecuted or gated.

---

## 2. Comprehensive Source-to-Rule Verification Matrix

| Method ID | Method Name & Location | Vulnerability Type & Inputs | Cited Source & Tier | Exact Source Support | Implemented Rule / Formula | Source-Defined? | Research-Supported? | Prototype Choice? | Final Classification | Required Governed Wording | Prohibited Wording | Implementation & Test Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :---: |
| **VULN-METH-SOC-SVI-001** | Composite Demographic Social Vulnerability Index (`app/vulnerability/social.py`) | **SOCIAL**<br>Inputs: 6 Census indicators (Age dep, Illit, Sex ratio, Marginal work, Kutcha housing, SC/ST pop) | Census of India 2011 (PCA, H-Tables) & NDMA Guidelines (**E2**) | Census defines raw population tables and ratios. NDMA identifies socioeconomically vulnerable groups. | 1. Min-max normalization with fixed national bounds.<br>2. Equal indicator weights: $W_i = 1/N$.<br>3. $\ge 60\%$ coverage threshold.<br>4. Composite score $[0, 1] \to$ 4 categories. | **NO** (Only raw counts/definitions) | **YES** (Vulnerable demographics) | **YES** (Bounds, equal weights, 60% rule) | **VAYUBODHAK-PROTOTYPE** | "VAYUBODHAK prototype estimates demographic social susceptibility based on Census 2011 baseline..." | "Guaranteed casualties", "poverty count", "mandatory evacuation", "composite risk" | **ACTIVE**<br>100% Tested (PASS) |
| **VULN-METH-PHYS-BLDG-001** | Building Structural Typology Categorical Susceptibility (`app/vulnerability/physical.py`) | **PHYSICAL_STRUCTURAL**<br>Inputs: `structural_class`, `hazard_type` | BMTPC Vulnerability Atlas of India & NBC 2016 (**E2**) | BMTPC / NBC 2016 define construction typologies (Kutcha mud-thatch, Semi-pucca, Pucca RCC, Steel frame) and qualitative force resistance. | 2D discrete lookup matrix: $\text{Typology} \times \text{Hazard} \to$ (Category, Heuristic Score). E.g., Kutcha $\times$ Flood = CRITICAL (0.90), Pucca RCC $\times$ Flood = LOW (0.20). | **NO** (Typology defined; matrix scores not) | **YES** (Qualitative structural resistance) | **YES** (2D discrete matrix, numerical scores) | **VAYUBODHAK-PROTOTYPE** | "Structural typology exhibits {category} physical susceptibility under environmental hazard forces..." | "Fragility curve probability", "building collapse guaranteed", "monetary repair loss" | **ACTIVE**<br>100% Tested (PASS) |
| **VULN-METH-INFRA-HOSP-001** | Healthcare Facility Operational Resilience Evaluation (`app/vulnerability/infrastructure.py`) | **INFRASTRUCTURE**<br>Inputs: `has_backup_power`, `plinth_height_cm`, `has_flood_protection_bund`, `has_icu` | WHO Hospital Safety Index (HSI) & Indian Public Health Standards (IPHS 2022) (**E1**) | WHO HSI identifies vital lifelines: elevated emergency diesel generator, plinth elevation, flood berms. IPHS recommends flood protection. | Additive scoring: Base 0.50. Backup power $(-0.15 \text{ or } +0.30)$; Plinth $<45\text{cm}$ $(+0.15)$, $\ge 90\text{cm}$ $(-0.15)$; Flood bund $(-0.15)$. Clamped to $[0.05, 0.95]$. | **NO** (Only qualitative guidance) | **YES** (Lifeline protection concepts) | **YES** (Exact additive weights, 45cm plinth threshold) | **VAYUBODHAK-PROTOTYPE** | "Facility operational resilience is evaluated as {category} based on backup lifelines..." | "Hospital closed", "patients evacuated", "blackout guaranteed", "admissions surge" | **ACTIVE**<br>100% Tested (PASS) |
| **VULN-METH-INFRA-ROAD-001** | Transport Infrastructure Surface & Drainage Susceptibility (`app/vulnerability/infrastructure.py`) | **INFRASTRUCTURE**<br>Inputs: `surface_type`, `has_storm_drainage`, `embankment_height_m` | Indian Roads Congress (IRC:SP:42 & IRC:36) (**E4**) | IRC defines pavement materials (Earthen, WBM, Bituminous, Concrete) and emphasizes drainage for embankment stability. | Base material score (Unpaved Kutcha 0.85, Bituminous 0.35, Concrete 0.15). Additive absence of storm drainage penalty $(+0.15)$. Embankment height adjustments $(\pm 0.10)$. | **NO** (Technical engineering guidance) | **YES** (Pavement saturation mechanics) | **YES** (Base scores, drainage penalty values) | **VAYUBODHAK-PROTOTYPE** | "Road segment exhibits {category} surface degradation susceptibility without adequate drainage..." | "Road washed away", "traffic terminated", "road blocked/impassable" | **ACTIVE**<br>100% Tested (PASS) |
| **VULN-METH-INFRA-SCH-001** | Educational Institution Emergency Shelter Readiness (`app/vulnerability/infrastructure.py`) | **INFRASTRUCTURE**<br>Inputs: `number_of_stories`, `is_designated_shelter`, `sanitation_facilities_adequate` | NDMA National Guidelines on School Safety & State DDMPs (**E0**) | NDMA identifies schools as multi-hazard vertical evacuation shelters and defines structural safety/sanitation needs. | Discrete readiness matrix: Multi-story designated shelter + sanitation = LOW (0.20); Multi-story non-designated = MODERATE (0.40); Single-story designated = MODERATE (0.60); Single-story non-designated = HIGH (0.85). | **NO** (Shelter criteria defined, not composite index) | **YES** (Vertical refuge concepts) | **YES** (Composite scoring assignments) | **VAYUBODHAK-PROTOTYPE** | "School emergency shelter coping suitability is evaluated as {category}..." | "Shelter certified safe", "invulnerable to disaster", "life safety guaranteed" | **ACTIVE**<br>100% Tested (PASS) |
| **VULN-METH-AGRI-STAGE-001** | Crop Phenological Stage Climate Susceptibility (`app/vulnerability/agricultural.py`) | **AGRICULTURAL**<br>Inputs: `crop_name`, `growth_stage`, `hazard_type` | ICAR Agronomic Advisory Guidelines & FAO-56 Crop Evapotranspiration (**E1**) | FAO-56 defines phenological phases (Germination, Vegetative, Flowering/Anthesis, Maturity). ICAR advisories detail reproductive sensitivity to extreme temperature and submergence. | Discrete matrix mapping: Stage $\times$ Hazard $\to$ (Category, Numerical Score, Physiological Rationale). E.g., Flowering $\times$ Heat = CRITICAL (0.95); Flowering $\times$ Flood = CRITICAL (0.90); Vegetative $\times$ Rain = LOW (0.25). | **NO** (Phenological stages defined; fragility scores not) | **YES** (Reproductive floral sterility / lodging biology) | **YES** (Discrete numerical susceptibility matrix) | **VAYUBODHAK-PROTOTYPE** | "Crop in {stage} phenological stage exhibits {category} physiological susceptibility..." | "100% crop loss", "yield loss percentage", "rupees per hectare loss", "famine" | **ACTIVE**<br>100% Tested (PASS) |
| **VULN-METH-AGRI-WATER-001** | Agricultural Plot Irrigation & Soil Drainage Vulnerability (`app/vulnerability/agricultural.py`) | **AGRICULTURAL**<br>Inputs: `irrigation_source`, `soil_drainage_class` | Ministry of Agriculture & Farmers Welfare (CDAP) (**E2**) | MoA&FW defines agricultural irrigation sources (Rainfed, Canal, Tubewell) and soil texture / drainage categories. | Additive waterlogging susceptibility: Base 0.50. Soil drainage: Poor $(+0.30)$, Well-drained $(-0.20)$. Irrigation: Rainfed $(+0.10)$, Drip $(-0.10)$. Clamped to $[0.05, 0.95]$. | **NO** (Classification schemas defined) | **YES** (Infiltration and root hypoxia mechanics) | **YES** (Additive scoring weights) | **VAYUBODHAK-PROTOTYPE** | "Agricultural plot demonstrates {category} waterlogging susceptibility based on soil permeability..." | "Crop drowned", "total yield write-off", "field ruined" | **ACTIVE**<br>100% Tested (PASS) |

---

## 3. Deep Methodological Verifications

### 3.1 Social Vulnerability Index (VULN-METH-SOC-SVI-001)

#### Indicator Audit
1. **Age Dependency Ratio (`IND-SOC-AGE-DEP`)**:
   - *Definition*: Ratio of dependent population (aged $\le 6$ and $\ge 60$) to working-age population (15–59).
   - *Source*: Census of India 2011, Table C-14.
   - *Direction*: `POSITIVE_RISK` (higher dependency increases precarity).
   - *Empirical Bounds*: $[0.30, 1.10]$.
   - *Provenance*: VAYUBODHAK empirical distribution across 640 districts in Census 2011. National median is $\approx 0.65$; 5th percentile is $\approx 0.35$; 95th percentile is $\approx 1.05$. Clamping prevents division anomalies.
   - *Classification*: `VAYUBODHAK-PROTOTYPE` bounds over `SOURCE-DEFINED` raw data.

2. **Illiteracy Rate (`IND-SOC-ILLIT`)**:
   - *Definition*: Proportion of illiterate persons aged 7 years and above.
   - *Source*: Census of India 2011, Primary Census Abstract (PCA).
   - *Direction*: `POSITIVE_RISK` (reduces ability to read written warnings).
   - *Empirical Bounds*: $[0.10, 0.65]$.
   - *Provenance*: Reflects national district spread (e.g. Kerala districts $\approx 0.08$ to tribal/central districts $\approx 0.60$).
   - *Classification*: `VAYUBODHAK-PROTOTYPE` bounds.

3. **Female Sex Ratio (`IND-SOC-FEM-RATIO`)**:
   - *Definition*: Females per 1,000 males.
   - *Source*: Census of India 2011, PCA.
   - *Direction*: `POSITIVE_RISK` in context of gender disparity and vulnerability access.
   - *Transformation*: Inversely scaled: $\text{Norm} = (1050 - R) / (1050 - 800)$. A ratio of 800 yields 1.0 (highest vulnerability); a ratio of 1050 yields 0.0 (lowest vulnerability).
   - *Empirical Bounds*: $[800.0, 1050.0]$.
   - *Provenance*: VAYUBODHAK engineering design choice to capture skewed sex ratio as social vulnerability.
   - *Classification*: `VAYUBODHAK-PROTOTYPE`.

4. **Marginal Workers (`IND-SOC-MARGINAL-WORK`)**:
   - *Definition*: Proportion of workers employed for less than 6 months per year.
   - *Source*: Census of India 2011, PCA B-Series.
   - *Direction*: `POSITIVE_RISK` (economic livelihood precarity).
   - *Empirical Bounds*: $[0.05, 0.50]$.
   - *Classification*: `VAYUBODHAK-PROTOTYPE` bounds.

5. **Kutcha Housing (`IND-SOC-KUTCHA`)**:
   - *Definition*: Proportion of households residing in non-permanent, temporary structures.
   - *Source*: Census of India 2011, Houses Household Amenities and Assets (H-Series).
   - *Direction*: `POSITIVE_RISK` (lack of physical shelter integrity).
   - *Empirical Bounds*: $[0.02, 0.60]$.
   - *Classification*: `VAYUBODHAK-PROTOTYPE` bounds.

6. **SC/ST Proportion (`IND-SOC-SCST`)**:
   - *Definition*: Proportion of population belonging to Scheduled Castes or Scheduled Tribes.
   - *Source*: Census of India 2011, PCA.
   - *Direction*: `POSITIVE_RISK` (systemic social marginalization under NDMA guidelines).
   - *Empirical Bounds*: $[0.05, 0.80]$.
   - *Classification*: `VAYUBODHAK-PROTOTYPE` bounds.

#### Weighting & Aggregation Scheme
- **Formula**: $SVI = \frac{1}{N_{available}} \sum_{i=1}^{N_{available}} \text{Norm}_i$
- **Audit**: Equal weighting is a recognized heuristic in index construction (UNDP HDI / SoVI baselines), but is not statutory. It is an engineering choice.
- **Classification**: `VAYUBODHAK-PROTOTYPE`.

#### Minimum Coverage Gating
- **Threshold**: $\ge 60\%$ (at least 4 of 6 indicators must be valid).
- **Rule**: If coverage $< 0.60$, the system emits `category = UNDETERMINED`, `score = None`, `quality_state = MISSING/INVALID`. It **NEVER** assumes missing indicators are zero vulnerability.
- **Classification**: `VAYUBODHAK-PROTOTYPE`.

---

### 3.2 Physical / Building Vulnerability (VULN-METH-PHYS-BLDG-001)

#### Taxonomy Verification
- BMTPC Vulnerability Atlas of India (3rd Edition, 2019) and National Building Code (NBC 2016) define wall and roof material classifications:
  1. `KUTCHA_MUD_THATCH` (Mud, unburnt brick, thatch, bamboo, polythene)
  2. `SEMI_PUCCA_BRICK_UNBURNT` (Unburnt brick with clay mortar, stone packing)
  3. `PUCCA_BRICK_BURNT` (Burnt clay bricks, concrete blocks, cement mortar)
  4. `PUCCA_RCC` (Reinforced cement concrete frames and slabs)
  5. `STEEL_FRAME` (Engineered structural steel framing)
- **Status**: The construction typology taxonomy is `SOURCE-DEFINED` (E2).

#### Categorical Susceptibility Matrix Audit
- The 2D matrix mapping construction types to categorical ratings (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`) and ordinal scores ($0.10$ to $0.95$) is **NOT** published as a single continuous equation by BMTPC.
- BMTPC publishes qualitative damage risk tables (e.g. Heavy damage vs Total collapse for earthquakes and cyclones).
- VAYUBODHAK parameterizes these qualitative tables into discrete deterministic categories.
- **Fragility Curve Claim**: The engine **DOES NOT** compute continuous HAZUS-style lognormal fragility curves $P(ds \ge DS | IM)$. It computes discrete categorical structural susceptibility. Calling this a continuous "fragility curve" is prohibited.
- **Classification**:
  - Building Typology: `SOURCE-DEFINED` (E2)
  - Susceptibility Mapping Matrix: `VAYUBODHAK-PROTOTYPE` (E5)
  - Fragility Curve Terminology: Corrected to *Categorical Structural Susceptibility Classification*.

---

### 3.3 Infrastructure Vulnerability (VULN-METH-INFRA-HOSP-001, ROAD-001, SCH-001)

#### Hospital Operational Resilience
- *WHO Hospital Safety Index (HSI)* and *Indian Public Health Standards (IPHS)* define essential emergency requirements:
  - Auxiliary emergency generator elevated above high flood level (HFL).
  - Plinth level raised above local inundation history.
  - Dedicated perimeter flood protection wall/bund.
- *Exact Threshold Audit*: The $45\text{ cm}$ plinth cutoff is based on standard Indian municipal building bye-laws for minimum plinth height, but the exact scoring penalty formula ($0.50 \pm 0.30 \pm 0.15$) is a project engineering heuristic.
- *ICU Readiness Distinction*: ICU presence indicates healthcare surge capacity, not physical building fragility.
- *Exposure $\ne$ Disruption Invariant*: A hospital exposed to flood inundation is **NOT** asserted to be closed, evacuated, or suffering patient mortality.

#### Road Surface & Drainage Fragility
- *Indian Roads Congress (IRC:SP:42 & IRC:36)* documents that unpaved earthen roads lose shear strength when saturated, and inadequate storm ditches cause edge fraying and subgrade failure.
- *Scoring Audit*: Base scores ($0.85, 0.65, 0.35, 0.15$) and $+0.15$ drainage penalty are project engineering values.
- *Exposure $\ne$ Impassability Invariant*: An exposed road is **NOT** declared impassable, washed out, or blocked to vehicular traffic. Downstream routing networks must evaluate clearance.

#### School Shelter Suitability
- *NDMA School Safety Guidelines* outline criteria for multi-story vertical evacuation refuges.
- *Scoring Audit*: Scores ($0.20, 0.40, 0.60, 0.85$) represent coping suitability, not structural invulnerability. A score of $0.20$ does not guarantee that a school is a "safe haven".

---

### 3.4 Agricultural Vulnerability (VULN-METH-AGRI-STAGE-001, WATER-001)

#### Crop Phenological Susceptibility
- *FAO-56 Irrigation and Drainage Paper* and *ICAR Agronomic Advisories* define crop growth stages:
  - `GERMINATION`: High sensitivity to seed rotting and crusting; low wind susceptibility.
  - `VEGETATIVE`: Relative vegetative resilience to short-term inundation.
  - `FLOWERING / ANTHESIS`: Peak physiological vulnerability. Heat stress ($>38^\circ\text{C}$) causes pollen desiccation and sterility; heavy rain washes away pollen; waterlogging induces floral abortion.
  - `MATURITY / HARVESTING`: High susceptibility to grain sprouting, fungal mold, and wind lodging.
- *Scientific Boundary*: The biological phenology is `RESEARCH-SUPPORTED` (E1). The numerical vulnerability matrix ($0.15$ to $0.95$) is a `VAYUBODHAK-PROTOTYPE`.
- *Susceptibility $\ne$ Yield Loss*: The engine **DOES NOT** calculate yield loss percentages, kilogram losses, or financial farm losses.

#### Irrigation Source & Soil Drainage
- MoA&FW Comprehensive District Agriculture Plans (CDAP) categorize rainfed vs irrigated tracts and alluvial vs black cotton clay soils.
- Black cotton soil (`POOR` drainage) exhibits acute waterlogging precarity.
- The additive score ($0.50 \pm 0.30$) is a `VAYUBODHAK-PROTOTYPE`.

---

## 4. Score Semantics & Boundary Rules

1. **Ordinal Susceptibility Rating, NOT Probability**:
   - Scores in $[0.0, 1.0]$ represent relative ordinal susceptibility rankings.
   - A score of $0.85$ does **NOT** mean an $85\%$ probability of destruction, death, or collapse.
2. **Zero Risk Calculation ($R = H \times E \times V$ Strict Non-Occurrence)**:
   - Phase 5 evaluates susceptibility $V$ given hazard $H$ and exposure $E$.
   - Phase 5 **DOES NOT** calculate risk scores ($R$). Risk modeling is strictly quarantined for Phase 6.
3. **Zero Impact Modeling**:
   - Phase 5 does not compute damage, dollar loss, hospital admissions, evacuation orders, casualties, or relief supply needs.
4. **Historical Baseline Preservation**:
   - Census 2011 demographic data is explicitly tagged with `is_historical = True` and `historical_reference_year = 2011` to prevent mistaking decadal baselines for real-time census counts.

---

## 5. Verification Status Verdict

| Method ID | Scientific Status | Governance Status | Production Eligibility |
| :--- | :--- | :--- | :--- |
| `VULN-METH-SOC-SVI-001` | VAYUBODHAK-PROTOTYPE (Census 2011 E2 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |
| `VULN-METH-PHYS-BLDG-001` | VAYUBODHAK-PROTOTYPE (BMTPC E2 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |
| `VULN-METH-INFRA-HOSP-001` | VAYUBODHAK-PROTOTYPE (WHO/IPHS E1 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |
| `VULN-METH-INFRA-ROAD-001` | VAYUBODHAK-PROTOTYPE (IRC E4 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |
| `VULN-METH-INFRA-SCH-001` | VAYUBODHAK-PROTOTYPE (NDMA E0 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |
| `VULN-METH-AGRI-STAGE-001` | VAYUBODHAK-PROTOTYPE (ICAR/FAO E1 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |
| `VULN-METH-AGRI-WATER-001` | VAYUBODHAK-PROTOTYPE (MoAFW E2 Base) | **ACTIVE** (Labeled Prototype) | APPROVED under governed disclosure |

**Final Verification Conclusion**:
All 7 Phase 5 methods have been audited and corrected. Unsupported statutory validation claims have been stripped. Every active method is rigorously cataloged as `VAYUBODHAK-PROTOTYPE` anchored to authoritative foundation datasets, with full runtime disclosures emitted on every result.
