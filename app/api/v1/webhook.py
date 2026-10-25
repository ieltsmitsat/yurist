"""Telegram Bot Webhook endpoint with secret token validation."""

import hmac
import logging
from typing import Any

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, status

from app.bot.bot_instance import bot, dp
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    """Process incoming Telegram updates via Webhook."""
    expected_secret = settings.WEBHOOK_SECRET
    if not expected_secret and settings.ENVIRONMENT.lower() == "development":
        expected_secret = "dev_webhook_secret_for_tests"

    if expected_secret:
        if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
            x_telegram_bot_api_secret_token, expected_secret
        ):
            logger.warning("Unauthorized webhook request with invalid secret token")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid secret token",
            )
    elif settings.ENVIRONMENT.lower() == "production":
        logger.error("Rejecting webhook update: WEBHOOK_SECRET is not configured in production")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook secret token is not configured",
        )

    try:
        telegram_update = Update.model_validate(update, context={"bot": bot})
        await dp.feed_update(bot=bot, update=telegram_update)
        return {"ok": True}
    except Exception as e:
        logger.error("Error processing webhook update: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing update",
        ) from e
