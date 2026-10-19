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
    """List all transactions with customer details, purchased service, and problem summary."""
    from app.db.models.inquiry import Inquiry

    stmt = (
        select(
            Transaction,
            User.full_name,
            User.telegram_id,
            User.phone_number,
            Inquiry.question_text,
        )
        .join(User, Transaction.user_id == User.id)
        .outerjoin(Inquiry, Transaction.inquiry_id == Inquiry.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )

    if payment_status:
        stmt = stmt.where(Transaction.payment_status == payment_status)

    res = await session.execute(stmt)
    rows = res.all()

    # If any transaction has no linked inquiry, fetch the latest inquiry for that user
    missing_inq_uids = [
        tx.user_id for tx, _fn, _tid, _ph, q_text in rows if not q_text and tx.user_id
    ]
    latest_inqs: dict[int, str] = {}
    if missing_inq_uids:
        inq_stmt = (
            select(Inquiry.user_id, Inquiry.question_text)
            .where(Inquiry.user_id.in_(set(missing_inq_uids)))
            .order_by(Inquiry.id.desc())
        )
        inq_res = await session.execute(inq_stmt)
        for u_id, q_text in inq_res.all():
            if u_id not in latest_inqs and q_text:
                latest_inqs[u_id] = q_text

    result: list[dict[str, Any]] = []
    for tx, full_name, telegram_id, phone_number, q_text in rows:
        problem = q_text or latest_inqs.get(tx.user_id) or ""
        service = tx.transaction_ref or "Yuridik xizmat / Konsultatsiya"

        result.append(
            {
                "id": tx.id,
                "user_id": tx.user_id,
                "user_name": full_name or "Unknown",
                "telegram_id": telegram_id,
                "phone_number": phone_number,
                "amount": float(tx.amount),
                "payment_method": tx.payment_method,
                "payment_status": tx.payment_status,
                "transaction_ref": tx.transaction_ref,
                "service_title": service,
                "problem_summary": problem,
                "inquiry_id": tx.inquiry_id,
                "appointment_id": tx.appointment_id,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
        )

    return result


@router.put("/{transaction_id}/status")
async def update_transaction_status(
    transaction_id: int,
    payload: TransactionStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Update transaction payment status (e.g., confirm or reject payment)."""
    import logging

    from app.bot.bot_instance import bot

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

    # Notify user via Telegram if status changed
    if old_status != tx.payment_status:
        user_stmt = select(User).where(User.id == tx.user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if user and user.telegram_id:
            lang = user.language or "uz"

            if tx.payment_status == "completed":
                text = (
                    "✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                    "To'lov qabul qilindi. Tez orada huquqshunoslarimiz siz bilan aloqaga chiqishadi."
                    if lang == "uz"
                    else "✅ <b>Ваш платеж успешно подтвержден!</b>\n\n"
                    "Оплата принята. В ближайшее время наши юристы свяжутся с вами."
                )
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=text)
                except Exception as e:  # noqa: BLE001
                    logging.getLogger(__name__).warning("Could not send payment confirmation to %s: %s", user.telegram_id, e)

            elif tx.payment_status == "failed":
                text = (
                    "⚠️ <b>To'lovni tekshirishda muammo yuzaga keldi</b>\n\n"
                    "Siz yuborgan to'lov cheki yoki ma'lumotlarida noaniqlik aniqlandi va to'lov tasdiqlanmadi.\n\n"
                    "Iltimos, to'lov muvaffaqiyatli o'tganligini tekshirib, chek skrinshotini qaytadan yuboring "
                    "yoki yordam uchun huquqshunos bilan bog'laning."
                    if lang == "uz"
                    else "⚠️ <b>Возникла проблема при проверке платежа</b>\n\n"
                    "В отправленном чеке или реквизитах обнаружена неточность, платеж не подтвержден.\n\n"
                    "Пожалуйста, проверьте списание средств и отправьте квитанцию повторно "
                    "либо свяжитесь с юристом."
                )
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=text)
                except Exception as e:  # noqa: BLE001
                    logging.getLogger(__name__).warning("Could not send payment rejection to %s: %s", user.telegram_id, e)

            elif tx.payment_status == "fulfilled":
                from app.bot.keyboards.keyboards import service_fulfillment_kb
                from app.core.config import settings
                from app.services.referral_service import ReferralService

                bot_user = await bot.get_me()
                bot_username = bot_user.username or settings.BOT_USERNAME
                ref_link = ReferralService.get_referral_link(bot_username, user)

                text = (
                    "🎉 <b>Hurmatli mijoz!</b>\n\n"
                    "Siz buyurtma qilgan yuridik xizmat muvaffaqiyatli bajarildi va yakunlandi!\n\n"
                    "Biz uchun sizning fikringiz juda muhim. Iltimos, ko'rsatilgan xizmat sifatini baholang:"
                    if lang == "uz"
                    else "🎉 <b>Уважаемый клиент!</b>\n\n"
                    "Юридическая услуга успешно выполнена в полном объеме!\n\n"
                    "Нам очень важно ваше мнение. Пожалуйста, оцените качество оказанной услуги:"
                )
                kb = service_fulfillment_kb(tx_id=tx.id, ref_link=ref_link, lang=lang)
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=kb)
                except Exception as e:  # noqa: BLE001
                    logging.getLogger(__name__).warning("Could not send service fulfillment to %s: %s", user.telegram_id, e)

    return {"ok": True, "id": tx.id, "status": tx.payment_status}
