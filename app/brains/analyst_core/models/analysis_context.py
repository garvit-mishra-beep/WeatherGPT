"""AnalysisContext: Unified analytical pipeline execution state and audit trail."""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.brains.analyst_core.models.schemas import Persona, PipelineState, HazardType
from app.brains.analyst_core.models.weather_data import LocationMetadata
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState
from app.brains.analyst_core.models.analyst_result import EvidenceItem, DecisionSupport
from app.brains.analyst_core.models.risk_model import RiskScore
from app.brains.analyst_core.models.retrieval import DataRetrievalResult


class AnalysisContext(BaseModel):
    """Unified runtime context and state machine passed through the intelligence pipeline."""
    query_id: str = Field(default_factory=lambda: f"QRY-{uuid.uuid4().hex[:12]}")
    session_id: str = Field(default_factory=lambda: f"SES-{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_persona: Persona = Persona.ANALYST
    language: str = "en"
    location_name: Optional[str] = None
    location_metadata: Optional[LocationMetadata] = None
    target_time_window: str = "current"
    config_version: str = "IMD-MET-2024.1"
    risk_config_version: str = "RISK-WMO-2024.1"
    pipeline_state: PipelineState = PipelineState.INITIALIZED
    execution_trace: List[str] = Field(default_factory=list)
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)
    retrieval_reports: List[DataRetrievalResult] = Field(default_factory=list)

    # Core Pipeline Analytical Artifacts
    canonical_state: Optional[CanonicalWeatherState] = None
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    active_hazards: List[HazardType] = Field(default_factory=list)
    risk_score: Optional[RiskScore] = None
    decision_support: Optional[DecisionSupport] = None
    reproducibility_hash: Optional[str] = None

    def record_step(self, step_name: str, details: str = "") -> None:
        """Records pipeline execution checkpoint with high-precision timestamp."""
        ts = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{ts}] {step_name}"
        if details:
            entry += f": {details}"
        self.execution_trace.append(entry)

    def transition_to(self, new_state: PipelineState, details: str = "") -> None:
        """Transitions the pipeline state machine to a new state and logs the transition."""
        prev = self.pipeline_state
        self.pipeline_state = new_state
        self.record_step(f"STATE_TRANSITION ({prev.value} -> {new_state.value})", details)

    def compute_reproducibility_hash(self) -> str:
        """Computes a deterministic cryptographic SHA-256 digest of the entire analytical pipeline execution."""
        digest_dict = {
            "query_id": self.query_id,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location_name,
            "config_version": self.config_version,
            "risk_config_version": self.risk_config_version,
            "active_hazards": [h.value for h in self.active_hazards],
            "risk_level": self.risk_score.level.value if self.risk_score else "NONE",
            "decision_outcome": self.decision_support.outcome.value if self.decision_support else "NONE",
            "evidence_count": len(self.evidence_items),
        }
        raw_json = json.dumps(digest_dict, sort_keys=True)
        self.reproducibility_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        return self.reproducibility_hash
