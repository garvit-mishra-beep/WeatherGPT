# VAYUBODHAK — PHASE 8 RBAC SECURITY MATRIX

## Decision Verification Endpoint Authorization & Security Matrix

**Target Endpoint:** `POST /api/v1/decision/verify`  
**Governing Security Principle:** Reviewer authorization is derived from the authenticated cryptographic identity and trusted authorization data. Client-controlled role headers (`X-Reviewer-Role`), request body fields (`role`, `verifier_id`), and query parameters (`?role=...`) cannot elevate privileges or determine authorization.

---

### Threat Model & Defense Matrix

| Attack / Condition | Test Scenario | Threat Vector | Server Enforcement Mechanism | Expected Result | Verified in Suite |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Missing Token** | Scenario 9 | Anonymous unauthenticated client attempting verification | FastAPI `HTTPBearer(auto_error=False)` rejects missing Authorization header. | **401 Unauthorized** (Missing authentication credentials) | `test_missing_jwt_rejected` |
| **Invalid Token** | Scenario 7 | Malformed token / gibberish bearer string | `jwt.decode` catches `InvalidTokenError` and raises 401. | **401 Unauthorized** (Invalid authentication token) | `test_forged_jwt_signature_rejected` |
| **Expired Token** | Scenario 8 | Client submits previously valid token past `exp` claim | `jwt.decode` catches `ExpiredSignatureError` and raises 401. | **401 Unauthorized** (Authentication token has expired) | `test_expired_jwt_rejected` |
| **Forged JWT Signature** | Scenario 7 | Attacker signs claims with incorrect secret key | Cryptographic signature verification fails with HMAC-SHA256. | **401 Unauthorized** (Invalid token signature) | `test_forged_jwt_signature_rejected` |
| **PUBLIC_USER + Reviewer Header** | Scenario 1 | Authenticated non-officer sends `X-Reviewer-Role: INCIDENT_COMMANDER` | Header is treated as untrusted metadata; RBAC checks trusted identity claims (`PUBLIC_USER` has no `DECISION_VERIFY`). | **403 Forbidden** (Role 'PUBLIC_USER' lacks DECISION_VERIFY permission) | `test_public_user_cannot_escalate_via_reviewer_role_header` |
| **PUBLIC_USER + Body Role** | Scenario 2 | Attacker includes `{"role": "INCIDENT_COMMANDER"}` in JSON payload | `DecisionVerificationRequest` ignores extra fields; identity extracted strictly from bearer token. | **403 Forbidden** | `test_public_user_cannot_escalate_via_body_role` |
| **PUBLIC_USER + Query Role** | Scenario 3 | Attacker appends `?role=INCIDENT_COMMANDER` to URL query string | Query params ignored for authorization; dependency inspects authenticated principal only. | **403 Forbidden** | `test_public_user_cannot_escalate_via_query_role` |
| **Authorized Verifier** | Scenario 4 | Verifier with trusted role (`FIELD_INSPECTOR`, `DUTY_OFFICER`, etc.) | JWT signature and expiration verified; role possesses `DECISION_VERIFY` permission. Verification persisted. | **200 OK** (Status: VERIFIED, verifier_id bound to subject) | `test_authorized_reviewer_from_trusted_identity_can_verify` |
| **Unknown Role** | Scenario 10 | Valid token with unrecognized role claim (e.g., `SUPER_ADMIN_CUSTOM`) | Server checks role against governed `ReviewerRole` enum. Unknown role rejected. | **403 Forbidden** (Unknown or unauthorized role) | `test_unknown_role_rejected` |
| **Header Conflict (Downgrade/Mismatch)** | Scenario 5 | Authorized user (`FIELD_INSPECTOR`) with `X-Reviewer-Role: PUBLIC_USER` | Authorization decisions follow trusted identity token; client cannot downgrade or corrupt server authorization. | **200 OK** (Trusted identity role executed) | `test_header_conflict_trusted_identity_wins` |
| **Role Swap (Escalation & Downgrade)** | Scenario 6 | Bidirectional role swap test (`PUBLIC_USER` + header vs `FIELD_INSPECTOR` + header) | Cryptographic identity is strictly authoritative in both directions. | **403 / 200** according to JWT | `test_role_swap_header_cannot_alter_authorization` |
| **Valid Role + Malicious Header** | Scenario 14 | Authorized `INCIDENT_COMMANDER` sends `X-Reviewer-Role: HACKER` | Malicious header is discarded/ignored; trusted principal permissions apply. | **200 OK** (Incident commander authorized) | `test_authorized_role_with_malicious_header_trusted_identity_prevails` |
| **Identity Spoofing (Impersonation)** | Scenario 12 | User A attempts to set `verifier_id = "user_b"` in verification body | Endpoint overrides/ignores request verifier ID; database persists `authenticated_principal.subject`. | **200 OK** with `verifier_id == token.sub` (impersonation negated) | `test_verifier_identity_bound_to_authenticated_subject` |
| **Authority Spoofing Payload** | Scenario 13 | Malicious payload with `authority`, `is_official: true`, `role`, `verifier_reference` | Server strictly relies on authenticated identity; unauthorized caller receives 403; zero records persisted. | **403 Forbidden** (Zero persistence) | `test_authority_spoofing_payload_blocked` |
| **Role Change / Revocation** | Scenario 11 | User role changed server-side from `PUBLIC_USER` to `FIELD_INSPECTOR` | Old token remains bound to old claims; verification requires token renewal with new role. | **403 then 200 upon token renewal** | `test_role_change_requires_new_token` |
| **Offline Unauthenticated Verification** | Scenario 9 / Architectural | Client disconnected or in degraded state with no valid token | No offline bypass backdoor. Verification endpoint strictly requires server cryptographic token validation. | **401 Unauthorized** (Offline bypass blocked) | Enforced by `require_decision_verifier` |

---

### Governed Verifier Role Hierarchy

```text
GOVERNED ROLES AND PERMISSIONS
-----------------------------------------------------------------------------------------
Role                          DECISION_READ    DECISION_VERIFY    Operational Authority
-----------------------------------------------------------------------------------------
FIELD_INSPECTOR                     [X]              [X]          On-ground verification
OPERATIONAL_ANALYST                 [X]              [X]          Impact & model verification
DISTRICT_DISASTER_OFFICER           [X]              [X]          Administrative verification
DUTY_OFFICER                        [X]              [X]          Emergency ops verification
INCIDENT_COMMANDER                  [X]              [X]          Full operational authority
SCIENTIFIC_REVIEWER                 [X]              [X]          Meteorological / model check
PUBLIC_USER                         [X]              [ ]          Read-only, no verification
GUEST                               [X]              [ ]          Read-only, no verification
-----------------------------------------------------------------------------------------
```
