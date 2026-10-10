"""Chat inbox and conversation history endpoints for web admin dashboard."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.bot_instance import bot
from app.db.session import get_db_session
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


class SendMessageRequest(BaseModel):
    text: str


@router.get("")
async def list_dialogs(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List all dialog threads with latest message snippet, unread info, and client details."""
    return await ChatService.get_dialogs_list(session=session, limit=limit)


@router.get("/{user_id}")
async def get_user_messages(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 150,
) -> list[dict[str, Any]]:
    """Fetch chronological message stream for a specific user dialog."""
    messages = await ChatService.get_conversation(session=session, user_id=user_id, limit=limit)
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "telegram_id": m.telegram_id,
            "sender_type": m.sender_type,
            "message_type": m.message_type,
            "text": m.text,
            "media_url": m.media_url,
            "telegram_message_id": m.telegram_message_id,
            "is_business": m.is_business,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.post("/{user_id}/send", status_code=status.HTTP_201_CREATED)
async def send_lawyer_reply(
    user_id: int,
    payload: SendMessageRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Lawyer sends a direct reply to the client via Telegram Bot from the admin dashboard."""
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message text cannot be empty"
        )

    try:
        msg = await ChatService.send_lawyer_reply(
            session=session,
            bot=bot,
            user_id=user_id,
            text=payload.text.strip(),
        )
        return {
            "ok": True,
            "id": msg.id,
            "user_id": msg.user_id,
            "sender_type": msg.sender_type,
            "text": msg.text,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {e}",
        )
