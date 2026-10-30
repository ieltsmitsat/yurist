"""Instagram Meta Graph API Webhook endpoints."""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis_client
from app.db.session import get_db_session
from app.services.chat_service import ChatService
from app.services.instagram.security import verify_meta_hub_signature
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
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    redis_client: Any = Depends(get_redis_client),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, Any]:
    """Receive and process incoming Instagram comments and Direct Messages with HMAC verification."""
    raw_body = await request.body()

    # Meta Webhook Security Signature Check (HMAC-SHA256)
    app_secret = settings.INSTAGRAM_APP_SECRET
    if app_secret:
        if not verify_meta_hub_signature(raw_body, x_hub_signature_256, app_secret):
            logger.warning("Rejected Instagram webhook with invalid X-Hub-Signature-256")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Meta X-Hub-Signature-256 signature",
            )
    elif settings.ENVIRONMENT.lower() == "production":
        logger.error("Rejecting Instagram webhook: INSTAGRAM_APP_SECRET is not configured in production")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instagram App Secret is not configured",
        )

    try:
        body: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
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
                    db_session=db_session,
                    event_data=event,
                )

    return {"status": "ok"}


class InstagramSendRequest(BaseModel):
    instagram_id: str
    text: str


class InstagramPauseRequest(BaseModel):
    instagram_id: str
    pause: bool = True
    duration_minutes: int = 30


@router.get("/chats")
async def list_instagram_chats(
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List Instagram-specific conversations with client details and message stats."""
    dialogs = await ChatService.get_dialogs_list(session=db_session, limit=limit)
    return [
        d for d in dialogs
        if d.get("platform") in ("instagram", "both") or d.get("instagram_id")
    ]


@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_manual_instagram_reply(
    payload: InstagramSendRequest,
    redis_client: Any = Depends(get_redis_client),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, Any]:
    """Lawyer sends manual message to Instagram lead from admin dashboard (activates 30-min AI pause)."""
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message text cannot be empty")

    success = await _instagram_service.send_manual_lawyer_reply(
        sender_id=payload.instagram_id.strip(),
        text=payload.text.strip(),
        redis_client=redis_client,
        db_session=db_session,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send message via Meta Graph API",
        )
    return {"ok": True, "instagram_id": payload.instagram_id}


@router.post("/pause")
async def toggle_instagram_ai_pause(
    payload: InstagramPauseRequest,
    redis_client: Any = Depends(get_redis_client),  # noqa: B008
) -> dict[str, Any]:
    """Pause or resume AI automated responses for a specific Instagram conversation."""
    ig_id = payload.instagram_id.strip()
    if payload.pause:
        await _instagram_service.handoff_skill.set_lawyer_takeover(
            chat_id=ig_id,
            redis_client=redis_client,
            pause_seconds=max(60, payload.duration_minutes * 60),
        )
    else:
        await _instagram_service.handoff_skill.resume_ai(
            chat_id=ig_id,
            redis_client=redis_client,
        )
    return {"ok": True, "instagram_id": ig_id, "paused": payload.pause}
