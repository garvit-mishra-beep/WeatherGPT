# Phase 7 — Potential Impact Source-to-Method Matrix

## 1. Executive Summary & Verification Methodology
This matrix establishes the definitive, audited mapping between authoritative institutional research sources, exact source statements, and the mathematical formulas implemented in the VAYUBODHAK Phase 7 Potential Impact Engine.

### Fundamental Scientific Principle:
$$\text{Authoritative Source Concept} \quad \ne \quad \text{VAYUBODHAK Exact Numerical Consequence Equation}$$

Passing automated software tests proves computational correctness and deterministic implementation integrity. It does **NOT** constitute independent empirical scientific validation of real-world disaster damage percentages or loss sums.

### Absolute Rule of Parameter Attribution:
```text
OFFICIAL / RESEARCH SOURCE
        ↓
SUPPORTED INPUT / CONCEPT / BOUNDARY
        ↓
VAYUBODHAK CONSEQUENCE SELECTION
        ↓
PROTOTYPE CONSEQUENCE PARAMETER
        ↓
POTENTIAL IMPACT OUTPUT
        ↓
EXPLICIT DISCLOSURE
```

Never convert a **source-supported hazard threshold** into a **source-supported damage/disruption consequence**.
- IMD rainfall classification threshold $\ne$ IMD road disruption percentage.
- IRC water-depth relevance $\ne$ IRC-defined 50% road disruption.
- ICAR/FAO phenological sensitivity $\ne$ ICAR/FAO universal 90% yield loss equation.
- CPWD reference rate $\ne$ actual local reconstruction cost.

---

## 2. Parameter Attribution Classification Matrix (Fix #11)

The following canonical four-column matrix establishes the precise boundary between what the source supports, what VAYUBODHAK adds, and the final parameter classification:

| Parameter | Source Support | VAYUBODHAK Addition | Final Classification |
| :--- | :--- | :--- | :--- |
| **64.5 mm / 24h** | IMD meteorological rainfall classification threshold for "Heavy Rainfall" | Used as an operational trigger for moderate road disruption | **SOURCE INPUT + PROTOTYPE CONSEQUENCE** |
| **115.6 mm / 24h** | IMD meteorological rainfall classification threshold for "Very Heavy Rainfall" | Used as an operational trigger for severe road disruption | **SOURCE INPUT + PROTOTYPE CONSEQUENCE** |
| **0.3 m water depth** | IRC:SP:42 / IRC:SP:50 engineering trafficability input (exhaust clearance consideration) | Used as a threshold for moderate corridor disruption | **SOURCE INPUT + PROTOTYPE CONSEQUENCE** |
| **0.5 m water depth** | IRC:SP:50 / MoRTH engineering trafficability input (commercial axle clearance consideration) | Used as a threshold for severe corridor disruption | **SOURCE INPUT + PROTOTYPE CONSEQUENCE** |
| **50% road disruption** | None (no source defines corridor closure percentages) | VAYUBODHAK spatial disruption rule | **PROTOTYPE** |
| **100% road disruption** | None (no source defines corridor closure percentages) | VAYUBODHAK spatial disruption rule | **PROTOTYPE** |
| **4h drainage window** | None (no source prescribes post-storm reopening delay hours) | VAYUBODHAK drainage delay approximation | **PROTOTYPE** |
| **12h drainage window** | None (no source prescribes post-storm reopening delay hours) | VAYUBODHAK drainage delay approximation | **PROTOTYPE** |
| **0.90 flowering deficit** | ICAR/FAO agronomic research supports anthesis physiological sensitivity | Exact static scalar assignment across all cultivars | **PROTOTYPE** |
| **CPWD DSR rate** | CPWD Delhi Schedule of Rates published government plinth rate schedule | Selected baseline reference rate for direct replacement | **SOURCE REFERENCE** |
| **CACP MSP benchmark** | Statutory policy procurement price benchmark published by GoI CACP | Selected baseline reference benchmark for crop valuation | **SOURCE REFERENCE** |

---

## 3. Canonical Sectoral Method Matrix Table

| Method ID | Conceptual Source | Exact Source Statement / Standard | What the Source Actually Proves | What the Source Does NOT Prove | Implemented Formula | Research-Supported Elements | Prototype Elements | Scientific Validation Status | Production Governance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IMPACT-METH-PHYS-BLDG-001** | BMTPC Vulnerability Atlas of India (3rd Ed, 2019) & NBC 2016 | Categorizes buildings into typologies (Kutcha, Semi-Pucca, Pucca, RCC) and classifies relative susceptibility under meteorological hazards. | Proves that building structural materials create differential physical vulnerability under meteorological stress. | Does NOT prescribe exact continuous damage ratios ($0.02$ to $0.90$) or empirical fragility curves. | $\text{DamageRatio} = \text{Matrix}(\text{Typology}, \text{Severity}) \times (0.5 + 0.5 \cdot V)$ | Structural typology categorization & relative vulnerability ranking. | Discrete numerical damage ratios, linear scaling heuristic, and damage state thresholds. | **UNVALIDATED PROTOTYPE**: Heuristic engineering matrix; software-tested only. | **ACTIVE**: Gated in `ImpactMethodRegistry`; blocked if structural class unspecified. |
| **IMPACT-METH-INFRA-ROAD-001** | IMD NWFC Criteria & Indian Roads Congress (IRC:SP:42 & IRC:SP:50) | Specifies rainfall classification criteria and notes surface water accumulation depth trafficability considerations. | Proves rainfall threshold categories and water depth relevance to vehicle transit. | Does NOT define corridor disruption length fractions ($50\%$, $100\%$) or fixed drainage delay durations ($4\text{h}$, $12\text{h}$). | $\text{DisruptedLength} = L \cdot \text{Trigger}(\text{Rain} \ge 64.5\,\text{mm} \lor \text{Depth} \ge 0.3\,\text{m})$ | Meteorological rainfall threshold and water depth trafficability concepts. | Disrupted length percentage rules ($50\%$, $100\%$) and estimated drainage windows ($4\text{h}$, $12\text{h}$). | **UNVALIDATED PROTOTYPE**: Heuristic engineering rule; software-tested only. | **ACTIVE**: Gated in `ImpactMethodRegistry`; strictly enforces Exposure $\ne$ Disruption. |
| **IMPACT-METH-SERV-HOSP-001** | WHO Hospital Safety Index (HSI, 2015) & NDMA Hospital Safety Guidelines | Outlines critical lifeline requirements for hospitals during disasters, emphasizing road access, power continuity, and surge capacity. | Proves that external flooding and transport disruption severely impair healthcare operational capacity. | Does NOT prescribe numerical capacity strain percentages ($25\%$, $50\%$, $80\%$) or patient mortality formulas. | $\text{CapacityAtRisk} = \text{Beds} \times \text{StrainFactor}(\text{Severity}, \text{RoadCut})$ | Lifeline criticality of hospitals and access dependency on surrounding transport corridors. | Numerical strain factors ($0.05, 0.25, 0.50, 0.80$) and bed capacity at risk multipliers. | **UNVALIDATED PROTOTYPE**: Operational service strain heuristic; zero clinical mortality forecast. | **ACTIVE**: Gated in `ImpactMethodRegistry`; strictly prohibits patient casualty fields. |
| **IMPACT-METH-SERV-SCHL-001** | NDMA National School Safety Policy (2016) | Mandates educational facility suspension during severe meteorological warnings and identifies schools as potential emergency relief shelters. | Proves institutional continuity disruption during severe weather events and dual-use shelter potential. | Does NOT model physical student injuries, structural failure, or casualty counts. | $\text{Disrupted} = 1.0 \quad (\text{if Severity} \ge \text{WARNING}); \quad \text{Shelter} = \text{True}$ | Protocol to suspend educational sessions and evaluate dual-use relief shelter potential. | Binary disruption threshold and heuristic shelter suitability assessment. | **UNVALIDATED PROTOTYPE**: Institutional administrative continuity heuristic. | **ACTIVE**: Gated in `ImpactMethodRegistry`; strictly prohibits student injury fields. |
| **IMPACT-METH-AGRI-YIELD-001** | ICAR Agromet Advisories & FAO-56 Crop Evapotranspiration Guidelines | Documents crop growth stages and identifies flowering/anthesis as the most physiologically sensitive stage to thermal and moisture extremes. | Proves that identical hazard intensity creates vastly different physiological yield impacts across crop phenological stages. | Does NOT define a universal static $90\%$ yield-loss equation across all cultivars, soil types, and environments. | $\text{YieldLoss} = \text{Matrix}(\text{Stage}, \text{Severity}) \times (0.6 + 0.4 \cdot V)$ | Crop phenological stage identification and anthesis physiological vulnerability. | Discrete yield loss percentages (including $0.90$ flowering parameter) and baseline normal yield assumption. | **UNVALIDATED PROTOTYPE**: Phenological sensitivity index; not a dynamic crop model (DSSAT). | **ACTIVE**: Gated in `ImpactMethodRegistry`; strictly enforces Exposure $\ne$ Yield Loss. |
| **IMPACT-METH-ECON-DIRECT-001** | CPWD Delhi Schedule of Rates (DSR 2021) & CACP Minimum Support Prices (MSP 2023-24) | Publishes standard government plinth area construction rates per square meter and statutory minimum support prices per metric tonne. | Proves official reference rate schedules and policy procurement price benchmarks in Indian Rupees (INR). | Does NOT validate actual observed local reconstruction losses or post-disaster dynamic market price surges. | $\text{Loss}_{\text{INR}} = \text{AssetValuation}_{\text{INR}} \times \text{DamageRatio}$ | Official unit rates (₹/sqm, ₹/tonne) and direct physical replacement valuation reference schedules. | Linear damage-ratio economic multiplier ($\text{Loss} = \text{Value} \cdot \text{Ratio}$) and indicative loss classification. | **UNVALIDATED PROTOTYPE**: Linear valuation multiplier; excludes indirect macroeconomic loss. | **ACTIVE**: Gated in `ImpactMethodRegistry`; requires explicit currency, date, and source. |

---

## 4. Deep Parameter Audit & Source Verification Table

| Numerical Parameter | Implemented Value | Cited Institutional Source | What the Source Directly Verifies | Scientific Classification | Methodological Audit & Governance Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Heavy Rainfall Threshold** | `64.5 mm / 24h` | IMD National Weather Forecasting Centre (NWFC) Criteria | Verifies standard meteorological criteria for "Heavy Rainfall" across India subdivisions. | **SOURCE_SUPPORTED_INPUT_THRESHOLD** | Validated meteorological input classification. Downstream consequence (50% road disruption) is prototype. |
| **Very Heavy Rainfall Threshold** | `115.6 mm / 24h` | IMD NWFC Meteorological Criteria | Verifies standard criteria for "Very Heavy Rainfall". | **SOURCE_SUPPORTED_INPUT_THRESHOLD** | Validated meteorological input classification. Downstream consequence (100% road disruption) is prototype. |
| **Moderate Road Inundation Depth** | `0.3 m (30 cm)` | IRC:SP:42 (Road Drainage) & IRC:SP:50 (Urban Drainage) | Verifies standard curb design considerations and passenger car exhaust sill clearance limit. | **SOURCE-ALIGNED ENGINEERING INPUT** | Source-aligned engineering input regarding trafficability. The resulting 50% length disruption is a VAYUBODHAK prototype. |
| **Severe Road Inundation Depth** | `0.5 m (50 cm)` | IRC:SP:50 & MoRTH Flood Resilience Guidelines | Verifies axle height limit considerations for commercial vehicles and buses. | **SOURCE-ALIGNED ENGINEERING INPUT** | Source-aligned engineering input regarding trafficability. The resulting 100% length disruption is a VAYUBODHAK prototype. |
| **CPWD Plinth Rates (Kutcha)** | `₹3,500 / sqm` | CPWD Delhi Schedule of Rates (DSR 2021) / PAR 2020 | Baseline earthen/thatch plinth replacement cost schedule under Delhi indexation (100). | **SOURCE REFERENCE** | Reference valuation schedule. Represents indicative baseline rate, not actual local contractor reconstruction bid. |
| **CPWD Plinth Rates (Semi-Pucca)** | `₹7,500 / sqm` | CPWD DSR 2021 / PAR 2020 | Unburnt brick / asbestos roof baseline reconstruction rate schedule. | **SOURCE REFERENCE** | Reference valuation schedule. |
| **CPWD Plinth Rates (Pucca Brick)** | `₹14,000 / sqm` | CPWD DSR 2021 / PAR 2020 | Load-bearing burnt brick masonry building replacement rate schedule. | **SOURCE REFERENCE** | Reference valuation schedule. |
| **CPWD Plinth Rates (Pucca RCC)** | `₹22,000 / sqm` | CPWD DSR 2021 / PAR 2020 | Standard framed RCC multistory residential/commercial plinth rate schedule. | **SOURCE REFERENCE** | Reference valuation schedule. |
| **CPWD Plinth Rates (Steel Frame)** | `₹26,000 / sqm` | CPWD DSR 2021 / PAR 2020 | Portal frame structural steel industrial/commercial warehouse rate schedule. | **SOURCE REFERENCE** | Reference valuation schedule. |
| **CACP Paddy MSP** | `₹21,830 / tonne` | CACP Minimum Support Prices 2023-24 (Kharif) | Statutory procurement price: ₹2,183 per quintal for common grade paddy. | **SOURCE REFERENCE** | Statutory policy procurement benchmark. Excludes local mandi spot price volatility; not actual farmer revenue. |
| **CACP Wheat MSP** | `₹22,750 / tonne` | CACP Minimum Support Prices 2023-24 (Rabi) | Statutory procurement price: ₹2,275 per quintal for milling wheat. | **SOURCE REFERENCE** | Statutory policy procurement benchmark. |
| **CACP Cotton MSP** | `₹66,200 / tonne` | CACP Minimum Support Prices 2023-24 (Kharif) | Statutory procurement price: ₹6,620 per quintal for medium staple cotton. | **SOURCE REFERENCE** | Statutory policy procurement benchmark. |
| **Anthesis Extreme Yield Deficit** | `90% (0.90)` | ICAR Agromet Advisories & FAO-56 / FAO Paper 66 | Agronomic research confirms anthesis/flowering is a critical physiological bottleneck where severe thermal or moisture stress impairs pollination. | **VAYUBODHAK_PROTOTYPE_ASSUMPTION** | **AUDITED (Fix #4 & #5)**: Physiological sensitivity is research-supported. The static scalar $0.90$ across all cultivars, soils, and microclimates is a VAYUBODHAK prototype heuristic, not a universal ICAR/FAO yield-loss equation. Unverified universal numeric claims have been removed. |
| **Road Disruption Length Fractions** | `50% & 100%` | IRC & NDMA Urban Flooding Guidelines | IRC proves water accumulation causes operational trafficability disruption, but does NOT prescribe fixed corridor percentages. | **VAYUBODHAK_PROTOTYPE_ASSUMPTION** | **AUDITED (Fix #2)**: Disruption length fractions ($50\%$ and $100\%$) are prototype engineering heuristics for spatial corridor planning. |
| **Road Drainage Durations** | `4.0h & 12.0h` | IRC:SP:42 Drainage Guidelines | Proves drainage duration depends on hydraulic gradient, outfall capacity, and culvert clearance. | **VAYUBODHAK_PROTOTYPE_ASSUMPTION** | **AUDITED (Fix #2)**: The $4\text{h}$ and $12\text{h}$ windows are prototype heuristic approximations, not official police reopening decrees or hydrodynamic recession times. |
| **Hospital Capacity Strain Ratios** | `5%, 25%, 50%, 80%` | WHO Hospital Safety Index (HSI 2015) & NDMA Lifelines | HSI proves hospital functionality depends critically on external road access and utility lifelines. | **VAYUBODHAK_PROTOTYPE_ASSUMPTION** | **AUDITED (Fix #7)**: The discrete strain multipliers ($0.05, 0.25, 0.50, 0.80$) are prototype operational approximations. Strictly excludes patient mortality or clinical harm. |
| **School Operational Disruption** | `1.0 facility / 24h` | NDMA School Safety Policy (2016) | Mandates educational suspension during severe warnings and identifies schools for relief shelters. | **VAYUBODHAK_PROTOTYPE_ASSUMPTION** | **AUDITED (Fix #7)**: Disruption indicator and shelter suitability flag are operational prototype rules. Does NOT model student injuries or statutory DM closure orders. |
| **Linear Economic Loss Multiplier** | $\text{Loss} = \text{Value} \cdot \text{Ratio}$ | FEMA Hazus & UNDRR Direct Loss Accounting Concepts | UNDRR and Hazus use depth-damage curves to estimate direct structural repair costs. | **VAYUBODHAK_PROTOTYPE_ASSUMPTION** | **AUDITED (Fix #8)**: Directly models indicative physical replacement cost in INR. Strictly excludes indirect macroeconomic disruptions, business interruption, or price surge. |

---

## 5. Governance and Negative Boundary Verification

### What Authoritative Sources Prove:
1. **BMTPC / NBC 2016**: Proves structural typology susceptibility order ($\text{Kutcha} > \text{Semi-Pucca} > \text{Pucca} > \text{RCC}$).
2. **IMD NWFC Criteria**: Proves 24-hour rainfall classification thresholds ($\ge 64.5$ mm Heavy, $\ge 115.6$ mm Very Heavy).
3. **IRC / MoRTH**: Proves transit waterlogging depth relevance ($\ge 0.3\,\text{m}$ passenger vehicles, $\ge 0.5\,\text{m}$ commercial vehicles).
4. **WHO / NDMA Lifelines**: Proves critical infrastructure service dependence on access corridors.
5. **ICAR / FAO-56**: Proves anthesis/flowering crop vulnerability to environmental stress.
6. **CPWD / CACP**: Proves standard unit reconstruction rate schedules and policy procurement price benchmarks in INR.

### What Authoritative Sources Do NOT Prove:
1. No source defines or validates an empirical post-disaster insurance loss curve for VAYUBODHAK.
2. No source mandates that damage scales as a linear multiplier of damage ratio.
3. No source justifies converting hazard polygons directly into casualty or fatality counts.
4. No source permits asserting that a building will "definitely collapse" or that a hospital will "certainly shut down."
5. No source defines universal 90% agricultural yield loss across all cultivars, environments, and soils.
6. No source validates road corridor closure percentages or exact reopening delay hours.

All such unsupported inferences are strictly rejected at the engine, documentation, and Claim Gate boundaries.
