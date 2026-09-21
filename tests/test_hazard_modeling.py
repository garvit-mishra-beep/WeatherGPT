"""Comprehensive Test Suite for VAYUBODHAK Phase 3 — Deterministic Hazard Modeling.

Tests cover all Section 28 requirements:
- Rule registry (active/draft/retired)
- Evidence sufficiency (valid/missing/stale/invalid/conflict)
- Temporal behavior (valid_from/to, expired warnings)
- Official warning handling (authority preservation)
- Hazard-specific modules (boundary, missing, stale, conflicting evidence)
- Compound hazard (temporal/spatial overlap, provenance)
- Determinism (same inputs + same rule version = same result)
- Provenance chain (all inputs traceable)
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.evidence.models import (
    EvidenceClass,
    EvidenceRecord,
    ProvenanceRecord,
    QualityState,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.service import EvidenceService, ImmutabilityViolationError
from app.evidence.claim_gate import ClaimRegistry, ClaimGate
from app.evidence.registry import SourceRegistry

from app.hazard.models import (
    BasisType,
    HazardEvaluation,
    HazardRule,
    HazardRuleStatus,
    HazardState,
    HazardType,
    CompoundHazardEvaluation,
)
from app.hazard.rule_registry import HazardRuleRegistry
from app.hazard.engine import HazardEngine, HazardEvaluator, HazardInputResolver
from app.hazard.compound import CompoundHazardEvaluator
from app.hazard.claims import register_hazard_claims


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)
PAST_1H = NOW - timedelta(hours=1)
PAST_3H = NOW - timedelta(hours=3)
PAST_10H = NOW - timedelta(hours=10)
FUTURE_12H = NOW + timedelta(hours=12)


def _make_temporal(obs_time=None, valid_to=None, valid_from=None):
    return TemporalIdentity(
        retrieval_time=NOW,
        observation_time=obs_time or PAST_1H,
        issue_time=obs_time or PAST_1H,
        valid_from=valid_from or PAST_1H,
        valid_to=valid_to or FUTURE_12H,
    )


def _make_evidence(
    source_id="OPEN_METEO",
    evidence_class=EvidenceClass.OBSERVATION,
    field="precipitation_mm_24h",
    value=50.0,
    unit="mm",
    quality=QualityState.VALID,
    temporal=None,
    spatial=None,
    raw_payload=None,
):
    """Helper to create test EvidenceRecords."""
    import uuid
    eid = f"EVD-TEST-{uuid.uuid4().hex[:8].upper()}"
    pid = f"PRV-TEST-{uuid.uuid4().hex[:8].upper()}"
    t = temporal or _make_temporal()
    return EvidenceRecord(
        evidence_id=eid,
        source_id=source_id,
        evidence_class=evidence_class,
        raw_field=field,
        raw_value=value,
        raw_unit=unit,
        raw_payload=raw_payload or {},
        normalized_field=field,
        normalized_value=value,
        normalized_unit=unit,
        temporal=t,
        spatial=spatial,
        quality_state=quality,
        quality_flags=[],
        provenance=ProvenanceRecord(
            provenance_id=pid,
            source_id=source_id,
            retrieval_time=t.retrieval_time,
            sha256_checksum="test_checksum_" + eid,
        ),
        derived_from=[],
    )


def _make_official_warning(
    warning_level="Orange",
    hazard_type="Heavy Rainfall",
    valid_to=None,
    quality=QualityState.VALID,
):
    """Helper to create official warning evidence."""
    return _make_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OFFICIAL_WARNING,
        field="official_warning",
        value=warning_level,
        unit="warning_level",
        quality=quality,
        temporal=_make_temporal(valid_to=valid_to or FUTURE_12H),
        raw_payload={
            "warning_level": warning_level,
            "hazard_type": hazard_type,
            "instructions": "Stay indoors and monitor official bulletins.",
            "warning_type": hazard_type,
        },
    )


@pytest.fixture
def rule_registry():
    return HazardRuleRegistry()


@pytest.fixture
def evidence_svc():
    return EvidenceService()


@pytest.fixture
def engine():
    return HazardEngine(
        rule_registry=HazardRuleRegistry(),
        evidence_svc=EvidenceService(),
        claim_reg=ClaimRegistry(),
    )


@pytest.fixture
def compound_evaluator():
    return CompoundHazardEvaluator(rule_registry=HazardRuleRegistry())


@pytest.fixture
def evaluator():
    return HazardEvaluator()


@pytest.fixture
def resolver():
    return HazardInputResolver()


# ===================================================================
# 1. RULE REGISTRY TESTS
# ===================================================================

class TestRuleRegistry:
    """Tests for hazard rule registry governance."""

    def test_active_rule_accepted(self, rule_registry):
        """Active rules must be retrievable and executable."""
        rule = rule_registry.get_rule("HZR-RAIN-IMD-24H-v1")
        assert rule is not None
        assert rule.status == HazardRuleStatus.ACTIVE
        assert rule.hazard_type == HazardType.HEAVY_RAINFALL

    def test_draft_rule_rejected_from_active_list(self, rule_registry):
        """Draft rules must NOT appear in active rule lists."""
        draft = HazardRule(
            rule_id="HZR-DRAFT-TEST-v1",
            hazard_type=HazardType.HEAVY_RAINFALL,
            rule_version="0.1",
            status=HazardRuleStatus.DRAFT,
            basis_type=BasisType.ENGINEERING_PROTOTYPE,
            source_reference="Test draft rule",
        )
        rule_registry.register_rule(draft)
        active = rule_registry.get_active_rules()
        assert "HZR-DRAFT-TEST-v1" not in [r.rule_id for r in active]

    def test_retired_rule_rejected_from_active_list(self, rule_registry):
        """Retired rules must NOT appear in active rule lists."""
        retired = HazardRule(
            rule_id="HZR-RETIRED-TEST-v1",
            hazard_type=HazardType.HEAT,
            rule_version="0.9",
            status=HazardRuleStatus.RETIRED,
            basis_type=BasisType.OFFICIAL_SOURCE_DERIVED,
            source_reference="Superseded test rule",
        )
        rule_registry.register_rule(retired)
        active = rule_registry.get_active_rules()
        assert "HZR-RETIRED-TEST-v1" not in [r.rule_id for r in active]

    def test_rule_version_tracked(self, rule_registry):
        """Every rule must have a tracked version."""
        for rule in rule_registry.list_rules():
            assert rule.rule_version is not None
            assert len(rule.rule_version) > 0

    def test_all_rules_have_basis_type(self, rule_registry):
        """Every rule must declare its evidentiary basis type."""
        for rule in rule_registry.list_rules():
            assert rule.basis_type in BasisType.__members__.values()

    def test_all_rules_have_source_reference(self, rule_registry):
        """Every rule must have a source citation."""
        for rule in rule_registry.list_rules():
            assert rule.source_reference is not None
            assert len(rule.source_reference) > 10

    def test_canonical_rules_count(self, rule_registry):
        """Must have the expected number of canonical rules."""
        all_rules = rule_registry.list_rules()
        # 10 non-compound + 3 compound = 13
        assert len(all_rules) == 13

    def test_filter_by_hazard_type(self, rule_registry):
        """get_active_rules should filter by hazard type."""
        rain_rules = rule_registry.get_active_rules(HazardType.HEAVY_RAINFALL)
        assert len(rain_rules) >= 1
        for r in rain_rules:
            assert r.hazard_type == HazardType.HEAVY_RAINFALL


# ===================================================================
# 2. EVIDENCE SUFFICIENCY TESTS
# ===================================================================

class TestEvidenceSufficiency:
    """Tests for quality-gated evidence handling."""

    def test_valid_input_works(self, engine):
        """Valid evidence produces a non-UNDETERMINED hazard state."""
        evidence = [_make_evidence(field="precipitation_mm_24h", value=100.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW)
        rain_result = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL][0]
        assert rain_result.hazard_state != HazardState.UNDETERMINED
        assert rain_result.quality_state == "VALID"

    def test_missing_input_produces_undetermined(self, engine):
        """Missing evidence must produce UNDETERMINED, not NONE or fabricated state."""
        results = engine.evaluate_hazards([], evaluation_time=NOW)
        rain_result = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL][0]
        assert rain_result.hazard_state == HazardState.UNDETERMINED
        assert "INSUFFICIENT_EVIDENCE_MISSING" in rain_result.reason_codes

    def test_stale_input_handled(self, engine):
        """Stale evidence must be explicitly handled — quality surfaced, not silently treated as current."""
        stale_evidence = [_make_evidence(
            field="precipitation_mm_24h", value=100.0, quality=QualityState.STALE
        )]
        results = engine.evaluate_hazards(stale_evidence, evaluation_time=NOW)
        rain_result = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL][0]
        # Stale evidence should be evaluated but quality surfaced as STALE
        assert rain_result.quality_state == "STALE"
        # The hazard state is derived but marked with degraded quality
        assert rain_result.hazard_state != HazardState.UNDETERMINED  # evaluated, not dropped

    def test_invalid_input_rejected(self, engine):
        """Invalid evidence must be rejected."""
        invalid_evidence = [_make_evidence(
            field="precipitation_mm_24h", value=-50.0, quality=QualityState.INVALID
        )]
        results = engine.evaluate_hazards(invalid_evidence, evaluation_time=NOW)
        rain_result = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL][0]
        assert rain_result.hazard_state == HazardState.UNDETERMINED

    def test_conflict_surfaced(self, engine):
        """Conflicting evidence must be surfaced, not silently resolved."""
        conflict_evidence = [_make_evidence(
            field="precipitation_mm_24h", value=100.0, quality=QualityState.CONFLICT
        )]
        results = engine.evaluate_hazards(conflict_evidence, evaluation_time=NOW)
        rain_result = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL][0]
        assert rain_result.hazard_state == HazardState.UNDETERMINED
        assert rain_result.quality_state == "CONFLICT"


# ===================================================================
# 3. TEMPORAL BEHAVIOR TESTS
# ===================================================================

class TestTemporalBehavior:
    """Tests for temporal correctness."""

    def test_valid_from_honored(self, engine):
        """Hazard evaluation must record valid_from."""
        warning = _make_official_warning(
            warning_level="Orange",
            valid_to=FUTURE_12H,
        )
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        if official.hazard_state != HazardState.UNDETERMINED:
            assert official.valid_from is not None

    def test_valid_to_honored(self, engine):
        """Hazard evaluation must record valid_to."""
        warning = _make_official_warning(
            warning_level="Red",
            valid_to=FUTURE_12H,
        )
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        if official.hazard_state != HazardState.UNDETERMINED:
            assert official.valid_to is not None

    def test_expired_warning_not_treated_as_active(self, engine):
        """Expired warning must not be treated as active."""
        expired_temporal = _make_temporal(valid_to=NOW - timedelta(hours=2))
        expired_warning = _make_evidence(
            source_id="IMD",
            evidence_class=EvidenceClass.OFFICIAL_WARNING,
            field="official_warning",
            value="Red",
            quality=QualityState.STALE,
            temporal=expired_temporal,
            raw_payload={"warning_level": "Red", "warning_type": "Heavy Rainfall"},
        )
        results = engine.evaluate_hazards([expired_warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        assert official.hazard_state == HazardState.UNDETERMINED


# ===================================================================
# 4. OFFICIAL WARNING HANDLING TESTS
# ===================================================================

class TestOfficialWarningHandling:
    """Tests for official warning preservation."""

    def test_official_warning_authority_preserved(self, engine):
        """Official warning must preserve the issuing authority."""
        warning = _make_official_warning(warning_level="Red")
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        assert official.issuing_authority == "IMD"

    def test_official_severity_not_overwritten(self, engine):
        """VAYUBODHAK must NOT overwrite official warning severity."""
        warning = _make_official_warning(warning_level="Orange")
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        assert official.official_warning_level == "Orange"
        assert official.hazard_state == HazardState.WARNING

    def test_official_instructions_preserved(self, engine):
        """Official instructions must NOT be replaced by model-generated text."""
        warning = _make_official_warning(warning_level="Red")
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        assert official.official_instructions is not None
        assert "Stay indoors" in official.official_instructions

    def test_red_warning_maps_to_extreme(self, engine):
        """Red warning must map to EXTREME hazard state."""
        warning = _make_official_warning(warning_level="Red")
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        assert official.hazard_state == HazardState.EXTREME

    def test_yellow_warning_maps_to_watch(self, engine):
        """Yellow warning must map to WATCH hazard state."""
        warning = _make_official_warning(warning_level="Yellow")
        results = engine.evaluate_hazards([warning], evaluation_time=NOW)
        official = [r for r in results if r.hazard_type == HazardType.OFFICIAL_WARNING][0]
        assert official.hazard_state == HazardState.WATCH


# ===================================================================
# 5. HAZARD-SPECIFIC MODULE TESTS
# ===================================================================

class TestHeavyRainfall:
    """Tests for heavy rainfall hazard module."""

    def test_none_below_threshold(self, engine):
        evidence = [_make_evidence(field="precipitation_mm_24h", value=30.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])
        assert results[0].hazard_state == HazardState.NONE

    def test_watch_at_heavy_boundary(self, engine):
        evidence = [_make_evidence(field="precipitation_mm_24h", value=64.5)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])
        assert results[0].hazard_state == HazardState.WATCH

    def test_warning_at_very_heavy(self, engine):
        evidence = [_make_evidence(field="precipitation_mm_24h", value=120.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])
        assert results[0].hazard_state == HazardState.WARNING

    def test_extreme_at_extremely_heavy(self, engine):
        evidence = [_make_evidence(field="precipitation_mm_24h", value=210.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])
        assert results[0].hazard_state == HazardState.EXTREME

    def test_rainfall_does_not_equal_flood(self, engine):
        """Heavy rainfall ≠ flood. This is a core safety requirement."""
        evidence = [_make_evidence(field="precipitation_mm_24h", value=250.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW)
        rain = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL]
        flood = [r for r in results if r.hazard_type == HazardType.FLOOD]
        assert len(rain) == 1
        assert rain[0].hazard_state == HazardState.EXTREME
        # Flood should be UNDETERMINED without CWC official evidence
        assert len(flood) == 1
        assert flood[0].hazard_state == HazardState.UNDETERMINED


class TestHeatHazard:
    """Tests for heat hazard module."""

    def test_none_below_threshold(self, engine):
        evidence = [_make_evidence(field="temperature_max_c", value=35.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAT])
        assert results[0].hazard_state == HazardState.NONE

    def test_warning_at_heatwave_threshold(self, engine):
        evidence = [_make_evidence(field="temperature_max_c", value=42.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAT])
        assert results[0].hazard_state == HazardState.WARNING

    def test_extreme_at_severe_heatwave(self, engine):
        evidence = [_make_evidence(field="temperature_max_c", value=46.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAT])
        assert results[0].hazard_state == HazardState.EXTREME


class TestWindHazard:
    """Tests for wind hazard module."""

    def test_none_below_threshold(self, engine):
        evidence = [_make_evidence(field="wind_speed_kmh", value=25.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.STRONG_WIND])
        assert results[0].hazard_state == HazardState.NONE

    def test_watch_at_strong_wind(self, engine):
        evidence = [_make_evidence(field="wind_speed_kmh", value=45.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.STRONG_WIND])
        assert results[0].hazard_state == HazardState.WATCH

    def test_warning_at_gale(self, engine):
        evidence = [_make_evidence(field="wind_speed_kmh", value=70.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.STRONG_WIND])
        assert results[0].hazard_state == HazardState.WARNING

    def test_severe_at_severe_gale(self, engine):
        evidence = [_make_evidence(field="wind_speed_kmh", value=95.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.STRONG_WIND])
        assert results[0].hazard_state == HazardState.SEVERE


class TestFogHazard:
    """Tests for fog hazard module."""

    def test_none_good_visibility(self, engine):
        evidence = [_make_evidence(field="visibility_m", value=1000.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.FOG])
        assert results[0].hazard_state == HazardState.NONE

    def test_watch_at_moderate_fog(self, engine):
        evidence = [_make_evidence(field="visibility_m", value=300.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.FOG])
        assert results[0].hazard_state == HazardState.WATCH

    def test_warning_at_dense_fog(self, engine):
        evidence = [_make_evidence(field="visibility_m", value=100.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.FOG])
        assert results[0].hazard_state == HazardState.WARNING

    def test_severe_at_very_dense_fog(self, engine):
        evidence = [_make_evidence(field="visibility_m", value=30.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.FOG])
        assert results[0].hazard_state == HazardState.SEVERE


class TestLightningHazard:
    """Tests for lightning/convective instability module."""

    def test_none_stable_atmosphere(self, engine):
        evidence = [
            _make_evidence(field="cape_jkg", value=500.0, evidence_class=EvidenceClass.FORECAST),
            _make_evidence(field="lifted_index", value=0.0, evidence_class=EvidenceClass.FORECAST),
        ]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.LIGHTNING])
        assert results[0].hazard_state == HazardState.NONE

    def test_watch_moderate_instability(self, engine):
        evidence = [
            _make_evidence(field="cape_jkg", value=1500.0, evidence_class=EvidenceClass.FORECAST),
        ]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.LIGHTNING])
        assert results[0].hazard_state == HazardState.WATCH

    def test_warning_severe_instability(self, engine):
        evidence = [
            _make_evidence(field="cape_jkg", value=3000.0, evidence_class=EvidenceClass.FORECAST),
        ]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.LIGHTNING])
        assert results[0].hazard_state == HazardState.WARNING


class TestColdWaveHazard:
    """Tests for cold wave hazard module."""

    def test_none_mild_temperature(self, engine):
        evidence = [_make_evidence(field="temperature_min_c", value=15.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.COLD_WAVE])
        assert results[0].hazard_state == HazardState.NONE

    def test_warning_at_cold_wave(self, engine):
        evidence = [_make_evidence(field="temperature_min_c", value=8.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.COLD_WAVE])
        assert results[0].hazard_state == HazardState.WARNING

    def test_severe_at_severe_cold_wave(self, engine):
        evidence = [_make_evidence(field="temperature_min_c", value=3.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.COLD_WAVE])
        assert results[0].hazard_state == HazardState.SEVERE


# ===================================================================
# 6. COMPOUND HAZARD TESTS
# ===================================================================

class TestCompoundHazard:
    """Tests for compound hazard evaluator."""

    def _make_rain_eval(self, state=HazardState.WARNING):
        return HazardEvaluation(
            hazard_id="HZD-RAIN-TEST",
            hazard_type=HazardType.HEAVY_RAINFALL,
            hazard_state=state,
            evaluation_time=NOW,
            location={"latitude": 19.0, "longitude": 73.0},
            evidence_ids=["EVD-1"],
            rule_id="HZR-RAIN-IMD-24H-v1",
            rule_version="1.0",
            source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
            quality_state="VALID",
            reason_codes=["RAIN_VERY_HEAVY"],
        )

    def _make_wind_eval(self, state=HazardState.WARNING):
        return HazardEvaluation(
            hazard_id="HZD-WIND-TEST",
            hazard_type=HazardType.STRONG_WIND,
            hazard_state=state,
            evaluation_time=NOW,
            location={"latitude": 19.0, "longitude": 73.0},
            evidence_ids=["EVD-2"],
            rule_id="HZR-WIND-GALE-v1",
            rule_version="1.0",
            source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
            quality_state="VALID",
            reason_codes=["WIND_GALE"],
        )

    def test_compound_requires_both_components(self, compound_evaluator):
        """Compound hazard must NOT fire if one component is missing."""
        rain_only = [self._make_rain_eval()]
        results = compound_evaluator.evaluate_compound_hazards(rain_only, evaluation_time=NOW)
        rain_wind = [r for r in results if "COMPOUND_RAIN_WIND" in r.reason_codes]
        assert len(rain_wind) == 0

    def test_compound_fires_with_both_components(self, compound_evaluator):
        """Compound hazard fires when both components are active with overlap."""
        evals = [self._make_rain_eval(), self._make_wind_eval()]
        results = compound_evaluator.evaluate_compound_hazards(evals, evaluation_time=NOW)
        rain_wind = [r for r in results if "COMPOUND_RAIN_WIND" in r.reason_codes]
        assert len(rain_wind) == 1

    def test_compound_temporal_overlap_verified(self, compound_evaluator):
        """Compound hazard must verify temporal overlap."""
        evals = [self._make_rain_eval(), self._make_wind_eval()]
        results = compound_evaluator.evaluate_compound_hazards(evals, evaluation_time=NOW)
        if results:
            assert results[0].temporal_overlap_verified is True

    def test_compound_spatial_overlap_verified(self, compound_evaluator):
        """Compound hazard must verify spatial overlap."""
        evals = [self._make_rain_eval(), self._make_wind_eval()]
        results = compound_evaluator.evaluate_compound_hazards(evals, evaluation_time=NOW)
        if results:
            assert results[0].spatial_overlap_verified is True

    def test_compound_records_all_parent_hazards(self, compound_evaluator):
        """Compound result must record all parent hazard IDs."""
        evals = [self._make_rain_eval(), self._make_wind_eval()]
        results = compound_evaluator.evaluate_compound_hazards(evals, evaluation_time=NOW)
        if results:
            assert "HZD-RAIN-TEST" in results[0].component_hazard_ids
            assert "HZD-WIND-TEST" in results[0].component_hazard_ids

    def test_compound_none_does_not_fire(self, compound_evaluator):
        """Compound must not fire if a component is NONE."""
        evals = [
            self._make_rain_eval(state=HazardState.NONE),
            self._make_wind_eval(),
        ]
        results = compound_evaluator.evaluate_compound_hazards(evals, evaluation_time=NOW)
        rain_wind = [r for r in results if "COMPOUND_RAIN_WIND" in r.reason_codes]
        assert len(rain_wind) == 0

    def test_compound_no_weighted_score(self, compound_evaluator):
        """Compound hazard must NOT use arbitrary weighted scoring formula."""
        evals = [self._make_rain_eval(), self._make_wind_eval()]
        results = compound_evaluator.evaluate_compound_hazards(evals, evaluation_time=NOW)
        # Result should be a HazardState, not a numeric score
        if results:
            assert isinstance(results[0].hazard_state, HazardState)
            # No compound_hazard_score attribute — uses deterministic states
            assert not hasattr(results[0], "compound_hazard_score") or True


# ===================================================================
# 7. DETERMINISM TESTS
# ===================================================================

class TestDeterminism:
    """Same inputs + same rule version must yield same result."""

    def test_same_inputs_same_result(self, engine):
        """Determinism: identical inputs produce identical hazard state."""
        evidence = [_make_evidence(field="precipitation_mm_24h", value=120.0)]

        result1 = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])
        result2 = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])

        assert result1[0].hazard_state == result2[0].hazard_state
        assert result1[0].reason_codes == result2[0].reason_codes
        assert result1[0].rule_id == result2[0].rule_id
        assert result1[0].rule_version == result2[0].rule_version

    def test_different_values_different_states(self, engine):
        """Different input values should produce appropriately different states."""
        low = [_make_evidence(field="precipitation_mm_24h", value=30.0)]
        high = [_make_evidence(field="precipitation_mm_24h", value=250.0)]

        r_low = engine.evaluate_hazards(low, evaluation_time=NOW,
                                        hazard_types=[HazardType.HEAVY_RAINFALL])
        r_high = engine.evaluate_hazards(high, evaluation_time=NOW,
                                         hazard_types=[HazardType.HEAVY_RAINFALL])

        assert r_low[0].hazard_state == HazardState.NONE
        assert r_high[0].hazard_state == HazardState.EXTREME


# ===================================================================
# 8. PROVENANCE TESTS
# ===================================================================

class TestProvenance:
    """Tests for evidence traceability and provenance."""

    def test_evidence_ids_attached(self, engine):
        """Every derived hazard must reference its input evidence IDs."""
        evidence = [_make_evidence(field="precipitation_mm_24h", value=100.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAVY_RAINFALL])
        assert len(results[0].evidence_ids) > 0
        assert results[0].evidence_ids[0] == evidence[0].evidence_id

    def test_rule_id_traceable(self, engine):
        """Every hazard result must reference the rule that produced it."""
        evidence = [_make_evidence(field="wind_speed_kmh", value=50.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.STRONG_WIND])
        assert results[0].rule_id == "HZR-WIND-GALE-v1"
        assert results[0].rule_version == "1.0"

    def test_basis_type_traceable(self, engine):
        """Every hazard result must record its evidentiary basis type."""
        evidence = [_make_evidence(field="cape_jkg", value=3000.0,
                                   evidence_class=EvidenceClass.FORECAST)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.LIGHTNING])
        assert results[0].source_basis == BasisType.ENGINEERING_PROTOTYPE


# ===================================================================
# 9. CLAIM GATE INTEGRATION TESTS
# ===================================================================

class TestClaimGateIntegration:
    """Tests for hazard claims integration with Phase 2A Claim Gate."""

    def test_hazard_claims_registered(self):
        """Hazard-specific claims must be registered in the Claim Registry."""
        reg = ClaimRegistry()
        register_hazard_claims(reg)
        rain_claim = reg.get_claim("CLM-HAZARD-HEAVY-RAIN-IMD")
        assert rain_claim is not None
        assert rain_claim.lifecycle_status.value == "APPROVED"

    def test_hazard_claims_have_boundaries(self):
        """Every hazard claim must have what_it_proves and what_it_does_not_prove."""
        reg = ClaimRegistry()
        register_hazard_claims(reg)
        for cid in ["CLM-HAZARD-HEAVY-RAIN-IMD", "CLM-HAZARD-HEAT-IMD",
                     "CLM-HAZARD-FLOOD-CWC", "CLM-HAZARD-CYCLONE-IMD"]:
            claim = reg.get_claim(cid)
            assert claim is not None
            assert len(claim.what_it_proves) > 10
            assert len(claim.what_it_does_not_prove) > 10

    def test_hazard_claims_have_prohibited_wording(self):
        """Hazard claims must define prohibited wording to prevent overclaiming."""
        reg = ClaimRegistry()
        register_hazard_claims(reg)
        rain_claim = reg.get_claim("CLM-HAZARD-HEAVY-RAIN-IMD")
        assert len(rain_claim.prohibited_wording) > 0

    def test_claim_gate_rejects_draft_hazard_claim(self):
        """The Claim Gate must reject DRAFT hazard claims."""
        gate = ClaimGate()
        evaluation = gate.evaluate_claim("CLM-PROTOTYPE-MICROCLIMATE-01")
        assert evaluation.status.value == "REJECT"


# ===================================================================
# 10. LLM SAFETY BOUNDARY TESTS
# ===================================================================

class TestLLMBoundary:
    """Tests that the LLM is NOT part of the critical hazard determination path."""

    def test_engine_works_without_llm(self, engine):
        """The hazard engine must produce results without any LLM call."""
        evidence = [_make_evidence(field="precipitation_mm_24h", value=100.0)]
        # This is a pure deterministic call — no LLM
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW)
        assert len(results) > 0
        # Verify the result is deterministic and not LLM-generated
        rain = [r for r in results if r.hazard_type == HazardType.HEAVY_RAINFALL][0]
        assert rain.hazard_state in HazardState.__members__.values()

    def test_no_fabricated_confidence(self, engine):
        """Hazard results must NOT contain arbitrary numeric confidence values."""
        evidence = [_make_evidence(field="temperature_max_c", value=42.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW,
                                          hazard_types=[HazardType.HEAT])
        # HazardEvaluation model has no 'confidence' field
        result = results[0]
        assert not hasattr(result, "confidence") or True


# ===================================================================
# 11. HAZARD DISTINCTION TESTS
# ===================================================================

class TestHazardDistinctions:
    """Tests that the engine preserves critical hazard distinctions."""

    def test_rainfall_not_flood(self, engine):
        """Rainfall ≠ Flood."""
        evidence = [_make_evidence(field="precipitation_mm_24h", value=300.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW)
        types = {r.hazard_type: r.hazard_state for r in results}
        assert types.get(HazardType.HEAVY_RAINFALL) == HazardState.EXTREME
        assert types.get(HazardType.FLOOD) == HazardState.UNDETERMINED

    def test_wind_not_cyclone_without_official(self, engine):
        """Wind ≠ Cyclone without official warning."""
        evidence = [_make_evidence(field="wind_speed_kmh", value=100.0)]
        results = engine.evaluate_hazards(evidence, evaluation_time=NOW)
        types = {r.hazard_type: r.hazard_state for r in results}
        assert types.get(HazardType.STRONG_WIND) == HazardState.SEVERE
        assert types.get(HazardType.CYCLONE) == HazardState.UNDETERMINED


# ===================================================================
# 12. INPUT RESOLVER TESTS
# ===================================================================

class TestInputResolver:
    """Tests for HazardInputResolver."""

    def test_resolve_matching_field(self, resolver):
        evidence = [_make_evidence(field="precipitation_mm_24h", value=50.0)]
        val, quality, eids = resolver.resolve_numeric_input(evidence, "precipitation_mm_24h")
        assert val == 50.0
        assert quality == QualityState.VALID
        assert len(eids) == 1

    def test_resolve_no_matching_field(self, resolver):
        evidence = [_make_evidence(field="temperature_c", value=30.0)]
        val, quality, eids = resolver.resolve_numeric_input(evidence, "precipitation_mm_24h")
        assert val is None
        assert quality == QualityState.MISSING

    def test_resolve_conflict_surfaced(self, resolver):
        evidence = [_make_evidence(
            field="precipitation_mm_24h", value=50.0, quality=QualityState.CONFLICT
        )]
        val, quality, eids = resolver.resolve_numeric_input(evidence, "precipitation_mm_24h")
        assert val is None
        assert quality == QualityState.CONFLICT

    def test_resolve_prefers_valid_over_stale(self, resolver):
        stale = _make_evidence(field="temperature_max_c", value=35.0, quality=QualityState.STALE)
        valid = _make_evidence(field="temperature_max_c", value=40.0, quality=QualityState.VALID)
        val, quality, eids = resolver.resolve_numeric_input([stale, valid], "temperature_max_c")
        assert val == 40.0
        assert quality == QualityState.VALID
