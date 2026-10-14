"""System Settings and Bot Configuration endpoints."""

from typing import Any

from dotenv import set_key
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])

ENV_FILE = ".env"


class BotSettingsResponse(BaseModel):
    lawyer_telegram_id: int | None
    admin_group_id: int | None
    admin_telegram_ids: str


class BotSettingsUpdate(BaseModel):
    lawyer_telegram_id: int | None = None
    admin_group_id: int | None = None
    admin_telegram_ids: str | None = None


@router.get("/bot", response_model=BotSettingsResponse)
async def get_bot_settings() -> dict[str, Any]:
    """Get current bot dynamic settings."""
    return {
        "lawyer_telegram_id": settings.LAWYER_TELEGRAM_ID,
        "admin_group_id": settings.ADMIN_GROUP_ID,
        "admin_telegram_ids": settings.ADMIN_TELEGRAM_IDS,
    }


@router.put("/bot", response_model=BotSettingsResponse)
async def update_bot_settings(payload: BotSettingsUpdate) -> dict[str, Any]:
    """Update bot dynamic settings in memory and .env file."""
    try:
        # Update in-memory
        if payload.lawyer_telegram_id is not None:
            settings.LAWYER_TELEGRAM_ID = payload.lawyer_telegram_id
            set_key(ENV_FILE, "LAWYER_TELEGRAM_ID", str(payload.lawyer_telegram_id))

        if payload.admin_group_id is not None:
            settings.ADMIN_GROUP_ID = payload.admin_group_id
            set_key(ENV_FILE, "ADMIN_GROUP_ID", str(payload.admin_group_id))

        if payload.admin_telegram_ids is not None:
            settings.ADMIN_TELEGRAM_IDS = payload.admin_telegram_ids
            set_key(ENV_FILE, "ADMIN_TELEGRAM_IDS", payload.admin_telegram_ids)

        return {
            "lawyer_telegram_id": settings.LAWYER_TELEGRAM_ID,
            "admin_group_id": settings.ADMIN_GROUP_ID,
            "admin_telegram_ids": settings.ADMIN_TELEGRAM_IDS,
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {e}",
        )


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

