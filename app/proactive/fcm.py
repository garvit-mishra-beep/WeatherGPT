"""Firebase Cloud Messaging (FCM) HTTP v1 Provider Abstraction (Phase 9).

Provides:
- FCMMessage & FCMResult data contracts.
- FCMProvider abstract base class.
- HTTPv1FCMProvider with OAuth2 token caching, bounded timeouts, token masking,
  and comprehensive transient vs permanent error classification.
- MockFCMProvider for deterministic offline unit testing.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def mask_token(token: str) -> str:
    """Masks sensitive FCM tokens for secure logging (e.g. 'eK9j...3x9z')."""
    if not token or len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


class FCMMessage(BaseModel):
    """Normalized FCM notification and data payload adhering to FCM v1 specifications."""
    token: str = Field(..., description="Target device registration token")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body / recommended action")
    data: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value data payload (all values must be strings)",
    )
    priority: str = Field(
        default="high",
        description="FCM Android message priority ('high' or 'normal')",
    )


class FCMResult(BaseModel):
    """Result of an FCM delivery attempt with explicit failure classification."""
    success: bool
    message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    is_transient: bool = False
    is_token_invalid: bool = False


class FCMProvider(ABC):
    """Abstract interface for FCM push notification transport."""

    @abstractmethod
    async def send_message(self, message: FCMMessage) -> FCMResult:
        """Dispatches a single message to a registered device token."""
        pass

    async def send_multicast(self, messages: List[FCMMessage]) -> List[FCMResult]:
        """Dispatches multiple messages sequentially or concurrently."""
        results: List[FCMResult] = []
        for msg in messages:
            res = await self.send_message(msg)
            results.append(res)
        return results


class HTTPv1FCMProvider(FCMProvider):
    """Production FCM provider executing HTTP v1 REST requests to Google."""

    def __init__(
        self,
        project_id: str,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ):
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.timeout_seconds = timeout_seconds
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_access_token(self) -> Optional[str]:
        """Loads and caches an OAuth2 Bearer token from the service account."""
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests

            scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
            credentials = None

            if self.credentials_json:
                cred_dict = json.loads(self.credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    cred_dict, scopes=scopes
                )
            elif self.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=scopes
                )

            if not credentials:
                return None

            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            return credentials.token
        except Exception as exc:
            logger.error("HTTPv1FCMProvider: Failed to acquire OAuth2 token: %s", exc)
            return None

    async def send_message(self, message: FCMMessage) -> FCMResult:
        """Sends an FCM v1 HTTP message to Google's push servers."""
        token = self._get_access_token()
        if not token:
            return FCMResult(
                success=False,
                error_code="CREDENTIALS_UNAVAILABLE",
                error_message="FCM service account credentials missing or invalid.",
                is_transient=False,
                is_token_invalid=False,
            )

        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; UTF-8",
        }

        # Build FCM v1 payload
        # Ensure all data values are strings
        sanitized_data = {str(k): str(v) for k, v in message.data.items()}

        payload = {
            "message": {
                "token": message.token,
                "notification": {
                    "title": message.title,
                    "body": message.body,
                },
                "data": sanitized_data,
                "android": {
                    "priority": message.priority,
                    "notification": {
                        "channel_id": "weathergpt_proactive_decisions",
                        "sound": "default",
                    },
                },
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

                if resp.status_code == 200:
                    msg_id = resp_json.get("name", "projects/.../messages/ok")
                    logger.info("FCM: Successfully sent message to %s (id: %s)", mask_token(message.token), msg_id)
                    return FCMResult(success=True, message_id=msg_id)

                status_code = resp.status_code
                error_body = resp_json.get("error", {})
                error_code = error_body.get("status", str(status_code))
                error_msg = error_body.get("message", resp.text)

                # Classify errors
                is_token_invalid = (
                    status_code == 404
                    or "UNREGISTERED" in error_msg
                    or "INVALID_ARGUMENT" in error_msg
                    or "NOT_FOUND" in error_code
                )
                is_transient = (
                    status_code in (429, 500, 503)
                    or "UNAVAILABLE" in error_code
                    or "QUOTA_EXCEEDED" in error_code
                )

                logger.warning(
                    "FCM: Delivery failed for %s with status %d: %s (token_invalid=%s, transient=%s)",
                    mask_token(message.token),
                    status_code,
                    error_msg,
                    is_token_invalid,
                    is_transient,
                )
                return FCMResult(
                    success=False,
                    error_code=error_code,
                    error_message=error_msg,
                    is_transient=is_transient,
                    is_token_invalid=is_token_invalid,
                )

        except (httpx.TimeoutException, httpx.NetworkError) as net_err:
            logger.warning("FCM: Network error contacting FCM for %s: %s", mask_token(message.token), net_err)
            return FCMResult(
                success=False,
                error_code="NETWORK_TIMEOUT",
                error_message=str(net_err),
                is_transient=True,
                is_token_invalid=False,
            )
        except Exception as exc:
            logger.exception("FCM: Unexpected error delivering message to %s: %s", mask_token(message.token), exc)
            return FCMResult(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=str(exc),
                is_transient=False,
                is_token_invalid=False,
            )


class MockFCMProvider(FCMProvider):
    """Deterministic mock provider for automated unit tests and offline staging."""

    def __init__(
        self,
        simulate_outcome: str = "success",
        invalid_tokens: Optional[List[str]] = None,
        transient_tokens: Optional[List[str]] = None,
    ):
        self.simulate_outcome = simulate_outcome
        self.invalid_tokens = set(invalid_tokens or [])
        self.transient_tokens = set(transient_tokens or [])
        self.sent_messages: List[FCMMessage] = []

    async def send_message(self, message: FCMMessage) -> FCMResult:
        self.sent_messages.append(message)

        if message.token in self.invalid_tokens or self.simulate_outcome == "invalid_token":
            return FCMResult(
                success=False,
                error_code="UNREGISTERED",
                error_message="Requested entity was not found (token unregistered).",
                is_transient=False,
                is_token_invalid=True,
            )

        if message.token in self.transient_tokens or self.simulate_outcome == "transient_error":
            return FCMResult(
                success=False,
                error_code="UNAVAILABLE",
                error_message="The service is currently unavailable. Retry later.",
                is_transient=True,
                is_token_invalid=False,
            )

        if self.simulate_outcome == "permanent_error":
            return FCMResult(
                success=False,
                error_code="SENDER_ID_MISMATCH",
                error_message="The authenticated sender ID does not match the registration token.",
                is_transient=False,
                is_token_invalid=False,
            )

        # Default success
        return FCMResult(
            success=True,
            message_id=f"projects/mock-test/messages/msg_{len(self.sent_messages)}",
        )

    def clear(self) -> None:
        self.sent_messages.clear()
