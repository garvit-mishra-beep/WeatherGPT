"""Dedicated Security Test Suite for VAYUBODHAK Phase 8 — RBAC Identity & Role Binding.

Verifies:
1. Public user cannot escalate privileges via X-Reviewer-Role header (403 Forbidden).
2. Public user cannot escalate privileges via body role fields (403 Forbidden).
3. Public user cannot escalate privileges via query parameters (403 Forbidden).
4. Authorized reviewer from trusted identity can verify (200 OK, verifier_id bound to subject).
5. Header conflict (trusted identity wins; client cannot alter authorization).
6. Role swap (JWT dictates authorization in both directions).
7. Forged JWT signature rejected (401 Unauthorized).
8. Expired JWT rejected (401 Unauthorized).
9. Missing JWT rejected (401 Unauthorized).
10. Unknown role rejected (403 Forbidden).
11. Role change reflects through token renewal.
12. Verifier identity bound to authenticated subject (impersonation rejected).
13. Authority spoofing payload blocked.
14. Authorized role with malicious header (trusted identity prevails).
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.repositories.decision import decision_repository
from app.decision.auth import ReviewerRole, create_reviewer_token
from app.decision.models import (
    ConfidenceLevel,
    DecisionContext,
    DecisionOutcome,
    DecisionPackage,
    DecisionState,
    NirnayCard,
    SeverityLevel,
)
from app.core.rate_limit import default_rate_limiter
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter windows to prevent 429 during bulk test suite runs."""
    default_rate_limiter.reset()
    if hasattr(app.state, "rate_limiter") and app.state.rate_limiter is not None:
        app.state.rate_limiter.reset()
    yield
    default_rate_limiter.reset()
    if hasattr(app.state, "rate_limiter") and app.state.rate_limiter is not None:
        app.state.rate_limiter.reset()


@pytest.fixture
def sample_decision():
    """Seeds a persistent decision package in the repository for verification testing."""
    dec_id = f"DEC-SEC-{uuid.uuid4().hex[:8].upper()}"
    now_iso = "2026-09-21T10:00:00Z"
    ctx = DecisionContext(
        decision_id=dec_id,
        version=1,
        assessment_time_iso=now_iso,
        decision_status=DecisionState.PREPARE,
        hazard_type="CYCLONE",
        hazard_state="SEVERE",
        geography="Puri",
        provenance_id="hash_sec_test_01",
    )
    card = NirnayCard(
        question="Security verification check",
        verdict=DecisionOutcome.PROCEED_WITH_CAUTION,
        severity=SeverityLevel.HIGH,
        recommended_action="Prepare flood defenses",
        confidence=ConfidenceLevel.HIGH,
        uncertainty={"detail": "Operational testing"},
        why=["High wind speed detected"],
    )
    pkg = DecisionPackage(
        decision_id=dec_id,
        timestamp_iso=now_iso,
        decision=ctx,
        nirnay_card=card,
        provenance={"provenance_id": "hash_sec_test_01"},
    )
    from app.decision.router import _DECISION_STORE
    _DECISION_STORE[dec_id] = pkg
    return pkg


# ============================================================================
# Security Test Scenarios
# ============================================================================

def test_public_user_cannot_escalate_via_reviewer_role_header(sample_decision):
    """Scenario 1: Authenticated PUBLIC_USER cannot promote self to INCIDENT_COMMANDER via header."""
    public_token = create_reviewer_token(subject="user_civilian_01", role=ReviewerRole.PUBLIC_USER.value)
    
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verification_status": "VERIFIED",
            "verification_note": "Attempted escalation via header",
        },
        headers={
            "Authorization": f"Bearer {public_token}",
            "X-Reviewer-Role": "INCIDENT_COMMANDER",
        },
    )
    assert resp.status_code == 403
    assert "Authorization denied" in resp.json()["detail"]


def test_public_user_cannot_escalate_via_body_role(sample_decision):
    """Scenario 2: Authenticated PUBLIC_USER cannot promote self via request body fields."""
    public_token = create_reviewer_token(subject="user_civilian_02", role=ReviewerRole.PUBLIC_USER.value)
    
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verification_status": "VERIFIED",
            "role": "INCIDENT_COMMANDER",
            "reviewer_role": "DISTRICT_DISASTER_OFFICER",
            "verification_note": "Attempted escalation via body",
        },
        headers={"Authorization": f"Bearer {public_token}"},
    )
    assert resp.status_code == 403
    assert "Authorization denied" in resp.json()["detail"]


def test_public_user_cannot_escalate_via_query_role(sample_decision):
    """Scenario 3: Authenticated PUBLIC_USER cannot promote self via query parameter."""
    public_token = create_reviewer_token(subject="user_civilian_03", role=ReviewerRole.PUBLIC_USER.value)
    
    resp = client.post(
        f"/api/v1/decision/verify?role=INCIDENT_COMMANDER",
        json={
            "decision_id": sample_decision.decision_id,
            "verification_status": "VERIFIED",
            "verification_note": "Attempted escalation via query param",
        },
        headers={"Authorization": f"Bearer {public_token}"},
    )
    assert resp.status_code == 403
    assert "Authorization denied" in resp.json()["detail"]


def test_authorized_reviewer_from_trusted_identity_can_verify(sample_decision):
    """Scenario 4: Authorized FIELD_INSPECTOR verified through JWT successfully records verification."""
    token = create_reviewer_token(subject="INSP-9921", role=ReviewerRole.FIELD_INSPECTOR.value)
    
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verification_status": "VERIFIED",
            "verification_note": "Culvert inspected on-site; water flowing normally.",
            "verifier_reference": "Field Inspection Unit 4",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision_id"] == sample_decision.decision_id
    assert data["verification_status"] == "VERIFIED"
    assert data["verifier_id"] == "INSP-9921"
    assert data["verifier_role"] == "FIELD_INSPECTOR"
    assert data["verifier_reference"] == "Field Inspection Unit 4"


def test_header_conflict_trusted_identity_wins(sample_decision):
    """Scenario 5: JWT role FIELD_INSPECTOR with header X-Reviewer-Role: PUBLIC_USER succeeds based on JWT."""
    token = create_reviewer_token(subject="INSP-7712", role=ReviewerRole.FIELD_INSPECTOR.value)
    
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verification_status": "VERIFIED",
            "verification_note": "Verified with conflicting client header",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Reviewer-Role": "PUBLIC_USER",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["verifier_id"] == "INSP-7712"
    assert resp.json()["verifier_role"] == "FIELD_INSPECTOR"


def test_role_swap_header_cannot_alter_authorization(sample_decision):
    """Scenario 6: Role swap test: JWT dictates authorization in both directions."""
    # Part A: JWT PUBLIC_USER, Header FIELD_INSPECTOR -> 403 Forbidden
    pub_token = create_reviewer_token(subject="user_fake", role=ReviewerRole.PUBLIC_USER.value)
    resp_a = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {pub_token}", "X-Reviewer-Role": "FIELD_INSPECTOR"},
    )
    assert resp_a.status_code == 403

    # Part B: JWT FIELD_INSPECTOR, Header PUBLIC_USER -> 200 OK
    auth_token = create_reviewer_token(subject="user_real", role=ReviewerRole.FIELD_INSPECTOR.value)
    resp_b = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {auth_token}", "X-Reviewer-Role": "PUBLIC_USER"},
    )
    assert resp_b.status_code == 200


def test_forged_jwt_signature_rejected(sample_decision):
    """Scenario 7: Token signed with untrusted secret key is rejected with 401 Unauthorized."""
    forged_token = create_reviewer_token(
        subject="attacker_01",
        role=ReviewerRole.INCIDENT_COMMANDER.value,
        secret_key="wrong_hacker_secret_key_that_does_not_match",
    )
    resp = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert resp.status_code == 401
    assert "signature is invalid or forged" in resp.json()["detail"].lower()


def test_expired_jwt_rejected(sample_decision):
    """Scenario 8: Expired token is rejected with 401 Unauthorized."""
    expired_token = create_reviewer_token(
        subject="officer_past",
        role=ReviewerRole.DUTY_OFFICER.value,
        expires_in_seconds=-100,  # expired 100 seconds ago
    )
    resp = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
    assert "token is expired" in resp.json()["detail"].lower()


def test_missing_jwt_rejected(sample_decision):
    """Scenario 9: Missing Authorization header is rejected with 401 Unauthorized."""
    resp = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
    )
    assert resp.status_code == 401
    assert "missing authorization header" in resp.json()["detail"].lower()


def test_unknown_role_rejected(sample_decision):
    """Scenario 10: Authenticated token with unknown or unmapped role is rejected with 403 Forbidden."""
    token = create_reviewer_token(subject="user_unknown", role="ARBITRARY_HACKER_ROLE")
    resp = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Authorization denied" in resp.json()["detail"]


def test_role_change_requires_new_token(sample_decision):
    """Scenario 11: Role promotion takes effect upon obtaining a refreshed token reflecting the new role."""
    # User originally has PUBLIC_USER token -> 403
    t1 = create_reviewer_token(subject="officer_promoted", role=ReviewerRole.PUBLIC_USER.value)
    resp1 = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp1.status_code == 403

    # Server updates role to DISTRICT_DISASTER_OFFICER, new token issued -> 200
    t2 = create_reviewer_token(subject="officer_promoted", role=ReviewerRole.DISTRICT_DISASTER_OFFICER.value)
    resp2 = client.post(
        "/api/v1/decision/verify",
        json={"decision_id": sample_decision.decision_id, "verification_status": "VERIFIED"},
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["verifier_role"] == "DISTRICT_DISASTER_OFFICER"


def test_verifier_identity_bound_to_authenticated_subject(sample_decision):
    """Scenario 12: Request body cannot impersonate another verifier; stored verifier_id equals JWT sub."""
    token = create_reviewer_token(subject="REAL_INSPECTOR_42", role=ReviewerRole.FIELD_INSPECTOR.value)
    
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verifier_id": "IMPERSONATED_DISTRICT_COLLECTOR",
            "verification_status": "VERIFIED",
            "verification_note": "Attempted impersonation in body",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    record = resp.json()
    # The authoritative verifier_id MUST be the authenticated subject, not the client-provided string
    assert record["verifier_id"] == "REAL_INSPECTOR_42"
    assert record["verifier_id"] != "IMPERSONATED_DISTRICT_COLLECTOR"


def test_authority_spoofing_payload_blocked(sample_decision):
    """Scenario 13: Malicious payload claiming statutory credentials is blocked."""
    # If sent by an unprivileged user -> 403 at authorization gate
    pub_token = create_reviewer_token(subject="unauth_user", role=ReviewerRole.PUBLIC_USER.value)
    resp_pub = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "authority": "DISTRICT_DISASTER_OFFICER",
            "is_official": True,
            "role": "INCIDENT_COMMANDER",
            "verifier_reference": "OFFICIAL_GOVT_CHIEF_SECRETARY",
            "verification_status": "VERIFIED",
        },
        headers={"Authorization": f"Bearer {pub_token}"},
    )
    assert resp_pub.status_code == 403

    # If sent by an authorized role trying to claim official government statutory reference -> 403
    auth_token = create_reviewer_token(subject="ins_01", role=ReviewerRole.FIELD_INSPECTOR.value)
    resp_spoof = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verifier_reference": "OFFICIAL_GOVT_DISASTER_CHIEF",
            "verification_status": "VERIFIED",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp_spoof.status_code == 403
    assert "statutory authority credentials" in resp_spoof.json()["detail"].lower()


def test_authorized_role_with_malicious_header_trusted_identity_prevails(sample_decision):
    """Scenario 14: Authorized INCIDENT_COMMANDER with garbage or injection header succeeds using trusted role."""
    token = create_reviewer_token(subject="CMD-001", role=ReviewerRole.INCIDENT_COMMANDER.value)
    
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": sample_decision.decision_id,
            "verification_status": "ESCALATED",
            "verification_note": "Immediate resource staging commanded",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Reviewer-Role": "' OR 1=1; DROP TABLE decision_verifications; --",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["verifier_id"] == "CMD-001"
    assert resp.json()["verifier_role"] == "INCIDENT_COMMANDER"
