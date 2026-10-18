"""System Settings, Access Control, and Bot Configuration endpoints."""

from typing import Any

from dotenv import set_key
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.services.access_service import AccessService
from app.services.inquiry_debouncer import inquiry_debouncer

router = APIRouter(prefix="/settings", tags=["settings"])

ENV_FILE = ".env"


# --- Legacy / Global Bot Settings ---

class BotSettingsResponse(BaseModel):
    lawyer_telegram_id: int | None
    admin_group_id: int | None
    admin_telegram_ids: str
    inquiry_debounce_seconds: float = 3.0


class BotSettingsUpdate(BaseModel):
    lawyer_telegram_id: int | None = None
    admin_group_id: int | None = None
    admin_telegram_ids: str | None = None
    inquiry_debounce_seconds: float | None = None


@router.get("/bot", response_model=BotSettingsResponse)
async def get_bot_settings() -> dict[str, Any]:
    """Get current bot dynamic settings."""
    return {
        "lawyer_telegram_id": settings.LAWYER_TELEGRAM_ID,
        "admin_group_id": settings.ADMIN_GROUP_ID,
        "admin_telegram_ids": settings.ADMIN_TELEGRAM_IDS,
        "inquiry_debounce_seconds": inquiry_debouncer.debounce_seconds,
    }


@router.put("/bot", response_model=BotSettingsResponse)
async def update_bot_settings(payload: BotSettingsUpdate) -> dict[str, Any]:
    """Update bot dynamic settings in memory and .env file."""
    try:
        if payload.lawyer_telegram_id is not None:
            settings.LAWYER_TELEGRAM_ID = payload.lawyer_telegram_id
            set_key(ENV_FILE, "LAWYER_TELEGRAM_ID", str(payload.lawyer_telegram_id))

        if payload.admin_group_id is not None:
            settings.ADMIN_GROUP_ID = payload.admin_group_id
            set_key(ENV_FILE, "ADMIN_GROUP_ID", str(payload.admin_group_id))

        if payload.admin_telegram_ids is not None:
            settings.ADMIN_TELEGRAM_IDS = payload.admin_telegram_ids
            set_key(ENV_FILE, "ADMIN_TELEGRAM_IDS", payload.admin_telegram_ids)

        if payload.inquiry_debounce_seconds is not None:
            settings.INQUIRY_DEBOUNCE_SECONDS = payload.inquiry_debounce_seconds
            inquiry_debouncer.debounce_seconds = payload.inquiry_debounce_seconds
            set_key(ENV_FILE, "INQUIRY_DEBOUNCE_SECONDS", str(payload.inquiry_debounce_seconds))

        return {
            "lawyer_telegram_id": settings.LAWYER_TELEGRAM_ID,
            "admin_group_id": settings.ADMIN_GROUP_ID,
            "admin_telegram_ids": settings.ADMIN_TELEGRAM_IDS,
            "inquiry_debounce_seconds": inquiry_debouncer.debounce_seconds,
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {e}",
        )


# --- Access Management: Lawyers, Groups, Admins ---

class SystemAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    role: str
    name: str
    description: str | None = None
    is_active: bool
    created_at: Any = None


class SystemAccessCreate(BaseModel):
    telegram_id: int
    role: str = "lawyer"  # lawyer, group, admin
    name: str
    description: str | None = None
    is_active: bool = True


class SystemAccessUpdate(BaseModel):
    telegram_id: int | None = None
    role: str | None = None
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


@router.get("/access", response_model=list[SystemAccessResponse])
async def get_system_access_list(
    role: str | None = Query(default=None, description="Filter by role: lawyer, group, admin"),
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """List all authorized system access entries (lawyers, groups, admins)."""
    return await AccessService.get_all(session, role=role)


@router.post("/access", response_model=SystemAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_system_access(
    payload: SystemAccessCreate,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Create a new authorized lawyer, group, or admin."""
    try:
        return await AccessService.create(
            session=session,
            telegram_id=payload.telegram_id,
            role=payload.role,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create access entry: {e}",
        )


@router.put("/access/{access_id}", response_model=SystemAccessResponse)
async def update_system_access(
    access_id: int,
    payload: SystemAccessUpdate,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Update an existing system access entry."""
    try:
        updated = await AccessService.update(
            session=session,
            access_id=access_id,
            **payload.model_dump(exclude_unset=True),
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access entry not found",
            )
        return updated
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update access entry: {e}",
        )


@router.delete("/access/{access_id}")
async def delete_system_access(
    access_id: int,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, bool]:
    """Delete a system access entry."""
    success = await AccessService.delete(session, access_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access entry not found",
        )
    return {"ok": True}


# --- Prompts Management ---

class PromptsUpdate(BaseModel):
    prompts: dict[str, str]


@router.get("/prompts")
async def get_prompts() -> dict[str, Any]:
    """Get all AI prompts."""
    from app.services.ai.prompts import PromptManager

    return {"prompts": PromptManager.get_all()}


@router.put("/prompts")
async def update_prompts(payload: PromptsUpdate) -> dict[str, Any]:
    """Update AI prompts."""
    from app.services.ai.prompts import PromptManager

    try:
        PromptManager.save_all(payload.prompts)
        return {"prompts": PromptManager.get_all()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompts: {e}",
        )
