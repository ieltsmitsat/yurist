"""Service for managing system access, lawyers, groups, and admin privileges."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.system_access import SystemAccess

logger = logging.getLogger(__name__)


class AccessService:
    """Manages role-based access for multiple lawyers, notification groups, and admin users."""

    @classmethod
    async def get_active_lawyer_ids(cls, session: AsyncSession) -> set[int]:
        """Return all active lawyer Telegram IDs, including configured fallback."""
        stmt = select(SystemAccess.telegram_id).where(
            SystemAccess.role == "lawyer",
            SystemAccess.is_active.is_(True),
        )
        res = await session.execute(stmt)
        lawyer_ids = set(res.scalars().all())

        if settings.LAWYER_TELEGRAM_ID:
            lawyer_ids.add(settings.LAWYER_TELEGRAM_ID)

        return lawyer_ids

    @classmethod
    async def get_active_admin_ids(cls, session: AsyncSession) -> set[int]:
        """Return all active admin Telegram IDs, including configured fallback."""
        stmt = select(SystemAccess.telegram_id).where(
            SystemAccess.role == "admin",
            SystemAccess.is_active.is_(True),
        )
        res = await session.execute(stmt)
        admin_ids = set(res.scalars().all())

        if settings.ADMIN_TELEGRAM_IDS:
            for item in settings.ADMIN_TELEGRAM_IDS.split(","):
                clean = item.strip()
                if clean.lstrip("-").isdigit():
                    admin_ids.add(int(clean))

        return admin_ids

    @classmethod
    async def get_active_group_ids(cls, session: AsyncSession) -> list[int]:
        """Return all active notification group Telegram IDs, including configured fallback."""
        stmt = select(SystemAccess.telegram_id).where(
            SystemAccess.role == "group",
            SystemAccess.is_active.is_(True),
        )
        res = await session.execute(stmt)
        group_ids = list(res.scalars().all())

        if settings.ADMIN_GROUP_ID and settings.ADMIN_GROUP_ID not in group_ids:
            group_ids.append(settings.ADMIN_GROUP_ID)

        return group_ids

    @classmethod
    async def is_lawyer(cls, session: AsyncSession, telegram_id: int) -> bool:
        """Check if telegram_id belongs to an active lawyer."""
        lawyer_ids = await cls.get_active_lawyer_ids(session)
        return telegram_id in lawyer_ids

    @classmethod
    async def get_all(
        cls, session: AsyncSession, role: str | None = None
    ) -> list[SystemAccess]:
        """Fetch all system access records, optionally filtered by role."""
        stmt = select(SystemAccess).order_by(SystemAccess.id.asc())
        if role:
            stmt = stmt.where(SystemAccess.role == role)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_by_id(cls, session: AsyncSession, access_id: int) -> SystemAccess | None:
        """Fetch system access record by ID."""
        stmt = select(SystemAccess).where(SystemAccess.id == access_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_by_telegram_id(
        cls, session: AsyncSession, telegram_id: int
    ) -> SystemAccess | None:
        """Fetch system access record by Telegram ID."""
        stmt = select(SystemAccess).where(SystemAccess.telegram_id == telegram_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        telegram_id: int,
        name: str,
        role: str = "lawyer",
        description: str | None = None,
        is_active: bool = True,
    ) -> SystemAccess:
        """Create new system access record."""
        existing = await cls.get_by_telegram_id(session, telegram_id)
        if existing:
            raise ValueError(f"Telegram ID {telegram_id} allaqachon mavjud!")

        access = SystemAccess(
            telegram_id=telegram_id,
            role=role,
            name=name,
            description=description,
            is_active=is_active,
        )
        session.add(access)
        await session.commit()
        await session.refresh(access)

        # Synchronize lawyer status for existing user record
        if role == "lawyer" and is_active:
            from app.services.user_service import UserService

            await UserService.sync_lawyer_status(session, telegram_id, is_active_lawyer=True)

        logger.info(
            "Created system access record: ID=%d, TelegramID=%d, Role=%s, Name=%s",
            access.id,
            access.telegram_id,
            access.role,
            access.name,
        )
        return access

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        access_id: int,
        **fields: Any,
    ) -> SystemAccess | None:
        """Update system access record."""
        access = await cls.get_by_id(session, access_id)
        if not access:
            return None

        # If telegram_id is updated, ensure uniqueness
        if "telegram_id" in fields and fields["telegram_id"] != access.telegram_id:
            existing = await cls.get_by_telegram_id(session, fields["telegram_id"])
            if existing and existing.id != access_id:
                raise ValueError(f"Telegram ID {fields['telegram_id']} boshqa yozuvda mavjud!")

        old_role = access.role
        old_tg_id = access.telegram_id

        for key, value in fields.items():
            if hasattr(access, key) and value is not None:
                setattr(access, key, value)

        await session.commit()
        await session.refresh(access)

        # Synchronize lawyer status if lawyer role or status was affected
        from app.services.user_service import UserService

        if access.role == "lawyer":
            await UserService.sync_lawyer_status(
                session, access.telegram_id, is_active_lawyer=access.is_active
            )
        elif old_role == "lawyer":
            still_lawyer = await cls.is_lawyer(session, old_tg_id)
            if not still_lawyer:
                await UserService.sync_lawyer_status(session, old_tg_id, is_active_lawyer=False)

        logger.info("Updated system access record: ID=%d", access.id)
        return access

    @classmethod
    async def delete(cls, session: AsyncSession, access_id: int) -> bool:
        """Delete system access record."""
        access = await cls.get_by_id(session, access_id)
        if not access:
            return False

        tg_id = access.telegram_id
        was_lawyer = access.role == "lawyer"

        await session.delete(access)
        await session.commit()

        if was_lawyer:
            from app.services.user_service import UserService

            still_lawyer = await cls.is_lawyer(session, tg_id)
            if not still_lawyer:
                await UserService.sync_lawyer_status(session, tg_id, is_active_lawyer=False)

        logger.info("Deleted system access record: ID=%d", access_id)
        return True

    @classmethod
    async def seed_default_access(cls, session: AsyncSession) -> None:
        """Automatically seed system access from environment settings if table is empty."""
        stmt = select(SystemAccess).limit(1)
        res = await session.execute(stmt)
        if res.scalar_one_or_none() is not None:
            return

        logger.info("system_access table is empty. Seeding defaults from environment...")

        if settings.LAWYER_TELEGRAM_ID:
            session.add(
                SystemAccess(
                    telegram_id=settings.LAWYER_TELEGRAM_ID,
                    role="lawyer",
                    name="Bosh Advokat",
                    description="Asosiy advokatlik hisobi (shaxsiy biznes-ulanish va to'liq huquqlar)",
                    is_active=True,
                )
            )

        if settings.ADMIN_GROUP_ID:
            session.add(
                SystemAccess(
                    telegram_id=settings.ADMIN_GROUP_ID,
                    role="group",
                    name="Asosiy Admin Guruhi",
                    description="Yangi buyurtmalar, to'lov kvitansiyalari va SOS xabarlari yuboriladigan guruh",
                    is_active=True,
                )
            )

        if settings.ADMIN_TELEGRAM_IDS:
            for raw in settings.ADMIN_TELEGRAM_IDS.split(","):
                clean = raw.strip()
                if clean.lstrip("-").isdigit():
                    tg_id = int(clean)
                    if tg_id != settings.LAWYER_TELEGRAM_ID:
                        session.add(
                            SystemAccess(
                                telegram_id=tg_id,
                                role="admin",
                                name="Bosh Administrator",
                                description="Admin paneliga kirish va sozlash huquqi",
                                is_active=True,
                            )
                        )

        await session.commit()
        logger.info("Successfully seeded default system access records.")
