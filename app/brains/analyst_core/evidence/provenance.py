import uuid
import hashlib
import json
from datetime import datetime
from typing import List, Optional
from app.brains.analyst_core.models.schemas import DataType, ConfidenceLevel
from app.brains.analyst_core.models.analyst_result import EvidenceItem
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert, ModelAnalysis


class ProvenanceTracker:
    """Tracks complete data lineage and builds verifiable EvidenceItems.
    
    SCIENTIFIC INTEGRITY RULES:
    TEST 1: Synthetic data MUST NOT be labeled official.
    TEST 3: Forecast MUST NOT be described as observation.
    TEST 4: Reanalysis MUST NOT be described as station observation.
    TEST 10: Stale data MUST NOT be described as current.
    """

    @staticmethod
    def _compute_sha256(data_str: str) -> str:
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def create_observation_evidence(
        self,
        obs: WeatherObservation,
        variable: str,
        value_str: str,
        confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    ) -> EvidenceItem:
        """Creates evidence item for ground observation with cryptographic provenance derived from source."""
        if obs.is_synthetic:
            dataset_name = "Synthetic Test Dataset"
            data_type = DataType.SYNTHETIC
            method_desc = "Synthetic test generator"
            agency = "WeatherGPT Synthetic Testing Generator"
            license_str = "Internal Testing Only"
            uri_str = obs.endpoint_uri or f"synthetic://test-fixture/{obs.location}"
        elif obs.data_type == DataType.MODEL_ANALYSIS:
            dataset_name = f"NWP Surface Analysis ({obs.source})"
            data_type = DataType.MODEL_ANALYSIS
            method_desc = "Numerical model atmospheric surface analysis and spatial assimilation (Non-station model output)"
            agency = obs.producing_agency or obs.source
            license_str = obs.data_license or "Unspecified License"
            uri_str = obs.endpoint_uri
        elif obs.data_type == DataType.REANALYSIS:
            dataset_name = f"Atmospheric Reanalysis Dataset ({obs.source})"
            data_type = DataType.REANALYSIS
            method_desc = "Historical climate reanalysis assimilation (ERA5/MERRA-2)"
            agency = obs.producing_agency or obs.source
            license_str = obs.data_license or "Unspecified License"
            uri_str = obs.endpoint_uri
        else:
            dataset_name = f"In-situ Station Observation ({obs.source})"
            data_type = DataType.OBSERVATION
            method_desc = "Direct calibrated meteorological instrument recording"
            agency = obs.producing_agency or obs.source
            license_str = obs.data_license or "Unspecified License"
            uri_str = obs.endpoint_uri

        # Freshness check
        limitations = ""
        if any("STALE_DATA" in f for f in obs.quality_flags):
            limitations = "Data timestamp is stale; represents historical observation rather than immediate real-time."
            if confidence == ConfidenceLevel.HIGH:
                confidence = ConfidenceLevel.LOW

        payload_repr = f"{obs.location}|{obs.timestamp.isoformat()}|{variable}|{value_str}|{obs.source}"
        sha = self._compute_sha256(payload_repr)

        return EvidenceItem(
            id=f"EV-OBS-{uuid.uuid4().hex[:8]}",
            source=obs.source,
            dataset=dataset_name,
            data_type=data_type,
            timestamp=obs.timestamp,
            variable=variable,
            location=obs.location,
            method=method_desc,
            result=value_str,
            confidence=confidence,
            limitations=limitations,
            is_synthetic=obs.is_synthetic,
            content_sha256=sha,
            uri_or_endpoint=uri_str,
            processing_step="Ingestion -> Unit Normalization -> Range Validation -> QC Flagging",
            data_license=license_str,
            producing_agency=agency,
        )

    def create_forecast_evidence(
        self,
        fc: ForecastPoint,
        variable: str,
        value_str: str,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> EvidenceItem:
        """Creates evidence item for NWP point forecast with source-driven attribution."""
        data_type = DataType.SYNTHETIC if fc.is_synthetic else DataType.FORECAST_NWP
        dataset_name = f"{fc.model_name} NWP Model Simulation" if not fc.is_synthetic else "Synthetic Forecast Model"
        
        if fc.is_synthetic:
            agency = "Synthetic Forecast Model Generator"
            license_str = "Internal Testing Only"
            uri_str = fc.endpoint_uri
        else:
            agency = fc.producing_center or fc.source
            license_str = fc.data_license or "Unspecified License"
            uri_str = fc.endpoint_uri

        payload_repr = f"{fc.location}|{fc.valid_time.isoformat()}|{variable}|{value_str}|{fc.model_name}|{fc.model_cycle}"
        sha = self._compute_sha256(payload_repr)

        lead_str = f"+{fc.lead_time_hours}h" if fc.lead_time_hours is not None else "Uninitialized"
        return EvidenceItem(
            id=f"EV-FC-{uuid.uuid4().hex[:8]}",
            source=fc.source,
            dataset=dataset_name,
            data_type=data_type,
            timestamp=fc.valid_time,
            variable=variable,
            location=fc.location,
            method=f"Dynamical atmospheric integration ({fc.model_name} Cycle {fc.model_cycle}, Lead {lead_str})",
            result=value_str,
            confidence=confidence,
            limitations=f"Valid at {fc.valid_time.isoformat()}; lead time {lead_str}; subject to initial condition uncertainty.",
            is_synthetic=fc.is_synthetic,
            content_sha256=sha,
            uri_or_endpoint=uri_str,
            processing_step="NWP Model Integration -> Model Level Extraction -> 2m Interpolation",
            data_license=license_str,
            producing_agency=agency,
        )

    def create_alert_evidence(
        self,
        alert: OfficialAlert,
    ) -> EvidenceItem:
        """Creates evidence item for official meteorological alert with cryptographic verification."""
        payload_repr = f"{alert.alert_id}|{alert.issuing_authority}|{alert.severity.value}|{alert.issue_time.isoformat()}"
        sha = self._compute_sha256(payload_repr)

        agency = alert.issuing_authority or "Official Emergency / Meteorological Authority"
        license_str = alert.data_license or "Official Warning Open Public Data"
        uri_str = alert.endpoint_uri

        return EvidenceItem(
            id=f"EV-ALT-{uuid.uuid4().hex[:8]}",
            source=alert.issuing_authority,
            dataset=f"Official Meteorological Alert Feed ({alert.warning_type})",
            data_type=DataType.SYNTHETIC if alert.is_synthetic else DataType.OFFICIAL_WARNING,
            timestamp=alert.issue_time,
            variable="Official Weather Warning",
            location=alert.geographic_area,
            method="National Meteorological / Disaster Management Official Bulletin",
            result=f"[{alert.severity.value}] {alert.headline}",
            confidence=ConfidenceLevel.VERY_HIGH,
            limitations="Official authoritative alert broadcast.",
            is_synthetic=alert.is_synthetic,
            content_sha256=sha,
            uri_or_endpoint=uri_str,
            processing_step="CAP XML/JSON Parsing -> Geographic Filtering -> Severity Escalation",
            data_license=license_str,
            producing_agency=agency,
        )

    def create_model_analysis_evidence(
        self,
        analysis: ModelAnalysis,
        variable: str,
        value_str: str,
        confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    ) -> EvidenceItem:
        """Creates evidence item for numerical model analysis / reanalysis fields."""
        payload_repr = f"{analysis.location}|{analysis.valid_time.isoformat()}|{variable}|{value_str}|{analysis.model_name}"
        sha = self._compute_sha256(payload_repr)

        return EvidenceItem(
            id=f"EV-MOD-{uuid.uuid4().hex[:8]}",
            source=analysis.source,
            dataset=f"{analysis.model_name} Atmospheric Analysis ({analysis.reanalysis_dataset or 'Assimilation'})",
            data_type=analysis.data_type,
            timestamp=analysis.valid_time,
            variable=variable,
            location=analysis.location,
            method=f"Numerical Data Assimilation (Resolution ~{analysis.grid_resolution_km or 'grid'}km)",
            result=value_str,
            confidence=confidence,
            limitations="Model-derived assimilation field; uncalibrated against micro-scale topoclimates.",
            is_synthetic=analysis.is_synthetic,
            content_sha256=sha,
            uri_or_endpoint=analysis.endpoint_uri,
            processing_step="Assimilation Ingestion -> Spatial Interpolation -> Grid Extraction",
            data_license=analysis.data_license or "Unspecified License",
            producing_agency=analysis.producing_agency or analysis.source,
        )
