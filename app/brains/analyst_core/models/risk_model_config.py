"""Versioned risk model configuration and methodology metadata."""

from typing import Dict
from pydantic import BaseModel, Field


class RiskModelConfig(BaseModel):
    """Configurable, versioned parameters for composite risk and confidence calculation."""
    config_version: str = "RISK-WMO-2024.1"
    model_id: str = "RM-MCDA-2024"
    hazard_weight_with_exposure: float = 0.50
    exposure_weight: float = 0.25
    vulnerability_weight: float = 0.25
    hazard_weight_unspecified: float = 1.0
    methodology: str = "Multi-Criteria Decision Analysis (MCDA) Impact-Based Risk Model"
    assumption_status: str = "EVIDENCE_CONSTRAINED"
    confidence_weight_data_quality: float = 0.40
    confidence_weight_model_agreement: float = 0.35
    confidence_weight_lead_time: float = 0.25
    authority_citation: str = (
        "WMO Guidelines on Multi-hazard Impact-based Forecast and Warning Services (WMO-No. 1150)"
    )
    effective_date: str = "2024-01-01"


class RiskModelRegistry:
    """Registry maintaining active and historical risk model configuration versions."""
    REGISTRY: Dict[str, RiskModelConfig] = {
        "RISK-WMO-2024.1": RiskModelConfig(
            config_version="RISK-WMO-2024.1",
            model_id="RM-MCDA-2024",
            hazard_weight_with_exposure=0.50,
            exposure_weight=0.25,
            vulnerability_weight=0.25,
            hazard_weight_unspecified=1.0,
            methodology="Multi-Criteria Decision Analysis (MCDA) Impact-Based Risk Model",
            assumption_status="EVIDENCE_CONSTRAINED",
            authority_citation="WMO Guidelines on Multi-hazard Impact-based Forecast and Warning Services (WMO-No. 1150)",
            effective_date="2024-01-01",
        ),
        "RISK-CONSERVATIVE-2024": RiskModelConfig(
            config_version="RISK-CONSERVATIVE-2024",
            model_id="RM-CONSERVATIVE-2024",
            hazard_weight_with_exposure=0.60,
            exposure_weight=0.20,
            vulnerability_weight=0.20,
            hazard_weight_unspecified=1.0,
            methodology="Conservative High-Impact Precautionary Risk Framework",
            assumption_status="CONSERVATIVE_UPPER_BOUND",
            authority_citation="NDMA National Disaster Management Guidelines",
            effective_date="2024-01-01",
        ),
    }

    @classmethod
    def get_config(cls, version: str = "RISK-WMO-2024.1") -> RiskModelConfig:
        """Retrieves an immutable risk model configuration by version tag."""
        if version not in cls.REGISTRY:
            return cls.REGISTRY["RISK-WMO-2024.1"]
        return cls.REGISTRY[version]
