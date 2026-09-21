"""VAYUBODHAK Phase 3 — Deterministic Hazard Modeling Engine.

Provides evidence-first, deterministic hazard evaluation on top of
the Phase 2A Evidence Foundation. No LLM involvement in the critical
hazard determination path.

Public API:
    HazardEngine          — Core orchestrator
    HazardRuleRegistry    — Versioned rule catalog
    CompoundHazardEvaluator — Evidence-backed compound hazards
    hazard_router         — FastAPI router
"""

from app.hazard.models import (
    BasisType,
    CompoundHazardEvaluation,
    HazardEvaluation,
    HazardRule,
    HazardRuleStatus,
    HazardState,
    HazardType,
)
from app.hazard.rule_registry import HazardRuleRegistry, hazard_rule_registry
from app.hazard.engine import HazardEngine, hazard_engine
from app.hazard.compound import CompoundHazardEvaluator

__all__ = [
    "BasisType",
    "CompoundHazardEvaluation",
    "CompoundHazardEvaluator",
    "HazardEngine",
    "HazardEvaluation",
    "HazardRule",
    "HazardRuleRegistry",
    "HazardRuleStatus",
    "HazardState",
    "HazardType",
    "hazard_engine",
    "hazard_rule_registry",
]
