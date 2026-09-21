"""Governed Risk Method Registry for VAYUBODHAK Phase 6.

Maintains canonical metadata, formula specifications, lifecycle statuses,
threshold configurations, and scientific classifications for risk assessment methods.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.risk.models import (
    MethodClassification,
    RiskAggregationPolicy,
    RiskCategory,
    RiskMethodStatus,
    RiskScale,
)


class RiskMethodRecord(BaseModel):
    """Canonical registry entry for a quantitative risk assessment method."""
    method_id: str = Field(..., description="Unique immutable method identifier")
    method_name: str = Field(..., description="Human-readable title of the method")
    version: str = Field(default="1.0.0", description="Semantic version of method definition")
    status: RiskMethodStatus = Field(default=RiskMethodStatus.ACTIVE)
    classification: MethodClassification = Field(default=MethodClassification.VAYUBODHAK_PROTOTYPE)
    formula: str = Field(..., description="Mathematical representation of formula")
    scale: RiskScale = Field(..., description="Measurement scale output")
    description: str = Field(..., description="Comprehensive method overview")
    citation: str = Field(..., description="Scientific or institutional source reference")
    thresholds: Dict[str, float] = Field(
        default_factory=dict,
        description="Upper bounds for categorical mapping (e.g. LOW: 0.05, MODERATE: 0.20, HIGH: 0.50)",
    )
    aggregation_policy: RiskAggregationPolicy = Field(default=RiskAggregationPolicy.MULTIPLICATIVE)
    is_prototype: bool = Field(default=True)
    limitations: List[str] = Field(default_factory=list)


class RiskMethodRegistry:
    """Registry maintaining active, draft, and retired risk assessment methodologies."""

    def __init__(self) -> None:
        self._registry: Dict[str, RiskMethodRecord] = {}
        self._initialize_canonical_methods()

    def _initialize_canonical_methods(self) -> None:
        """Loads canonical VAYUBODHAK risk methods."""

        # 1. Primary Multiplicative Interaction Method
        self.register_method(
            RiskMethodRecord(
                method_id="RISK-METH-MULT-001",
                method_name="Multiplicative Dimensionless Interaction Risk Engine",
                version="1.0.0",
                status=RiskMethodStatus.ACTIVE,
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                formula="R_mult = H_norm * E_norm * V_norm",
                scale=RiskScale.INDEX_0_TO_1,
                description=(
                    "Deterministic VAYUBODHAK prototype risk index combining normalized, dimensionless "
                    "hazard, exposure, and vulnerability factors on [0.0, 1.0]. Satisfies physical "
                    "zero-boundary conditions (H=0, E=0, or V=0 yields R=0). "
                    "NOTE: UNDRR and IPCC frameworks describe disaster risk conceptually as resulting "
                    "from interactions among hazard, exposure, vulnerability, and capacity, but do NOT "
                    "prescribe this specific mathematical equation or mandate multiplication. "
                    "Capacity is not represented in this numerical index."
                ),
                citation=(
                    "Conceptual interaction framework: UNDRR Terminology (2017) & Sendai Framework (2015-2030). "
                    "Mathematical parameterization: VAYUBODHAK-PROTOTYPE engineering implementation."
                ),
                thresholds={
                    "LOW": 0.05,
                    "MODERATE": 0.20,
                    "HIGH": 0.50,
                    "CRITICAL": 1.00,
                },
                aggregation_policy=RiskAggregationPolicy.MULTIPLICATIVE,
                is_prototype=True,
                limitations=[
                    "Capacity (coping/adaptive capacity) is not represented in this numerical index",
                    "Does NOT represent an official UNDRR or IPCC mandated equation (VAYUBODHAK prototype)",
                    "Stale meteorological hazard inputs are rejected for real-time risk determination",
                    "Exposure normalization relies on engineering reference capacity constants (Q_ref)",
                    "Thresholds are prototype calibration cutoffs, not empirical fatality boundaries",
                    "Does not model monetary damages, casualties, or building collapse probabilities",
                    "Assumes spatial concordance of input component boundaries",
                ],
            )
        )

        # 2. Legacy Operational Additive Method (WeatherGPT Backward Compatibility)
        self.register_method(
            RiskMethodRecord(
                method_id="RISK-METH-ADD-001",
                method_name="Additive Operational Multi-Criteria Risk Index",
                version="1.0.0",
                status=RiskMethodStatus.ACTIVE,
                classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
                formula="R_add = (0.50 * H) + (0.30 * E) + (0.20 * V)",
                scale=RiskScale.INDEX_0_TO_10,
                description=(
                    "Linear weighted sum of operational hazard (0.50), exposure (0.30), "
                    "and vulnerability (0.20) indices on [0.0, 10.0]. Retained for backward "
                    "compatibility with legacy analytics and mobile dashboards."
                ),
                citation="VAYUBODHAK Analytics Engine Spec (docs/11_ANALYTICS_ENGINE.md §4.2)",
                thresholds={
                    "LOW": 3.5,
                    "MODERATE": 7.0,
                    "HIGH": 10.0,
                },
                aggregation_policy=RiskAggregationPolicy.ADDITIVE_WEIGHTED,
                is_prototype=True,
                limitations=[
                    "Violates zero-boundary conditions: yields positive risk (5.0) when E=0 and V=0",
                    "Fails to differentiate uninhabited areas from populated risk zones under extreme weather",
                    "Engineering heuristic index, not physical disaster risk",
                ],
            )
        )

        # 3. Draft Actuarial Copula Model
        self.register_method(
            RiskMethodRecord(
                method_id="RISK-METH-COPV-001",
                method_name="Actuarial Copula Loss Exceedance Model",
                version="0.1.0",
                status=RiskMethodStatus.DRAFT,
                classification=MethodClassification.UNRESOLVED,
                formula="P(L > l) = C(F_H(h), F_E(e), F_V(v))",
                scale=RiskScale.INDEX_0_TO_1,
                description="Draft copula loss exceedance model. Execution blocked pending empirical damage calibration.",
                citation="Catastrophe Modeling Research / CAPRA Guidelines",
                thresholds={},
                aggregation_policy=RiskAggregationPolicy.INDEPENDENT_PARALLEL,
                is_prototype=True,
                limitations=["Uncalibrated; requires multi-decadal empirical disaster loss tables"],
            )
        )

    def register_method(self, method: RiskMethodRecord) -> None:
        """Registers a new or updated risk method in the registry."""
        self._registry[method.method_id] = method

    def get_method(self, method_id: str) -> Optional[RiskMethodRecord]:
        """Retrieves a risk method by unique identifier."""
        return self._registry.get(method_id)

    def list_methods(self, status: Optional[RiskMethodStatus] = None) -> List[RiskMethodRecord]:
        """Lists registered risk methods, optionally filtered by status."""
        if status is None:
            return list(self._registry.values())
        return [m for m in self._registry.values() if m.status == status]


# Global singleton instance
risk_method_registry = RiskMethodRegistry()
