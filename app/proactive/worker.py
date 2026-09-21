"""Durable Outbox Delivery Worker for Phase 9 Push Notifications.

Processes pending outbox dispatches asynchronously:
- Enforces bounded retries with exponential backoff on transient errors.
- Dispatches notifications to registered active device tokens via FCM.
- Deactivates invalid or expired tokens upon FCM error (UNREGISTERED/INVALID_ARGUMENT).
- Suppresses expired events whose valid_until operational horizon has elapsed.
- Ensures delivery idempotency across events and device targets.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.db.models.outbox import ProactiveNotificationOutbox, UserDeviceToken
from app.db.repositories.device import DeviceTokenRepository
from app.db.repositories.outbox import OutboxRepository
from app.proactive.fcm import FCMMessage, FCMProvider, FCMResult, mask_token

logger = logging.getLogger(__name__)


class OutboxDeliveryWorker:
    """Asynchronous worker pulling pending entries from PostgreSQL outbox and delivering via FCM."""

    def __init__(
        self,
        outbox_repo: OutboxRepository,
        device_repo: DeviceTokenRepository,
        fcm_provider: FCMProvider,
        max_retries: int = 3,
        batch_size: int = 50,
        base_backoff_seconds: float = 2.0,
    ):
        self.outbox_repo = outbox_repo
        self.device_repo = device_repo
        self.fcm_provider = fcm_provider
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.base_backoff_seconds = base_backoff_seconds

    async def process_batch(self) -> Dict[str, int]:
        """Executes a single processing cycle over pending outbox records."""
        stats = {
            "processed": 0,
            "delivered": 0,
            "retried": 0,
            "failed": 0,
            "expired": 0,
            "tokens_deactivated": 0,
        }

        pending_items = await self.outbox_repo.fetch_pending_batch(limit=self.batch_size)
        stats["processed"] = len(pending_items)

        now_utc = datetime.now(timezone.utc)

        for item in pending_items:
            # 1. Check for expiration
            if item.valid_until and item.valid_until.tzinfo is None:
                # Normalize timezone-naive datetime to UTC if needed
                item_valid_until = item.valid_until.replace(tzinfo=timezone.utc)
            else:
                item_valid_until = item.valid_until

            if item_valid_until and item_valid_until < now_utc:
                logger.info("OutboxWorker: Event %s expired (valid_until=%s). Suppressing push.", item.event_id, item_valid_until)
                await self.outbox_repo.mark_expired(item.outbox_id)
                stats["expired"] += 1
                continue

            # 2. Check retry bounds
            if item.attempt_count >= self.max_retries:
                logger.warning("OutboxWorker: Item %s exceeded max retries (%d). Marking FAILED.", item.outbox_id, self.max_retries)
                await self.outbox_repo.mark_failed(item.outbox_id, error_info=f"Exceeded maximum retries ({self.max_retries})")
                stats["failed"] += 1
                continue

            # 3. Retrieve recipient's active device tokens
            devices = await self.device_repo.get_active_tokens_for_user(item.user_id)
            if not devices:
                logger.info("OutboxWorker: No active push tokens for user %s. Marking delivered to local outbox.", item.user_id)
                await self.outbox_repo.mark_delivered(item.outbox_id)
                stats["delivered"] += 1
                continue

            # 4. Dispatch to all active registered devices
            delivered_any = False
            has_transient_failure = False
            last_error_msg = None

            for dev in devices:
                msg = FCMMessage(
                    token=dev.fcm_token,
                    title=item.title,
                    body=item.body,
                    data={
                        "event_id": str(item.event_id),
                        "severity": str(item.severity),
                        "event_type": str(item.event_type),
                        "operation": str(item.payload.get("operation") or ""),
                        "verdict": str(item.payload.get("verdict") or ""),
                        "plot_id": str(item.plot_id or ""),
                        "outbox_id": str(item.outbox_id),
                    },
                    priority="high" if item.severity.lower() in ("critical", "high") else "normal",
                )

                res: FCMResult = await self.fcm_provider.send_message(msg)

                if res.success:
                    delivered_any = True
                    logger.info("OutboxWorker: Delivered event %s to device %s", item.event_id, dev.device_id)
                elif res.is_token_invalid:
                    logger.warning("OutboxWorker: Invalid token encountered for device %s. Deactivating token.", dev.device_id)
                    await self.device_repo.deactivate_token(dev.fcm_token)
                    stats["tokens_deactivated"] += 1
                    last_error_msg = f"{res.error_code or 'INVALID_TOKEN'}: {res.error_message or 'Token invalid'}"
                elif res.is_transient:
                    has_transient_failure = True
                    last_error_msg = f"{res.error_code or 'TRANSIENT_ERROR'}: {res.error_message or 'Transient push network failure'}"
                else:
                    last_error_msg = f"{res.error_code or 'PERMANENT_ERROR'}: {res.error_message or 'Permanent push delivery failure'}"

            # 5. Evaluate final status for this outbox item
            if delivered_any:
                await self.outbox_repo.mark_delivered(item.outbox_id)
                stats["delivered"] += 1
            elif has_transient_failure:
                await self.outbox_repo.record_attempt(item.outbox_id, error_info=last_error_msg)
                stats["retried"] += 1
            else:
                # All attempts failed permanently or all tokens were deactivated
                await self.outbox_repo.mark_failed(item.outbox_id, error_info=last_error_msg or "All device targets failed permanently")
                stats["failed"] += 1

        return stats
