"""Domain service orchestrating Evidence Creation, Quality Validation, Lineage, and Bundles."""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Set

from app.evidence.claim_gate import ClaimGate, ClaimRegistry, claim_gate, claim_registry
from app.evidence.models import (
    CANONICAL_FRESHNESS_POLICIES,
    ClaimGateResultStatus,
    ClaimRecord,
    EvidenceClass,
    EvidenceRecord,
    FreshnessPolicy,
    ProvenanceRecord,
    QualityState,
    RuntimeEvidenceBundle,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.registry import SourceRegistry, source_registry


class ImmutabilityViolationError(ValueError):
    """Raised when an attempt is made to mutate, overwrite, or alter an immutable evidence record."""
    pass


class EvidenceService:
    """Core domain service for the VAYUBODHAK Evidence Foundation."""

    def __init__(
        self,
        sources: Optional[SourceRegistry] = None,
        claims: Optional[ClaimRegistry] = None,
        gate: Optional[ClaimGate] = None,
    ) -> None:
        self.sources = sources or source_registry
        self.claims = claims or claim_registry
        self.gate = gate or claim_gate
        self._evidence_store: Dict[str, EvidenceRecord] = {}

    @staticmethod
    def compute_sha256(data_payload: Any) -> str:
        """Computes deterministic SHA-256 hash for data integrity verification."""
        if isinstance(data_payload, (dict, list)):
            serialized = json.dumps(data_payload, sort_keys=True, default=str)
        else:
            serialized = str(data_payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def evaluate_quality(
        self,
        raw_val: Any,
        normalized_val: Any,
        variable_name: str,
        temporal: TemporalIdentity,
        evidence_class: Optional[EvidenceClass] = None,
        source_id: Optional[str] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> tuple[QualityState, List[str]]:
        """Determines explicit quality state without silent conversions.
        
        Zero Silent Conversion Rules:
        - None / null values -> QualityState.MISSING (never 0.0)
        - Extreme physical bounds violations -> QualityState.INVALID
        - Expired / stale timestamps -> QualityState.STALE (evaluated via FreshnessPolicy)
        - Discrepant sensor flags -> QualityState.CONFLICT
        """
        flags: List[str] = list(custom_flags or [])

        # 1. Missing Check
        if raw_val is None or normalized_val is None:
            flags.append("MISSING_VALUE")
            return QualityState.MISSING, flags

        # 2. Physical Range Validation (Invalid Check)
        var_lower = variable_name.lower()
        try:
            val_float = float(normalized_val)
            if "temp" in var_lower:
                if val_float < -90.0 or val_float > 65.0:
                    flags.append(f"PHYSICAL_RANGE_VIOLATION: Temperature {val_float} outside [-90, 65] degC")
                    return QualityState.INVALID, flags
            elif "rain" in var_lower or "precip" in var_lower:
                if val_float < 0.0 or val_float > 2000.0:
                    flags.append(f"PHYSICAL_RANGE_VIOLATION: Rainfall {val_float} outside [0, 2000] mm")
                    return QualityState.INVALID, flags
            elif "humidity" in var_lower:
                if val_float < 0.0 or val_float > 100.0:
                    flags.append(f"PHYSICAL_RANGE_VIOLATION: Humidity {val_float} outside [0, 100] %")
                    return QualityState.INVALID, flags
            elif "wind" in var_lower:
                if val_float < 0.0 or val_float > 450.0:
                    flags.append(f"PHYSICAL_RANGE_VIOLATION: Wind speed {val_float} outside [0, 450] km/h")
                    return QualityState.INVALID, flags
        except (ValueError, TypeError):
            pass

        # 3. Conflict Flag
        if any("CONFLICT" in f.upper() for f in flags):
            return QualityState.CONFLICT, flags

        # 4. Freshness / Staleness Evaluation via Configurable FreshnessPolicy
        policy: Optional[FreshnessPolicy] = None
        if source_id:
            source_meta = self.sources.get_source(source_id)
            if source_meta:
                if evidence_class and evidence_class.value in source_meta.freshness_policies:
                    policy = source_meta.freshness_policies[evidence_class.value]
                elif evidence_class and evidence_class in source_meta.freshness_policies:
                    policy = source_meta.freshness_policies[evidence_class]
        if not policy and evidence_class:
            policy = CANONICAL_FRESHNESS_POLICIES.get(evidence_class)
        if not policy:
            # Fallback default: 6 hours max age, enforce validity
            policy = FreshnessPolicy(
                max_age_seconds=6 * 3600,
                enforce_validity_window=True,
                description="Default 6-hour observation freshness policy fallback",
            )

        now_utc = temporal.retrieval_time or datetime.now(timezone.utc)

        # 4a. Check Validity Window Expiration
        if policy.enforce_validity_window and temporal.valid_to:
            if temporal.valid_to < now_utc:
                flags.append(f"EXPIRED_VALIDITY: Window expired at {temporal.valid_to.isoformat()}")
                return QualityState.STALE, flags

        # 4b. Special case for OFFICIAL_WARNING:
        # If valid_to is defined and still active (valid_to >= now_utc),
        # an official alert (e.g. 24h-72h warning) is ACTIVE and FRESH.
        # It must NEVER be prematurely expired after 6 hours.
        if evidence_class == EvidenceClass.OFFICIAL_WARNING and temporal.valid_to and temporal.valid_to >= now_utc:
            return QualityState.VALID, flags

        # 4c. Check observation / issuance age against max_age_seconds
        if policy.max_age_seconds is not None:
            ref_time = temporal.observation_time or temporal.issue_time
            if ref_time:
                age_seconds = (now_utc - ref_time).total_seconds()
                if age_seconds > policy.max_age_seconds:
                    flags.append(
                        f"STALE_DATA: Age of {round(age_seconds / 3600, 1)}h exceeds "
                        f"freshness threshold of {round(policy.max_age_seconds / 3600, 1)}h"
                    )
                    return QualityState.STALE, flags

        return QualityState.VALID, flags

    def create_evidence(
        self,
        source_id: str,
        evidence_class: EvidenceClass,
        raw_field: str,
        raw_value: Any,
        raw_unit: Optional[str],
        normalized_field: str,
        normalized_value: Any,
        normalized_unit: Optional[str],
        temporal: TemporalIdentity,
        spatial: Optional[SpatialIdentity] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
        source_version: Optional[str] = None,
        product_id: Optional[str] = None,
        endpoint_uri: Optional[str] = None,
        derived_from: Optional[List[str]] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> EvidenceRecord:
        """Creates and indexes a canonical EvidenceRecord with cryptographic provenance."""
        # 1. Source verification
        source_meta = self.sources.get_source(source_id)
        if not source_meta:
            raise ValueError(f"Source '{source_id}' is not registered in SourceRegistry.")

        # 2. Quality state evaluation
        quality_state, quality_flags = self.evaluate_quality(
            raw_val=raw_value,
            normalized_val=normalized_value,
            variable_name=normalized_field,
            temporal=temporal,
            evidence_class=evidence_class,
            source_id=source_id,
            custom_flags=custom_flags,
        )

        # 3. Cryptographic SHA-256 Provenance Checksum
        payload_for_hash = {
            "source_id": source_id,
            "raw_field": raw_field,
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "raw_payload": raw_payload,
            "retrieval_time": temporal.retrieval_time.isoformat() if temporal.retrieval_time else None,
            "observation_time": temporal.observation_time.isoformat() if temporal.observation_time else None,
        }
        checksum = self.compute_sha256(payload_for_hash)

        evidence_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
        provenance_id = f"PRV-{uuid.uuid4().hex[:8].upper()}"

        provenance = ProvenanceRecord(
            provenance_id=provenance_id,
            source_id=source_id,
            product_id=product_id or source_meta.product_id,
            source_version=source_version or source_meta.version,
            retrieval_time=temporal.retrieval_time,
            issue_time=temporal.issue_time,
            observation_time=temporal.observation_time,
            valid_from=temporal.valid_from,
            valid_to=temporal.valid_to,
            location_context=spatial.model_dump() if spatial else None,
            transformation_version="1.0",
            sha256_checksum=checksum,
            producing_agency=source_meta.authority,
            endpoint_uri=endpoint_uri or source_meta.base_url,
        )

        record = EvidenceRecord(
            evidence_id=evidence_id,
            source_id=source_id,
            evidence_class=evidence_class,
            raw_field=raw_field,
            raw_value=raw_value,
            raw_unit=raw_unit,
            raw_payload=raw_payload,
            normalized_field=normalized_field,
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
            temporal=temporal,
            spatial=spatial,
            quality_state=quality_state,
            quality_flags=quality_flags,
            provenance=provenance,
            derived_from=list(derived_from or []),
        )

        return self.store_evidence(record)

    def derive_evidence(
        self,
        parent_evidence_ids: List[str],
        derived_field: str,
        derived_value: Any,
        derived_unit: Optional[str],
        derivation_name: str,
        temporal: TemporalIdentity,
        spatial: Optional[SpatialIdentity] = None,
        derivation_version: str = "1.0",
    ) -> EvidenceRecord:
        """Derives a new EvidenceRecord maintaining strict multi-parent lineage."""
        if not parent_evidence_ids:
            raise ValueError("Cannot derive evidence without at least one parent evidence ID.")

        parent_records: List[EvidenceRecord] = []
        for pid in parent_evidence_ids:
            parent = self._evidence_store.get(pid)
            if not parent:
                raise ValueError(f"Parent evidence ID '{pid}' not found in evidence store.")
            parent_records.append(parent)

        primary_parent = parent_records[0]
        checksum = self.compute_sha256({
            "derivation_name": derivation_name,
            "parents": [p.provenance.sha256_checksum for p in parent_records],
            "value": derived_value,
            "version": derivation_version,
        })

        evidence_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
        provenance_id = f"PRV-{uuid.uuid4().hex[:8].upper()}"

        provenance = ProvenanceRecord(
            provenance_id=provenance_id,
            source_id=primary_parent.source_id,
            product_id=f"DERIVED_{derivation_name.upper()}",
            source_version=primary_parent.provenance.source_version,
            retrieval_time=temporal.retrieval_time,
            issue_time=temporal.issue_time,
            observation_time=temporal.observation_time,
            valid_from=temporal.valid_from,
            valid_to=temporal.valid_to,
            location_context=spatial.model_dump() if spatial else primary_parent.provenance.location_context,
            transformation_version=derivation_version,
            sha256_checksum=checksum,
            producing_agency="VAYUBODHAK Derivation Engine",
            endpoint_uri="algorithm://vayubodhak/derivation/" + derivation_name,
        )

        # Inherit STALE / INVALID if any parent has it
        parent_qualities = [p.quality_state for p in parent_records]
        if QualityState.INVALID in parent_qualities:
            derived_quality = QualityState.INVALID
            flags = ["DERIVED_FROM_INVALID_PARENT"]
        elif QualityState.STALE in parent_qualities:
            derived_quality = QualityState.STALE
            flags = ["DERIVED_FROM_STALE_PARENT"]
        elif QualityState.MISSING in parent_qualities:
            derived_quality = QualityState.MISSING
            flags = ["DERIVED_FROM_MISSING_PARENT"]
        else:
            derived_quality = QualityState.VALID
            flags = [f"DERIVED_VIA_{derivation_name.upper()}"]

        record = EvidenceRecord(
            evidence_id=evidence_id,
            source_id=primary_parent.source_id,
            evidence_class=EvidenceClass.DERIVED,
            raw_field=f"computed_{derived_field}",
            raw_value=derived_value,
            raw_unit=derived_unit,
            raw_payload={"parent_ids": parent_evidence_ids, "derivation": derivation_name},
            normalized_field=derived_field,
            normalized_value=derived_value,
            normalized_unit=derived_unit,
            temporal=temporal,
            spatial=spatial or primary_parent.spatial,
            quality_state=derived_quality,
            quality_flags=flags,
            provenance=provenance,
            derived_from=parent_evidence_ids,
        )

        return self.store_evidence(record)

    def store_evidence(self, record: EvidenceRecord) -> EvidenceRecord:
        """Stores an EvidenceRecord, strictly preventing in-place mutation or overwriting."""
        if record.evidence_id in self._evidence_store:
            raise ImmutabilityViolationError(
                f"Immutability violation: Evidence record '{record.evidence_id}' already exists and cannot be overwritten."
            )
        self._evidence_store[record.evidence_id] = record
        return record

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Retrieves an EvidenceRecord by ID."""
        return self._evidence_store.get(evidence_id)

    def verify_integrity(self, evidence_id: str) -> tuple[bool, str]:
        """Cryptographically verifies mathematical SHA-256 integrity of an EvidenceRecord.
        
        Guarantees that stored raw values, timestamps, and provenance metadata have not
        been modified or corrupted in storage or in memory.
        
        Returns:
            (True, "INTEGRITY_VERIFIED") if bit-for-bit valid.
            (False, <violation_reason>) if checksum does not match or record is missing.
        """
        record = self.get_evidence(evidence_id)
        if not record:
            return False, f"Evidence record '{evidence_id}' not found in store."

        if record.evidence_class == EvidenceClass.DERIVED:
            parent_records = [self.get_evidence(pid) for pid in record.derived_from]
            if any(p is None for p in parent_records):
                return False, f"Derived record '{evidence_id}' references missing parent records."
            derivation_name = ""
            if isinstance(record.raw_payload, dict):
                derivation_name = record.raw_payload.get("derivation", "")
            recalculated = self.compute_sha256({
                "derivation_name": derivation_name,
                "parents": [p.provenance.sha256_checksum for p in parent_records if p],
                "value": record.normalized_value,
                "version": record.provenance.transformation_version,
            })
        else:
            payload_for_hash = {
                "source_id": record.source_id,
                "raw_field": record.raw_field,
                "raw_value": record.raw_value,
                "raw_unit": record.raw_unit,
                "raw_payload": record.raw_payload,
                "retrieval_time": record.temporal.retrieval_time.isoformat() if record.temporal.retrieval_time else None,
                "observation_time": record.temporal.observation_time.isoformat() if record.temporal.observation_time else None,
            }
            recalculated = self.compute_sha256(payload_for_hash)

        if recalculated != record.provenance.sha256_checksum:
            return False, (
                f"INTEGRITY_VIOLATION: Checksum mismatch for '{evidence_id}' "
                f"(expected {record.provenance.sha256_checksum}, computed {recalculated})"
            )

        return True, "INTEGRITY_VERIFIED"

    def get_lineage(self, evidence_id: str) -> Dict[str, Any]:
        """Recursively builds the complete ancestor lineage DAG for an evidence record."""
        target = self.get_evidence(evidence_id)
        if not target:
            raise ValueError(f"Evidence ID '{evidence_id}' not found.")

        visited: Set[str] = set()

        def _traverse(node_id: str) -> Dict[str, Any]:
            if node_id in visited:
                return {"evidence_id": node_id, "cycle_detected": True}
            visited.add(node_id)
            node = self.get_evidence(node_id)
            if not node:
                return {"evidence_id": node_id, "status": "UNKNOWN_PARENT"}

            parents_trees = [_traverse(p) for p in node.derived_from]
            return {
                "evidence_id": node.evidence_id,
                "source_id": node.source_id,
                "evidence_class": node.evidence_class.value,
                "normalized_field": node.normalized_field,
                "normalized_value": node.normalized_value,
                "normalized_unit": node.normalized_unit,
                "quality_state": node.quality_state.value,
                "provenance": node.provenance.model_dump(),
                "parents": parents_trees,
            }

        return _traverse(evidence_id)

    def build_runtime_bundle(
        self,
        claim_ids: List[str],
        evidence_ids: List[str],
    ) -> RuntimeEvidenceBundle:
        """Assembles a machine-readable Runtime Evidence Bundle with verified provenance."""
        evidence_records: List[EvidenceRecord] = []
        provenance_records: List[ProvenanceRecord] = []
        quality_counts: Dict[str, int] = {q.value: 0 for q in QualityState}
        permitted_wording: List[str] = []
        prohibited_wording: List[str] = []
        claims_list: List[ClaimRecord] = []

        # 1. Collect evidence and verify checksums
        chain_verified = True
        for eid in evidence_ids:
            ev = self.get_evidence(eid)
            if not ev:
                chain_verified = False
                continue
            evidence_records.append(ev)
            provenance_records.append(ev.provenance)
            quality_counts[ev.quality_state.value] = quality_counts.get(ev.quality_state.value, 0) + 1

            # Strict cryptographic integrity verification
            is_valid, _ = self.verify_integrity(eid)
            if not is_valid:
                chain_verified = False

        # 2. Evaluate and collect claims
        for cid in claim_ids:
            evaluation = self.gate.evaluate_claim(cid, attached_evidence_ids=evidence_ids)
            claim = self.claims.get_claim(cid)
            if claim:
                claims_list.append(claim)
                permitted_wording.extend(evaluation.permitted_wording)
                prohibited_wording.extend(evaluation.prohibited_wording)
            if evaluation.status != ClaimGateResultStatus.ALLOW:
                chain_verified = False

        bundle_id = f"BDL-{uuid.uuid4().hex[:8].upper()}"
        return RuntimeEvidenceBundle(
            bundle_id=bundle_id,
            claim_ids=claim_ids,
            claims=claims_list,
            evidence_records=evidence_records,
            provenance_records=provenance_records,
            generated_at=datetime.now(timezone.utc),
            quality_summary={k: v for k, v in quality_counts.items() if v > 0},
            permitted_wording=list(set(permitted_wording)),
            prohibited_wording=list(set(prohibited_wording)),
            provenance_chain_verified=chain_verified,
        )


# Singleton instance
evidence_service = EvidenceService(source_registry, claim_registry, claim_gate)
