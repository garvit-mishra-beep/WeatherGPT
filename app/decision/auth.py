"""VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.
Cryptographic Authentication & Role-Based Access Control (RBAC) Module.

Binds reviewer authorization strictly to the cryptographically verified identity.
Eliminates reliance on client-supplied headers, request body fields, or query parameters.
"""

from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import Header, HTTPException, status
import jwt
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Governed Roles & Decision Permissions
# ============================================================================

class ReviewerRole(str, Enum):
    """Governed operational reviewer roles."""
    FIELD_INSPECTOR = "FIELD_INSPECTOR"
    OPERATIONAL_ANALYST = "OPERATIONAL_ANALYST"
    DISTRICT_DISASTER_OFFICER = "DISTRICT_DISASTER_OFFICER"
    DUTY_OFFICER = "DUTY_OFFICER"
    INCIDENT_COMMANDER = "INCIDENT_COMMANDER"
    SCIENTIFIC_REVIEWER = "SCIENTIFIC_REVIEWER"
    # Unprivileged / Public roles
    PUBLIC_USER = "PUBLIC_USER"
    GUEST = "GUEST"


class DecisionPermission(str, Enum):
    """Granular permissions for operational decision actions."""
    DECISION_VERIFY = "DECISION_VERIFY"
    DECISION_READ = "DECISION_READ"


# Server-side mapping of roles to permissions
ROLE_PERMISSIONS: Dict[str, Set[DecisionPermission]] = {
    ReviewerRole.FIELD_INSPECTOR.value: {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    ReviewerRole.OPERATIONAL_ANALYST.value: {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    ReviewerRole.DISTRICT_DISASTER_OFFICER.value: {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    ReviewerRole.DUTY_OFFICER.value: {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    ReviewerRole.INCIDENT_COMMANDER.value: {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    ReviewerRole.SCIENTIFIC_REVIEWER.value: {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    
    # Standardized aliases for operational compatibility
    "DDMA_OFFICER": {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    "SDMA_OFFICER": {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    "DISASTER_MANAGER": {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    "MUNICIPAL_ENGINEER": {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    "VERIFIED_FIELD_INSPECTOR": {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    "ADMINISTRATOR": {DecisionPermission.DECISION_VERIFY, DecisionPermission.DECISION_READ},
    
    # Non-authorized roles
    ReviewerRole.PUBLIC_USER.value: {DecisionPermission.DECISION_READ},
    ReviewerRole.GUEST.value: {DecisionPermission.DECISION_READ},
}

AUTHORIZED_VERIFIER_ROLES: Set[str] = {
    r for r, perms in ROLE_PERMISSIONS.items() if DecisionPermission.DECISION_VERIFY in perms
}


# ============================================================================
# Authenticated Principal Model
# ============================================================================

class ReviewerPrincipal(BaseModel):
    """Cryptographically authenticated reviewer identity and resolved server-side permissions."""
    subject: str = Field(..., description="Authenticated user ID or sub claim from JWT")
    role: str = Field(..., description="Authoritative role extracted from verified JWT claims")
    permissions: Set[DecisionPermission] = Field(default_factory=set, description="Resolved server-side permissions")
    issuer: Optional[str] = None
    audience: Optional[str] = None
    claims: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)

    def has_permission(self, permission: DecisionPermission) -> bool:
        """Returns True if the authenticated principal holds the requested permission."""
        return permission in self.permissions


# ============================================================================
# Token Verification & Generation
# ============================================================================

def create_reviewer_token(
    subject: str,
    role: str = ReviewerRole.FIELD_INSPECTOR.value,
    expires_in_seconds: int = 3600,
    secret_key: Optional[str] = None,
    algorithm: str = "HS256",
    custom_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Creates a signed JWT access token with bound subject and role claims for testing or sessions."""
    key = secret_key or settings.secret_key
    now = time.time()
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now),
        "exp": int(now + expires_in_seconds),
    }
    if custom_claims:
        payload.update(custom_claims)
    return jwt.encode(payload, key, algorithm=algorithm)


def decode_and_verify_token(token: str, secret_key: Optional[str] = None) -> ReviewerPrincipal:
    """Cryptographically decodes and validates a JWT token.
    
    Enforces:
    - Signature verification using server secret key
    - Algorithm constraint (strictly HS256)
    - Expiration (exp claim)
    - Subject (sub claim) presence
    """
    key = secret_key or settings.secret_key
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Authentication failed: Reviewer token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Reviewer token is expired.",
        )
    except jwt.InvalidSignatureError:
        logger.warning("Authentication failed: Reviewer token signature is invalid or forged")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Reviewer token signature is invalid or forged.",
        )
    except jwt.PyJWTError as e:
        logger.warning("Authentication failed: Token decoding failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: Token could not be validated ({str(e)}).",
        )
    except Exception as e:
        logger.error("Unexpected error during token decoding: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Token validation encountered an unexpected error.",
        )

    sub = payload.get("sub")
    if not sub or not str(sub).strip():
        logger.warning("Authentication failed: Token missing valid 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Token missing valid subject identifier ('sub').",
        )

    role = payload.get("role", ReviewerRole.PUBLIC_USER.value)
    role_str = str(role).strip()

    # Resolve server-side permissions
    perms = ROLE_PERMISSIONS.get(role_str, set())

    return ReviewerPrincipal(
        subject=str(sub).strip(),
        role=role_str,
        permissions=perms,
        issuer=payload.get("iss"),
        audience=payload.get("aud"),
        claims=payload,
    )


# ============================================================================
# FastAPI Dependency
# ============================================================================

async def require_decision_verifier(
    authorization: Optional[str] = Header(default=None),
) -> ReviewerPrincipal:
    """FastAPI dependency enforcing valid Bearer authentication and DECISION_VERIFY permission.
    
    Derives authorization strictly from verified token claims.
    Rejects missing or invalid tokens with 401 Unauthorized.
    Rejects unauthorized or unknown roles with 403 Forbidden.
    """
    if authorization is None:
        logger.warning("Verification endpoint called without Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Missing Authorization header with Bearer token.",
        )

    if not authorization.startswith("Bearer "):
        logger.warning("Verification endpoint called with non-Bearer authorization scheme")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Invalid authorization scheme. Bearer token required.",
        )

    raw_token = authorization.split("Bearer ", 1)[1].strip()
    if not raw_token:
        logger.warning("Verification endpoint called with empty Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Empty Bearer token.",
        )

    principal = decode_and_verify_token(raw_token)

    if not principal.has_permission(DecisionPermission.DECISION_VERIFY):
        logger.warning(
            "RBAC Authorization denied: Subject '%s' with role '%s' lacks DECISION_VERIFY permission",
            principal.subject,
            principal.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization denied: Role '{principal.role}' lacks DECISION_VERIFY permission.",
        )

    return principal
