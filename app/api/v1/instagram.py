"""Instagram Meta Graph API Webhook endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.core.redis import get_redis_client
from app.services.instagram.service import InstagramAutomationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instagram", tags=["instagram"])
_instagram_service = InstagramAutomationService()


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_instagram_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
) -> Response:
    """Verify Meta Webhook subscription challenge."""
    challenge = _instagram_service.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge is not None:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post("/webhook")
async def handle_instagram_webhook_events(
    request: Request,
    redis_client: Any = Depends(get_redis_client),  # noqa: B008
) -> dict[str, Any]:
    """Receive and process incoming Instagram comments and Direct Messages."""
    try:
        body: dict[str, Any] = await request.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("Invalid JSON in Instagram webhook: %s", e)
        return {"status": "ignored"}

    object_type = body.get("object")
    if object_type != "instagram":
        return {"status": "ignored", "reason": "non-instagram object"}

    entries = body.get("entry") or []
    for entry in entries:
        # 1. Check for comment feed changes (Skill 1: Comment-to-DM)
        changes = entry.get("changes") or []
        for change in changes:
            field = change.get("field")
            value = change.get("value") or {}
            if field == "comments" or value.get("item") == "comment":
                await _instagram_service.handle_comment_event(value, redis_client=redis_client)

        # 2. Check for Direct messaging events (Skills 2-9)
        messaging_events = entry.get("messaging") or []
        for event in messaging_events:
            sender_id = str(event.get("sender", {}).get("id") or "")
            message_data = event.get("message") or {}

            if sender_id and message_data:
                await _instagram_service.handle_direct_message(
                    sender_id=sender_id,
                    message_data=message_data,
                    redis_client=redis_client,
                )

    return {"status": "ok"}
