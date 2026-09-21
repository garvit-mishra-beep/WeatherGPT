"""Deterministic Hazard Rule Registry for VAYUBODHAK Phase 3.

Seeds versioned, source-cited hazard rules aligned with the existing
ThresholdConfig (IMD-MET-2024.1) and Phase 2A Source Registry.

CRITICAL SAFETY RULE:
    Every implemented threshold records its basis (OFFICIAL / RESEARCH / ENGINEERING).
    An engineering assumption must NEVER silently become an official scientific threshold.
    Only ACTIVE rules may execute in production.
"""

from typing import Dict, List, Optional

from app.hazard.models import (
    BasisType,
    HazardRule,
    HazardRuleStatus,
    HazardState,
    HazardType,
)


class HazardRuleRegistry:
    """Catalog and governance registry for deterministic hazard evaluation rules."""

    def __init__(self) -> None:
        self._rules: Dict[str, HazardRule] = {}
        self._initialize_canonical_rules()

    def _initialize_canonical_rules(self) -> None:
        """Seeds canonical hazard rules derived from IMD/WMO standards and VAYUBODHAK research."""
        canonical_rules: List[HazardRule] = [
            # ------------------------------------------------------------------
            # 1. Heavy Rainfall — IMD 24h Accumulation Standard
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-RAIN-IMD-24H-v1",
                hazard_type=HazardType.HEAVY_RAINFALL,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD Standard Operational Guidelines for Severe Weather Warnings (2024): "
                                 "Heavy (64.5-115.5mm), Very Heavy (115.6-204.4mm), Extremely Heavy (≥204.5mm) in 24h",
                claim_id="CLM-HAZARD-HEAVY-RAIN-IMD",
                required_inputs=["precipitation_mm_24h"],
                required_evidence_classes=["OBSERVATION", "FORECAST"],
                validity_conditions="India; 24-hour accumulation period; surface gauge or calibrated satellite/NWP estimate",
                output_states={
                    "< 64.5 mm": "NONE",
                    "64.5 - 115.5 mm": "WATCH",
                    "115.6 - 204.4 mm": "WARNING",
                    "≥ 204.5 mm": "EXTREME",
                },
                reason_codes=["RAIN_NONE", "RAIN_HEAVY", "RAIN_VERY_HEAVY", "RAIN_EXTREMELY_HEAVY"],
                effective_from="2024-01-01",
                what_it_proves="Proves that observed/forecast 24h precipitation accumulation meets IMD classification thresholds.",
                what_it_does_not_prove="Does NOT prove flooding, waterlogging, structural inundation, or infrastructure failure. "
                                      "A rainfall indicator does not automatically prove flooding.",
                applicability="India — standard meteorological warning thresholds",
                known_limitations="Does not account for sub-daily burst intensity, antecedent soil moisture, or orographic enhancement.",
            ),

            # ------------------------------------------------------------------
            # 2. Heat — IMD Heatwave Standard (Plains)
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-HEAT-IMD-PLAINS-v1",
                hazard_type=HazardType.HEAT,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD Heatwave Criteria (Plains): Heatwave ≥40°C, Severe Heatwave ≥45°C "
                                 "(or departure ≥4.5°C / ≥6.5°C from normal)",
                claim_id="CLM-HAZARD-HEAT-IMD",
                required_inputs=["temperature_max_c"],
                required_evidence_classes=["OBSERVATION", "FORECAST"],
                validity_conditions="India Plains region; maximum daily temperature",
                output_states={
                    "< 40.0°C": "NONE",
                    "40.0 - 44.9°C": "WARNING",
                    "≥ 45.0°C": "EXTREME",
                },
                reason_codes=["HEAT_NONE", "HEAT_WAVE", "HEAT_SEVERE_WAVE"],
                effective_from="2024-01-01",
                what_it_proves="Proves that the maximum temperature meets IMD heatwave classification for Plains.",
                what_it_does_not_prove="Does NOT prove an official IMD heatwave declaration (requires IMD bulletin). "
                                      "Separate: temperature condition ≠ heat-stress indicator ≠ official heatwave warning.",
                applicability="India Plains region only. Coastal (37°C) and Hills (30°C) thresholds require separate rules.",
                known_limitations="Uses ambient air temperature only. Does not account for humidity-based heat index or "
                                  "wet-bulb globe temperature (WBGT).",
            ),

            # ------------------------------------------------------------------
            # 3. Strong Wind / Gale — IMD Wind Scale
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-WIND-GALE-v1",
                hazard_type=HazardType.STRONG_WIND,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD Wind Hazard Scale: Strong (40-49 km/h), Squall (50-61 km/h), "
                                 "Gale (62-88 km/h), Severe Gale (≥89 km/h)",
                required_inputs=["wind_speed_kmh"],
                required_evidence_classes=["OBSERVATION", "FORECAST"],
                validity_conditions="Surface (10m anemometer height) wind speed",
                output_states={
                    "< 40 km/h": "NONE",
                    "40 - 61 km/h": "WATCH",
                    "62 - 88 km/h": "WARNING",
                    "≥ 89 km/h": "SEVERE",
                },
                reason_codes=["WIND_NONE", "WIND_STRONG", "WIND_GALE", "WIND_SEVERE_GALE"],
                effective_from="2024-01-01",
                what_it_proves="Proves that surface wind speed meets IMD gale/squall thresholds.",
                what_it_does_not_prove="Does NOT prove cyclonic circulation. "
                                      "Wind ≠ Cyclone unless official cyclone warning exists.",
                applicability="General surface wind hazard assessment",
            ),

            # ------------------------------------------------------------------
            # 4. Cyclone — IMD 8-Stage Classification
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-CYCLONE-IMD-8STAGE-v1",
                hazard_type=HazardType.CYCLONE,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD 8-Stage Tropical Cyclone Intensity Scale: "
                                 "Depression (31-49), CS (50-61), DD (50+), SCS (89-117), "
                                 "VSCS (118-166), ESCS (167-221), SuCS (≥222 km/h)",
                required_inputs=["wind_speed_kmh"],
                required_evidence_classes=["OFFICIAL_WARNING"],
                validity_conditions="Requires official IMD cyclone warning OR deep barometric depression (≤990 hPa) "
                                    "alongside gale-force winds. Do not derive independently when authoritative warning exists.",
                output_states={
                    "Official IMD cyclone warning active": "Use official warning level",
                    "Deep depression + gale winds confirmed": "WARNING",
                    "No official warning, no barometric evidence": "UNDETERMINED",
                },
                reason_codes=["CYCLONE_OFFICIAL", "CYCLONE_BAROMETRIC", "CYCLONE_NONE"],
                effective_from="2024-01-01",
                what_it_proves="Classifies cyclonic intensity per IMD 8-stage scale when official evidence exists.",
                what_it_does_not_prove="Does NOT replace official IMD cyclone bulletins. "
                                      "Do not derive an official cyclone warning independently when authoritative warning evidence exists.",
                applicability="Indian Ocean basin; requires IMD warning bulletin or barometric evidence",
                known_limitations="Storm surge estimates are heuristic (SLOSH/ADCIRC unavailable). "
                                  "Track geometry requires official bulletin.",
            ),

            # ------------------------------------------------------------------
            # 5. Fog — Dense Fog Visibility Threshold
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-FOG-DENSE-v1",
                hazard_type=HazardType.FOG,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD Fog Classification: Moderate (200-500m), Dense (50-200m), Very Dense (<50m)",
                required_inputs=["visibility_m"],
                required_evidence_classes=["OBSERVATION"],
                validity_conditions="Surface visibility observation from calibrated sensor or manual METAR",
                output_states={
                    "> 500 m": "NONE",
                    "200 - 500 m": "WATCH",
                    "50 - 200 m": "WARNING",
                    "< 50 m": "SEVERE",
                },
                reason_codes=["FOG_NONE", "FOG_MODERATE", "FOG_DENSE", "FOG_VERY_DENSE"],
                effective_from="2024-01-01",
                what_it_proves="Proves that observed visibility meets IMD fog classification thresholds.",
                what_it_does_not_prove="Does NOT prove transport disruption unless research defines the relationship.",
                applicability="Surface visibility at observation station",
            ),

            # ------------------------------------------------------------------
            # 6. Lightning — Convective Instability (Engineering Prototype)
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-LIGHTNING-CONV-v1",
                hazard_type=HazardType.LIGHTNING,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.ENGINEERING_PROTOTYPE,
                source_reference="CAPE/Lifted Index convective instability heuristic. "
                                 "CAPE ≥1000 J/kg moderate, ≥2500 J/kg severe. "
                                 "Lifted Index ≤-3 unstable, ≤-6 very unstable. "
                                 "Basis: WMO thunderstorm diagnostic guidance.",
                required_inputs=["cape_jkg", "lifted_index"],
                required_evidence_classes=["FORECAST"],
                validity_conditions="NWP-derived convective parameters. "
                                    "This is an ENGINEERING PROTOTYPE — not an observed lightning detection.",
                output_states={
                    "CAPE < 1000 and LI > -3": "NONE",
                    "CAPE ≥ 1000 or LI ≤ -3": "WATCH",
                    "CAPE ≥ 2500 or LI ≤ -6": "WARNING",
                },
                reason_codes=["LIGHTNING_NONE", "LIGHTNING_MODERATE_INSTABILITY", "LIGHTNING_SEVERE_INSTABILITY"],
                effective_from="2024-01-01",
                what_it_proves="Indicates convective instability potential from NWP diagnostics.",
                what_it_does_not_prove="Does NOT prove observed lightning. "
                                      "Diagnostic model potential ≠ observed strike. "
                                      "If lightning observations/nowcasts are absent, the system must say evidence is unavailable.",
                applicability="NWP grid point or sounding-derived parameters",
                known_limitations="False alarm rate is high for CAPE-only thresholds. "
                                  "No direct lightning detection network integrated.",
            ),

            # ------------------------------------------------------------------
            # 7. Flood — CWC Official Warning Only
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-FLOOD-CWC-OFFICIAL-v1",
                hazard_type=HazardType.FLOOD,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="Central Water Commission (CWC) official flood forecasts and hydrological bulletins. "
                                 "CWC flood levels are station-specific and must NOT be silently interpolated nationwide.",
                claim_id="CLM-HAZARD-FLOOD-CWC",
                required_inputs=["cwc_flood_warning"],
                required_evidence_classes=["OFFICIAL_WARNING"],
                validity_conditions="Active CWC flood warning for a specific gauging station/river basin. "
                                    "Do not invent a national flood threshold.",
                output_states={
                    "No CWC warning": "NONE",
                    "CWC warning active": "Use CWC warning level",
                },
                reason_codes=["FLOOD_NONE", "FLOOD_CWC_OFFICIAL"],
                effective_from="2024-01-01",
                what_it_proves="Proves that CWC has issued an official hydrological warning for the specified station/basin.",
                what_it_does_not_prove="Does NOT prove nationwide flooding. "
                                      "CWC flood levels are station-specific. "
                                      "A rainfall indicator does not automatically prove flooding.",
                applicability="CWC-monitored river basins and gauging stations only",
                known_limitations="Coverage limited to CWC monitoring network. "
                                  "No interpolation to unmonitored locations.",
            ),

            # ------------------------------------------------------------------
            # 8. Official Warning Passthrough
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-OFFICIAL-WARNING-v1",
                hazard_type=HazardType.OFFICIAL_WARNING,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD/CWC/NDMA-SACHET official warning bulletins",
                required_inputs=["official_warning_evidence"],
                required_evidence_classes=["OFFICIAL_WARNING"],
                validity_conditions="Active official warning from E0 source authority",
                output_states={
                    "Green/None": "NONE",
                    "Yellow/Watch": "WATCH",
                    "Orange/Alert": "WARNING",
                    "Red/Warning": "EXTREME",
                },
                reason_codes=["OFFICIAL_GREEN", "OFFICIAL_YELLOW", "OFFICIAL_ORANGE", "OFFICIAL_RED"],
                effective_from="2024-01-01",
                what_it_proves="Preserves and passes through the official warning exactly as issued.",
                what_it_does_not_prove="VAYUBODHAK does not validate or override the official warning. "
                                      "The official severity is immutable.",
                applicability="All E0 authority official warning bulletins",
            ),

            # ------------------------------------------------------------------
            # 9. Landslide Susceptibility — GSI (Static)
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-LANDSLIDE-GSI-SUSCEPT-v1",
                hazard_type=HazardType.LANDSLIDE_SUSCEPTIBILITY,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="Geological Survey of India (GSI) National Landslide Susceptibility Mapping",
                required_inputs=["gsi_susceptibility_class"],
                required_evidence_classes=["SPATIAL_STATIC"],
                validity_conditions="GSI susceptibility maps for the queried location",
                output_states={
                    "Low susceptibility": "NONE",
                    "Moderate susceptibility": "WATCH",
                    "High susceptibility": "WARNING",
                    "Very High susceptibility": "SEVERE",
                },
                reason_codes=["LANDSLIDE_LOW", "LANDSLIDE_MODERATE", "LANDSLIDE_HIGH", "LANDSLIDE_VERY_HIGH"],
                effective_from="2024-01-01",
                what_it_proves="Proves the geological susceptibility classification of the terrain.",
                what_it_does_not_prove="Does NOT prove a landslide event has occurred or will occur. "
                                      "Susceptibility ≠ trigger evidence ≠ observed event ≠ official warning. "
                                      "Do not invent universal rainfall thresholds for landslide occurrence.",
                applicability="GSI-mapped terrain only",
                known_limitations="Static baseline; does not incorporate real-time rainfall triggering.",
            ),

            # ------------------------------------------------------------------
            # 10. Cold Wave — IMD Standard
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-COLD-WAVE-IMD-v1",
                hazard_type=HazardType.COLD_WAVE,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
                source_reference="IMD Coldwave Criteria: Minimum temp ≤10°C (cold wave), ≤4°C (severe cold wave), "
                                 "or departure ≤-4.5°C / ≤-6.5°C from normal",
                required_inputs=["temperature_min_c"],
                required_evidence_classes=["OBSERVATION", "FORECAST"],
                validity_conditions="India; minimum daily temperature at surface station",
                output_states={
                    "> 10.0°C": "NONE",
                    "4.1 - 10.0°C": "WARNING",
                    "≤ 4.0°C": "SEVERE",
                },
                reason_codes=["COLD_NONE", "COLD_WAVE", "COLD_SEVERE_WAVE"],
                effective_from="2024-01-01",
                what_it_proves="Proves that minimum temperature meets IMD cold wave threshold.",
                what_it_does_not_prove="Does NOT prove frost damage to crops without additional agricultural evidence.",
                applicability="India — primarily north India plains during winter",
            ),

            # ------------------------------------------------------------------
            # Compound Hazard Rules
            # ------------------------------------------------------------------
            HazardRule(
                rule_id="HZR-CMP-RAIN-WIND-v1",
                hazard_type=HazardType.COMPOUND,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.RESEARCH_SUPPORTED,
                source_reference="WMO Multi-Hazard Early Warning Systems Guidelines (No. 1150): "
                                 "Co-occurring heavy precipitation and gale-force winds amplify "
                                 "structural disruption and surface runoff risk.",
                required_inputs=["precipitation_mm_24h", "wind_speed_kmh"],
                validity_conditions="Both HEAVY_RAINFALL and STRONG_WIND hazards concurrently active "
                                    "with temporal and spatial overlap verified",
                output_states={
                    "Both present + overlap verified": "WARNING",
                    "Missing component": "NONE",
                },
                reason_codes=["COMPOUND_RAIN_WIND"],
                what_it_proves="Proves concurrent exposure to heavy rain and strong wind at the same location and time.",
                what_it_does_not_prove="Does NOT prove structural failure or specific infrastructure damage.",
            ),

            HazardRule(
                rule_id="HZR-CMP-HEAT-HUMID-v1",
                hazard_type=HazardType.COMPOUND,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.RESEARCH_SUPPORTED,
                source_reference="WMO Heat-Health Warning Systems guidance: "
                                 "Co-occurring high temperature (≥35°C) and high humidity (≥65%) "
                                 "creates critical apparent heat stress conditions.",
                required_inputs=["temperature_max_c", "humidity_pct"],
                validity_conditions="Temperature ≥35°C and relative humidity ≥65% at same location and time",
                output_states={
                    "Both thresholds met + overlap": "WARNING",
                    "Missing component": "NONE",
                },
                reason_codes=["COMPOUND_HEAT_HUMIDITY"],
                what_it_proves="Proves concurrent high temperature and humidity creating elevated physiological thermal stress.",
                what_it_does_not_prove="Does NOT prove heatstroke casualties or official heatwave declaration.",
            ),

            HazardRule(
                rule_id="HZR-CMP-RAIN-SATURATED-v1",
                hazard_type=HazardType.COMPOUND,
                rule_version="1.0",
                status=HazardRuleStatus.ACTIVE,
                basis_type=BasisType.ENGINEERING_PROTOTYPE,
                source_reference="VAYUBODHAK engineering heuristic: Heavy rain (≥35mm) on saturated soil (≥75%) "
                                 "amplifies surface runoff and flash flood potential. "
                                 "This is a PROTOTYPE rule, not an operationally validated flood threshold.",
                required_inputs=["precipitation_mm_24h", "soil_moisture_pct"],
                validity_conditions="Precipitation ≥35mm and soil moisture ≥75% at same location",
                output_states={
                    "Both thresholds met + overlap": "WATCH",
                    "Missing component": "NONE",
                },
                reason_codes=["COMPOUND_RAIN_SATURATED_SOIL"],
                what_it_proves="Indicates elevated surface runoff potential from rainfall on saturated soils.",
                what_it_does_not_prove="Does NOT prove flooding. A rainfall indicator combined with soil moisture "
                                      "does not automatically prove flood inundation.",
                known_limitations="Soil moisture data may be satellite-derived (coarse resolution). "
                                  "This is an ENGINEERING PROTOTYPE rule.",
            ),
        ]

        for rule in canonical_rules:
            self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[HazardRule]:
        """Retrieves a rule by ID."""
        return self._rules.get(rule_id)

    def get_active_rules(self, hazard_type: Optional[HazardType] = None) -> List[HazardRule]:
        """Returns all ACTIVE rules, optionally filtered by hazard type."""
        rules = [r for r in self._rules.values() if r.status == HazardRuleStatus.ACTIVE]
        if hazard_type:
            rules = [r for r in rules if r.hazard_type == hazard_type]
        return rules

    def register_rule(self, rule: HazardRule) -> HazardRule:
        """Registers or updates a hazard rule."""
        self._rules[rule.rule_id] = rule
        return rule

    def list_rules(self, status: Optional[HazardRuleStatus] = None) -> List[HazardRule]:
        """Lists rules, optionally filtered by status."""
        if status:
            return [r for r in self._rules.values() if r.status == status]
        return list(self._rules.values())


# Singleton instance
hazard_rule_registry = HazardRuleRegistry()
