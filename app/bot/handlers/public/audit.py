"""Express document audit handlers (PDF and DOCX)."""

import io
import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.public.inquiry import _simulate_typing
from app.bot.keyboards.keyboards import cta_keyboard, phone_request_kb
from app.db.models.user import User
from app.services.inquiry_service import InquiryService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="audit_router")
router.message.filter(F.chat.type == "private")
inquiry_service = InquiryService()


@router.message(F.text.in_(["📑 Hujjat auditi", "📑 Аудит документа"]))
async def handle_audit_menu_click(message: Message, user: User | None = None) -> None:
    """Prompt user to upload a contract or legal document."""
    lang = user.language if user else "uz"
    prompt = (
        "📑 <b>Hujjat auditi</b>\n\n"
        "Shartnoma yoki huquqiy hujjatni (PDF yoki Word) yuboring. "
        "Advokat xavf balli va 2 ta asosiy zaiflikni ko'rsatib beradi."
        if lang == "uz"
        else "📑 <b>Аудит документа</b>\n\n"
        "Отправьте договор или документ (PDF или DOCX). "
        "Адвокат определит балл риска и 2 ключевые уязвимости."
    )
    await message.answer(prompt)


@router.message(F.document)
async def handle_document_upload(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle document upload for express audit."""
    if not message.from_user or not message.document:
        return

    # Hard gate check
    if not user or not user.phone_number:
        prompt = (
            "Hujjatni tahlil qilish uchun avval telefon raqamingizni yuboring:"
            if (user.language if user else "uz") == "uz"
            else "Для проведения аудита документа, пожалуйста, отправьте ваш номер телефона:"
        )
        await message.answer(prompt, reply_markup=phone_request_kb(user.language if user else "uz"))
        return

    lang = user.language
    filename = message.document.file_name or "document.pdf"
    ext = filename.lower().rsplit(".", 1)[-1]

    if ext not in ("pdf", "docx", "doc", "txt"):
        err = (
            "Faqat <b>PDF</b> yoki <b>Word (.docx)</b> formatidagi hujjatlar qabul qilinadi."
            if lang == "uz"
            else "Поддерживаются только форматы <b>PDF</b> или <b>DOCX</b>."
        )
        await message.answer(err)
        return

    # Check question balance
    if not await UserService.has_questions_available(user):
        limit_msg = (
            "Hurmatli mijoz, bepul savollar balansingiz yakunlandi.\n"
            "Advokat bilan shaxsiy konsultatsiya olishingiz yoki do'stlarni taklif qilib (+1 savol) olishingiz mumkin."
            if lang == "uz"
            else "Лимит бесплатных консультаций исчерпан. Запишитесь на консультацию или пригласите друзей (+1 вопрос)."
        )
        await message.answer(limit_msg, reply_markup=cta_keyboard("consultation", lang))
        return

    # Download document
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_document")
    buffer = io.BytesIO()

    try:
        file_info = await bot.get_file(message.document.file_id)
        if file_info.file_path:
            await bot.download_file(file_info.file_path, destination=buffer)
        file_bytes = buffer.getvalue()

        # Simulate typing and run express audit
        await _simulate_typing(bot, message.chat.id, duration=3.0)
        _inquiry, analysis = await inquiry_service.process_express_audit(
            session=session,
            user=user,
            filename=filename,
            file_bytes=file_bytes,
        )

        reply_kb = cta_keyboard(analysis.cta_type, lang)
        header = (
            f"📑 <b>Hujjat auditi natijasi:</b> <i>{filename}</i>\n"
            f"Xavf darajasi: <b>{analysis.risk_score}/100</b>\n\n"
            if lang == "uz"
            else f"📑 <b>Результат аудита:</b> <i>{filename}</i>\n"
            f"Оценка риска: <b>{analysis.risk_score}/100</b>\n\n"
        )
        await message.answer(header + analysis.response_text, reply_markup=reply_kb)

    except Exception as e:  # noqa: BLE001
        logger.error("Error processing document: %s", e)
        err = (
            "Hujjatni o'qishda xatolik yuz berdi. Fayl shikastlanmaganligiga ishonch hosil qiling "
            "yoki matn shaklida yuboring."
            if lang == "uz"
            else "Не удалось прочитать документ. Убедитесь в целостности файла."
        )
        await message.answer(err)


@router.callback_query(F.data == "order_service:audit")
async def handle_order_audit(callback: CallbackQuery, user: User | None = None) -> None:
    """Prompt user to order a full contract audit."""
    if not callback.message:
        return
    lang = user.language if user else "uz"
    text = (
        "💼 <b>To'liq Shartnoma Auditi xizmati</b>\n\n"
        "Advokat hujjatning barcha bandlarini amaldagi qonunchilikka muvofiq tekshiradi, "
        "barcha yashirin risklarni olib tashlaydi va sizning manfaatlaringizni to'liq himoya qiluvchi tahrirni tayyorlaydi.\n\n"
        "Xizmat narxi: <b>150 000 so'm</b>\n\n"
        "Buyurtma berish uchun quyidagi to'lov usulini tanlang yoki advokat bilan bog'laning."
        if lang == "uz"
        else "💼 <b>Полный аудит договора</b>\n\n"
        "Юрист проверит все пункты на соответствие законодательству РУз, "
        "устранит скрытые риски и составит безопасную редакцию документа.\n\n"
        "Стоимость: <b>150 000 сум</b>."
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(text, reply_markup=cta_keyboard("consultation", lang))
