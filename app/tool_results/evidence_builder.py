"""Evidence Package builder aggregating normalized tool results for LLM grounding."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.contracts.enums import WarningLevel
from app.contracts.evidence import (
    EvidencePackage,
    OfficialAlertItem,
    ProvenanceItem,
)
from app.contracts.location import LocationContext
from app.tool_results.errors import EvidenceAssemblyError
from app.tool_results.models import NormalizedToolResult


class EvidenceBuilder:
    """Assembles multiple NormalizedToolResults into a validated EvidencePackage."""

    @staticmethod
    def build_evidence_package(
        results: List[NormalizedToolResult],
        location: LocationContext,
        temporal_context: Dict[str, Any],
        evidence_id: Optional[str] = None,
    ) -> EvidencePackage:
        """Constructs an EvidencePackage ensuring provenance and warning preservation.

        Args:
            results: List of verified NormalizedToolResults.
            location: The resolved LocationContext for the query.
            temporal_context: Temporal metadata (reference_time, forecast_window).
            evidence_id: Optional custom tracing ID.

        Returns:
            EvidencePackage: Grounded evidence envelope.

        Raises:
            EvidenceAssemblyError: If required location or temporal metadata is invalid.
        """
        if not isinstance(location, LocationContext):
            raise EvidenceAssemblyError("LocationContext must be a valid instance.")

        generated_at = datetime.now(timezone.utc).isoformat()
        ev_id = evidence_id or f"ev_{uuid.uuid4().hex[:8]}"

        official_alerts: List[OfficialAlertItem] = []
        provenance_items: List[ProvenanceItem] = []
        tool_results_dict: Dict[str, Any] = {}
        limitations: List[str] = []

        for res in results:
            # 1. Map tool data
            if res.tool_name in tool_results_dict:
                # If tool was called multiple times, store as list
                existing = tool_results_dict[res.tool_name]
                if isinstance(existing, list):
                    existing.append(res.data)
                else:
                    tool_results_dict[res.tool_name] = [existing, res.data]
            else:
                tool_results_dict[res.tool_name] = res.data

            # 2. Extract official warnings/alerts if present (preserving severity)
            if "alerts" in res.data and isinstance(res.data["alerts"], list):
                for alert_dict in res.data["alerts"]:
                    try:
                        raw_color = str(alert_dict.get("warning_color", "Yellow")).title()
                        warning_lvl = (
                            WarningLevel(raw_color)
                            if raw_color in WarningLevel._value2member_map_
                            else WarningLevel.YELLOW
                        )
                        alert_item = OfficialAlertItem(
                            source=alert_dict.get("source", "IMD"),
                            warning_level=warning_lvl,
                            hazard=alert_dict.get("hazard_type", "Meteorological Hazard"),
                            headline=alert_dict.get("headline"),
                            description=alert_dict.get("description", "Official weather warning."),
                            valid_from=alert_dict.get("valid_from"),
                            valid_until=alert_dict.get("valid_until", generated_at),
                            issuing_office=alert_dict.get("issuing_office"),
                        )
                        official_alerts.append(alert_item)
                    except Exception:
                        pass

            # 3. Map provenance
            if res.provenance:
                for src in res.provenance.data_sources:
                    is_official = "IMD" in src or "NDMA" in src
                    provenance_items.append(
                        ProvenanceItem(
                            authority="IMD" if is_official else None,
                            dataset=src,
                            retrieved_at=res.provenance.retrieval_timestamp,
                            is_official=is_official,
                            methodology=res.tool_name,
                        )
                    )

            # 4. Collect limitations
            limitations.extend(res.limitations)

        return EvidencePackage(
            evidence_id=ev_id,
            generated_at=generated_at,
            location=location,
            temporal_context=temporal_context,
            official_alerts=official_alerts,
            tool_results=tool_results_dict,
            provenance=provenance_items,
            limitations=limitations,
        )
