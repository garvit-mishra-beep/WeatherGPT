"""Repository for managing user device tokens for push notifications (Phase 9)."""

from datetime import datetime, timezone
import logging
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.outbox import UserDeviceToken
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DeviceTokenRepository(BaseRepository[UserDeviceToken]):
    """Async repository for user device push token registration and lifecycle."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=UserDeviceToken)

    async def register_or_update_token(
        self,
        user_id: str,
        device_id: str,
        fcm_token: str,
        platform: str = "android",
    ) -> UserDeviceToken:
        """Registers a new device token or updates an existing device registration."""
        stmt = select(UserDeviceToken).where(
            UserDeviceToken.device_id == device_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalars().first()

        now_utc = datetime.now(timezone.utc)
        if existing:
            existing.user_id = user_id
            existing.fcm_token = fcm_token
            existing.platform = platform
            existing.is_active = True
            existing.updated_at = now_utc
            await self.session.commit()
            await self.session.refresh(existing)
            logger.info("DeviceTokenRepository: Updated device %s for user %s", device_id, user_id)
            return existing

        # Create new device record
        token_record = UserDeviceToken(
            device_id=device_id,
            user_id=user_id,
            fcm_token=fcm_token,
            platform=platform,
            is_active=True,
            created_at=now_utc,
            updated_at=now_utc,
        )
        self.session.add(token_record)
        await self.session.commit()
        await self.session.refresh(token_record)
        logger.info("DeviceTokenRepository: Registered new device %s for user %s", device_id, user_id)
        return token_record

    async def get_active_tokens_for_user(self, user_id: str) -> List[UserDeviceToken]:
        """Retrieves all active registered device tokens for a given user."""
        stmt = (
            select(UserDeviceToken)
            .where(
                UserDeviceToken.user_id == user_id,
                UserDeviceToken.is_active == True,
            )
            .order_by(UserDeviceToken.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_token(self, fcm_token: str) -> bool:
        """Deactivates a token when FCM reports UNREGISTERED or INVALID_ARGUMENT."""
        stmt = (
            update(UserDeviceToken)
            .where(UserDeviceToken.fcm_token == fcm_token)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        logger.info("DeviceTokenRepository: Deactivated invalid token (affected rows: %s)", result.rowcount)
        return result.rowcount > 0

    async def deactivate_device(self, device_id: str) -> bool:
        """Deactivates a specific device registration."""
        stmt = (
            update(UserDeviceToken)
            .where(UserDeviceToken.device_id == device_id)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete_device(self, device_id: str) -> bool:
        """Permanently unregisters a device."""
        record = await self.get(device_id)
        if not record:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True
