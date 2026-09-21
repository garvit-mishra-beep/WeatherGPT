"""Method Registry for VAYUBODHAK Phase 7 — Potential Impact Modeling.

Provides an immutable, governed registry of impact calculation methods, formulas,
scientific classifications, lifecycle statuses, and input/output contracts.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.evidence.models import SourceAuthorityLevel
from app.exposure.models import SpatialResolution
from app.impact.models import ImpactMethodStatus, ImpactType
from app.vulnerability.models import MethodClassification


class ImpactMethod(BaseModel):
    """Metadata specification for a registered impact evaluation methodology."""
    method_id: str = Field(..., description="Unique method identifier")
    method_name: str = Field(..., description="Descriptive human-readable title")
    impact_type: ImpactType = Field(..., description="Sectoral impact category")
    hazard_types: List[str] = Field(..., description="Applicable hazard categories")
    entity_types: List[str] = Field(..., description="Applicable exposed asset classes")
    formula_description: str = Field(..., description="Mathematical or logical formulation")
    inputs_required: List[str] = Field(..., description="List of required input parameters")
    output_units: str = Field(..., description="Measurement unit of impact output")
    method_version: str = Field(default="1.0.0", description="SemVer release version")
    status: ImpactMethodStatus = Field(default=ImpactMethodStatus.ACTIVE)
    source_basis: str = Field(..., description="Scientific or institutional basis")
    claim_basis: str = Field(..., description="Permitted claim registration link")
    classification: MethodClassification = Field(default=MethodClassification.VAYUBODHAK_PROTOTYPE)
    scientific_validation_status: str = Field(
        default="UNVALIDATED_PROTOTYPE: Heuristic engineering model; software-tested, not empirically loss-calibrated",
    )
    spatial_applicability: SpatialResolution = Field(default=SpatialResolution.BUILDING_FOOTPRINT)
    source_supported_inputs: List[str] = Field(
        default_factory=list,
        description="Hazard, asset, or vulnerability inputs directly supported by official standards or research",
    )
    prototype_consequence_parameters: List[str] = Field(
        default_factory=list,
        description="Downstream consequence rules, multipliers, and durations assigned via VAYUBODHAK prototype heuristics",
    )
    exact_source_defined_consequences: Optional[str] = Field(
        default=None,
        description="Exact consequence percentages or equations directly defined by cited sources (None unless directly defined)",
    )
    prototype_disclosure: str = Field(
        default="Prototype scenario-based consequence approximation; software-verified, not empirically loss-calibrated",
        description="Mandatory user-facing prototype disclosure statement",
    )
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    what_it_measures: str = Field(...)
    what_it_does_not_measure: str = Field(...)


class ImpactMethodRegistry:
    """Thread-safe singleton registry storing registered impact methodologies."""

    def __init__(self) -> None:
        self._methods: Dict[str, ImpactMethod] = {}
        self._register_default_methods()

    def register_method(self, method: ImpactMethod) -> None:
        """Registers a new impact method."""
        self._methods[method.method_id] = method

    def get_method(self, method_id: str) -> Optional[ImpactMethod]:
        """Retrieves a registered method by ID."""
        return self._methods.get(method_id)

    def list_methods(self, status: Optional[ImpactMethodStatus] = None) -> List[ImpactMethod]:
        """Lists registered methods, optionally filtered by lifecycle status."""
        if status is None:
            return list(self._methods.values())
        return [m for m in self._methods.values() if m.status == status]

    def validate_method_active(self, method_id: str) -> ImpactMethod:
        """Validates that a method exists and is ACTIVE. Raises ValueError if not."""
        method = self.get_method(method_id)
        if not method:
            raise ValueError(f"Impact method '{method_id}' is not registered.")
        if method.status != ImpactMethodStatus.ACTIVE:
            raise ValueError(f"Impact method '{method_id}' is {method.status.value}, not ACTIVE.")
        return method

    def _register_default_methods(self) -> None:
        """Registers the canonical Phase 7 impact methods."""

        # 1. Building Physical Damage Model
        self.register_method(
            ImpactMethod(
                method_id="IMPACT-METH-PHYS-BLDG-001",
                method_name="BMTPC Typology Building Physical Damage State & Ratio Prototype",
                impact_type=ImpactType.PHYSICAL_DAMAGE,
                hazard_types=["FLOOD", "HEAVY_RAINFALL", "CYCLONE", "STRONG_WIND", "LANDSLIDE_SUSCEPTIBILITY"],
                entity_types=["BUILDING"],
                formula_description="DamageState & DamageRatio = f(HazardSeverityTier, StructuralTypology, FragilityScore)",
                inputs_required=["hazard_severity", "structural_class", "footprint_area_sqm", "vulnerability_score"],
                output_units="sqm (affected) and ratio [0.0, 1.0]",
                method_version="1.0.0",
                status=ImpactMethodStatus.ACTIVE,
                source_basis="BMTPC Vulnerability Atlas of India construction typologies and NDMA damage guidelines",
                claim_basis="CLM-IMPACT-MODEL-001",
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                scientific_validation_status="UNVALIDATED_PROTOTYPE: Engineering heuristic discrete damage matrix; verified via unit tests, not an empirical fragility curve.",
                spatial_applicability=SpatialResolution.BUILDING_FOOTPRINT,
                source_supported_inputs=[
                    "BMTPC Vulnerability Atlas building typologies (Kutcha, Semi-Pucca, Pucca, Steel Frame) (source-supported input classification)",
                    "NBC 2016 building construction classification and material vulnerability context (source-supported standard)",
                ],
                prototype_consequence_parameters=[
                    "Discrete damage ratios (0.02, 0.10, 0.25, 0.50, 0.90) mapped across hazard tiers (VAYUBODHAK prototype engineering heuristic; not an empirical fragility curve)",
                    "Categorical qualitative damage state mapping (VAYUBODHAK prototype heuristic)",
                ],
                exact_source_defined_consequences="None: Neither BMTPC nor NBC defines mathematical damage ratios or post-disaster continuous loss percentages.",
                prototype_disclosure="Prototype building physical damage approximation based on BMTPC typology archetypes; scenario-based consequence approximation, not an empirical fragility curve or loss-calibrated model.",
                assumptions=[
                    "Building structural vulnerability conforms to BMTPC archetypes",
                    "Damage state indicates potential physical degradation, not certain collapse",
                ],
                limitations=[
                    "Exposure != Collapse: Categorical damage states do not forecast structural collapse",
                    "Foundation depth, maintenance condition, and unpermitted modifications are unmodeled",
                ],
                what_it_measures="Potential structural damage state and estimated damage ratio for exposed buildings.",
                what_it_does_not_measure="Building collapse certainty, occupant casualty counts, or exact repair bills.",
            )
        )

        # 2. Road Infrastructure Transport Disruption Model
        self.register_method(
            ImpactMethod(
                method_id="IMPACT-METH-INFRA-ROAD-001",
                method_name="Road Infrastructure Transport Disruption Prototype",
                impact_type=ImpactType.INFRASTRUCTURE_DISRUPTION,
                hazard_types=["FLOOD", "HEAVY_RAINFALL"],
                entity_types=["ROAD"],
                formula_description="DisruptedLength = Length * DisruptionTrigger(Rainfall >= 64.5mm or Inundation >= 0.3m)",
                inputs_required=["hazard_severity", "observed_rainfall_mm", "road_length_km", "road_classification"],
                output_units="km (disrupted length) and hours (estimated disruption duration)",
                method_version="1.0.0",
                status=ImpactMethodStatus.ACTIVE,
                source_basis="IRC (Indian Roads Congress) drainage guidelines and MoRTH flood resilience standards",
                claim_basis="CLM-IMPACT-MODEL-001",
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                scientific_validation_status="UNVALIDATED_PROTOTYPE: Engineering heuristic combining source-supported input thresholds with prototype disruption consequence rules; not hydrodynamically calibrated to micro-topography.",
                spatial_applicability=SpatialResolution.ROAD_SEGMENT,
                source_supported_inputs=[
                    "IMD 24h rainfall classification thresholds: Heavy Rainfall >= 64.5 mm, Very Heavy Rainfall >= 115.6 mm (SOURCE_SUPPORTED_INPUT_THRESHOLD)",
                    "IRC road drainage guidelines (IRC:SP:42 & IRC:SP:50) trafficability water depth considerations: 0.3 m car exhaust clearance, 0.5 m heavy vehicle axle clearance (SOURCE-ALIGNED ENGINEERING INPUT)",
                ],
                prototype_consequence_parameters=[
                    "50% corridor disruption length for moderate trigger (VAYUBODHAK prototype consequence assumption)",
                    "100% corridor disruption length for severe trigger (VAYUBODHAK prototype consequence assumption)",
                    "4.0 hours drainage duration window for moderate trigger (VAYUBODHAK prototype consequence assumption)",
                    "12.0 hours drainage duration window for severe trigger (VAYUBODHAK prototype consequence assumption)",
                ],
                exact_source_defined_consequences="None: Neither IMD nor IRC defines percentage corridor disruption fractions or post-storm traffic reopening delay durations.",
                prototype_disclosure="Prototype road transport disruption approximation based on IMD input thresholds and IRC-aligned water depth inputs; disrupted corridor fractions and durations are uncalibrated VAYUBODHAK prototype rules, not observed traffic closures.",
                assumptions=[
                    "Road segment lacks elevated culverts or active stormwater pump systems",
                    "Rainfall exceeding 64.5 mm (IMD Heavy) creates waterlogging on surface corridors",
                ],
                limitations=[
                    "Exposure != Disruption: Crossing hazard perimeter does not mean road is closed unless threshold exceeded",
                    "Micro-topography, culvert clogging, and real-time traffic diversions are unmodeled",
                ],
                what_it_measures="Potential roadway waterlogging disruption length and estimated disruption duration.",
                what_it_does_not_measure="Traffic accident casualties, vehicle damages, or official police road closures.",
            )
        )

        # 3. Healthcare Service Disruption Model
        self.register_method(
            ImpactMethod(
                method_id="IMPACT-METH-SERV-HOSP-001",
                method_name="Healthcare Facility Operational Capacity at Risk Prototype",
                impact_type=ImpactType.SERVICE_DISRUPTION,
                hazard_types=["FLOOD", "CYCLONE", "HEAT", "HEAVY_RAINFALL"],
                entity_types=["HOSPITAL"],
                formula_description="CapacityAtRisk = TotalBeds * OperationalStrainFactor(HazardSeverity, AccessDisruption)",
                inputs_required=["hazard_severity", "hospital_bed_capacity", "access_road_disrupted"],
                output_units="beds (capacity at risk)",
                method_version="1.0.0",
                status=ImpactMethodStatus.ACTIVE,
                source_basis="WHO Hospital Safety Index (HSI) and NDMA Hospital Safety Guidelines",
                claim_basis="CLM-IMPACT-MODEL-001",
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                scientific_validation_status="UNVALIDATED_PROTOTYPE: Operational service strain indicator; scenario-based heuristic, strictly does NOT model patient mortality, morbidity, or clinical harm.",
                spatial_applicability=SpatialResolution.POINT,
                source_supported_inputs=[
                    "WHO Hospital Safety Index (HSI 2015) operational lifeline dependency principles (RESEARCH-SUPPORTED CONCEPT)",
                    "NDMA Hospital Safety Guidelines multi-hazard operational criteria (RESEARCH-SUPPORTED CONCEPT)",
                ],
                prototype_consequence_parameters=[
                    "Discrete operational capacity strain multipliers (0.05, 0.25, 0.50, 0.80) mapped to hazard tiers (VAYUBODHAK prototype heuristic)",
                    "External feeder road cut capacity strain amplification (50% to 80%) (VAYUBODHAK prototype heuristic)",
                ],
                exact_source_defined_consequences="None: Neither WHO nor NDMA defines quantitative bed strain percentages or patient capacity reduction formulas.",
                prototype_disclosure="Prototype healthcare operational strain approximation; scenario-based consequence approximation, strictly does NOT model patient mortality or casualties.",
                assumptions=[
                    "Healthcare facility serves as localized critical lifeline during extreme events",
                    "Severe surrounding waterlogging impedes patient transit and ambulance access",
                ],
                limitations=[
                    "Physical Exposure != Service Shutdown: Backup power generators and redundant access are unmodeled",
                    "Strictly does NOT model patient mortality, morbidity, or medical supply chain failure",
                ],
                what_it_measures="Potential inpatient capacity at risk and facility operational access strain.",
                what_it_does_not_measure="Patient casualties, disease outbreaks, or hospital evacuation mandates.",
            )
        )

        # 4. Educational Facility Service Disruption Model
        self.register_method(
            ImpactMethod(
                method_id="IMPACT-METH-SERV-SCHL-001",
                method_name="Educational Facility Operational Disruption Prototype",
                impact_type=ImpactType.SERVICE_DISRUPTION,
                hazard_types=["FLOOD", "CYCLONE", "HEAVY_RAINFALL"],
                entity_types=["SCHOOL"],
                formula_description="DisruptionState = SeverityThreshold(Hazard >= WARNING ? DISRUPTED : OPERATIONAL)",
                inputs_required=["hazard_severity", "school_type", "enrollment_capacity"],
                output_units="count (facilities disrupted)",
                method_version="1.0.0",
                status=ImpactMethodStatus.ACTIVE,
                source_basis="NDMA School Safety Policy and Disaster Management Guidelines",
                claim_basis="CLM-IMPACT-MODEL-001",
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                scientific_validation_status="UNVALIDATED_PROTOTYPE: Institutional administrative continuity heuristic; strictly does NOT model student injuries or casualties.",
                spatial_applicability=SpatialResolution.POINT,
                source_supported_inputs=[
                    "NDMA School Safety Policy institutional disaster continuity guidelines (RESEARCH-SUPPORTED CONCEPT)",
                    "National Disaster Management Plan school shelter dual-use policy framework (RESEARCH-SUPPORTED CONCEPT)",
                ],
                prototype_consequence_parameters=[
                    "Binary operational suspension trigger at WARNING hazard severity (VAYUBODHAK prototype heuristic)",
                    "Precautionary operational suspension ratio (0.50 at WARNING, 1.0 at SEVERE) (VAYUBODHAK prototype heuristic)",
                    "Emergency relief shelter prototype suitability assessment (prototype heuristic; uncertified without facility-specific engineering audit)",
                ],
                exact_source_defined_consequences="None: NDMA policies mandate safety precautions and identify dual-use potential, but do not provide automated facility-level mathematical closure equations.",
                prototype_disclosure="Prototype educational service disruption approximation; scenario-based consequence approximation, strictly does NOT model student injuries or casualties.",
                assumptions=[
                    "Severe meteorological warnings prompt school closure or emergency shelter conversion",
                ],
                limitations=[
                    "Exposure != Structural Collapse: Facility closure does not imply physical building failure",
                    "Strictly does NOT model student injury, casualty counts, or administrative closure decrees",
                ],
                what_it_measures="Educational facility operational disruption and shelter availability consequence.",
                what_it_does_not_measure="Student casualty prediction or official administrative school closure orders.",
            )
        )

        # 5. Agricultural Phenological Yield Loss Model
        self.register_method(
            ImpactMethod(
                method_id="IMPACT-METH-AGRI-YIELD-001",
                method_name="Crop Phenological Yield Consequence Prototype",
                impact_type=ImpactType.AGRICULTURAL_IMPACT,
                hazard_types=["FLOOD", "HEAVY_RAINFALL", "HEAT", "STRONG_WIND"],
                entity_types=["AGRICULTURE"],
                formula_description="PotentialYieldLossPct = StageSensitivity * HazardIntensityFactor",
                inputs_required=["crop_name", "growth_stage", "planted_acres", "hazard_severity", "hazard_intensity"],
                output_units="acres (affected) and percentage [0.0, 1.0] (potential yield loss)",
                method_version="1.0.0",
                status=ImpactMethodStatus.ACTIVE,
                source_basis="ICAR / IMD Agromet advisories and FAO-56 crop coefficient guidelines",
                claim_basis="CLM-IMPACT-MODEL-001",
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                scientific_validation_status="UNVALIDATED_PROTOTYPE: Phenological stress sensitivity index; scenario-based engineering prototype, NOT a calibrated biophysical dynamic crop simulation (e.g. DSSAT) or PMFBY loss curve.",
                spatial_applicability=SpatialResolution.ADMINISTRATIVE_POLYGON,
                source_supported_inputs=[
                    "ICAR Agromet Advisory phenological stage definitions (Germination, Vegetative, Flowering/Anthesis, Maturity) (SOURCE-SUPPORTED INPUT CONCEPT)",
                    "FAO-56 and FAO Paper 66 crop yield response principles and stage sensitivity concepts (RESEARCH-SUPPORTED CONCEPT)",
                ],
                prototype_consequence_parameters=[
                    "Discrete phenological yield loss deficit ratio matrix (0.00 to 0.90) across growth stages and hazard tiers (VAYUBODHAK prototype assumption; not an empirical equation)",
                    "0.90 yield-deficit scalar for extreme anthesis/flowering stress (VAYUBODHAK prototype assumption; not a universal ICAR/FAO yield-loss equation)",
                    "Baseline normal yield baseline assumption (tonnes/acre) (prototype baseline assumption)",
                ],
                exact_source_defined_consequences="None: Neither ICAR nor FAO defines a static universal percentage yield-loss equation across all cultivars, micro-climates, and soil types.",
                prototype_disclosure="Prototype agricultural phenological yield loss approximation; scenario-based consequence approximation, not calibrated against biophysical crop models (DSSAT) or PMFBY insurance claims; not a universal equation.",
                assumptions=[
                    "Crop physiological vulnerability varies dramatically by growth stage (flowering most sensitive)",
                    "Submergence or extreme thermal stress during anthesis sharply impairs pollination",
                ],
                limitations=[
                    "Vulnerability != Absolute Crop Failure: Micro-climate, cultivar genetics, and drainage are unmodeled",
                    "Does NOT calculate crop insurance payouts or final post-harvest grain weigh-in",
                ],
                what_it_measures="Potential crop yield loss percentage and affected planted area in acres.",
                what_it_does_not_measure="Guaranteed harvest failure, farmer suicide risk, or official relief compensations.",
            )
        )

        # 6. Direct Economic Loss Valuation Model
        self.register_method(
            ImpactMethod(
                method_id="IMPACT-METH-ECON-DIRECT-001",
                method_name="Direct Asset Physical Damage Economic Valuation Prototype",
                impact_type=ImpactType.ECONOMIC_LOSS,
                hazard_types=["ALL_SUPPORTED"],
                entity_types=["BUILDING", "AGRICULTURE"],
                formula_description="EstimatedLossINR = AssetValuationINR * DamageRatio",
                inputs_required=["asset_valuation_inr", "damage_ratio", "valuation_source", "valuation_date"],
                output_units="INR (Indian Rupees)",
                method_version="1.0.0",
                status=ImpactMethodStatus.ACTIVE,
                source_basis="CPWD (Central Public Works Department) Delhi Schedule of Rates (DSR) and CACP Minimum Support Prices (MSP)",
                claim_basis="CLM-IMPACT-MODEL-001",
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                scientific_validation_status="UNVALIDATED_PROTOTYPE: Linear damage-ratio economic multiplier; computes an indicative direct physical loss estimate, not actual market loss, official contractor tender bids, or insurance claim settlements.",
                spatial_applicability=SpatialResolution.BUILDING_FOOTPRINT,
                source_supported_inputs=[
                    "CPWD Delhi Schedule of Rates (DSR 2021) baseline plinth area reconstruction rates in INR/sqm (SOURCE REFERENCE)",
                    "CACP Minimum Support Prices (MSP 2023-24) statutory procurement price benchmarks in INR/tonne (SOURCE REFERENCE)",
                ],
                prototype_consequence_parameters=[
                    "Linear damage-ratio economic loss formulation: Loss = AssetValue * DamageRatio (VAYUBODHAK prototype assumption)",
                    "Indirect macroeconomic loss exclusion boundary (prototype analytical boundary)",
                    "Output classification as an indicative direct physical loss estimate (not actual loss or contractor bid) (VAYUBODHAK prototype assumption)",
                ],
                exact_source_defined_consequences="None: Official schedules define reference unit rates and procurement price benchmarks; they do NOT define disaster damage ratios or dynamic loss models.",
                prototype_disclosure="Indicative direct physical replacement cost estimate based on official benchmark schedules (CPWD reference rate / CACP MSP benchmark) and prototype damage ratios; not actual market loss, official reconstruction cost, or insurance indemnity settlement.",
                assumptions=[
                    "Replacement/repair cost scales linearly with estimated physical damage ratio",
                    "Valuation baseline uses standard schedules without dynamic post-disaster price inflation",
                ],
                limitations=[
                    "Direct physical loss ONLY: Excludes supply-chain disruption, wage losses, and GDP impacts",
                    "Inflation, land value appreciation, and salvage value deductions are unmodeled",
                ],
                what_it_measures="Estimated direct physical repair/replacement cost in Indian Rupees (INR).",
                what_it_does_not_measure="Indirect macroeconomic loss, business interruption, or insurance indemnity settlements.",
            )
        )


# Global singleton instance
impact_method_registry = ImpactMethodRegistry()
