"""Transaction management API for admin panel."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.db.session import get_db_session

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionStatusUpdate(BaseModel):
    payment_status: str  # pending, completed, failed, refunded
    transaction_ref: str | None = None


@router.get("")
async def list_transactions(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    payment_status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List all transactions with optional status filter."""
    stmt = select(Transaction, User.full_name, User.telegram_id).join(
        User, Transaction.user_id == User.id
    ).order_by(Transaction.created_at.desc()).limit(limit)

    if payment_status:
        stmt = stmt.where(Transaction.payment_status == payment_status)

    res = await session.execute(stmt)
    rows = res.all()

    return [
        {
            "id": tx.id,
            "user_id": tx.user_id,
            "user_name": full_name or "Unknown",
            "telegram_id": telegram_id,
            "amount": float(tx.amount),
            "payment_method": tx.payment_method,
            "payment_status": tx.payment_status,
            "transaction_ref": tx.transaction_ref,
            "inquiry_id": tx.inquiry_id,
            "appointment_id": tx.appointment_id,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        }
        for tx, full_name, telegram_id in rows
    ]


@router.put("/{transaction_id}/status")
async def update_transaction_status(
    transaction_id: int,
    payload: TransactionStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Update transaction payment status (e.g., confirm payment)."""
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    res = await session.execute(stmt)
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    old_status = tx.payment_status
    tx.payment_status = payload.payment_status
    if payload.transaction_ref:
        tx.transaction_ref = payload.transaction_ref
    await session.commit()
    await session.refresh(tx)

    # Notify user via Telegram if payment is newly completed
    if old_status != "completed" and tx.payment_status == "completed":
        user_stmt = select(User).where(User.id == tx.user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if user and user.telegram_id:
            import logging

            from app.bot.bot_instance import bot
            lang = user.language or "uz"
            
            text = (
                "✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                "Iltimos, biroz kutib tursangiz, huquqshunoslarimiz tez orada siz bilan bog'lanishadi."
                if lang == "uz"
                else "✅ <b>Ваш платеж успешно подтвержден!</b>\n\n"
                "Пожалуйста, подождите немного, наши юристы скоро с вами свяжутся."
            )
            try:
                await bot.send_message(chat_id=user.telegram_id, text=text)
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).warning("Could not send payment confirmation to %s: %s", user.telegram_id, e)

    return {"ok": True, "id": tx.id, "status": tx.payment_status}
