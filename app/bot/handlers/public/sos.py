"""Emergency Legal SOS Hotline handlers."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.keyboards import sos_options_kb
from app.db.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="sos_router")
router.message.filter(F.chat.type == "private")


@router.message(F.text.in_(["🆘 Favqulodda yordam (SOS)", "🆘 Экстренная помощь (SOS)"]))
async def handle_sos_menu(message: Message, user: User | None = None) -> None:
    """Display Emergency SOS options and quick constitutional guide."""
    lang = user.language if user else "uz"
    text = (
        "🆘 <b>Shoshilinch Yuridik Yordam (SOS Hotline)</b>\n\n"
        "Siz yoki yaqinlaringiz IIB xodimlari tomonidan to'xtatilganda, "
        "tintuv yoki favqulodda huquqiy nizo yuzaga kelganda quyidagi qonuniy yo'riqnomadan foydalaning "
        "yoki zudlik bilan navbatchi advokatni chaqiring."
        if lang == "uz"
        else "🆘 <b>Экстренная юридическая помощь (SOS Hotline)</b>\n\n"
        "При остановке сотрудниками правоохранительных органов, "
        "обыске или задержании выберите соответствующую инструкцию или срочно вызовите адвоката."
    )
    await message.answer(text, reply_markup=sos_options_kb(lang))


@router.callback_query(F.data == "sos_guide:police")
async def handle_police_guide(callback: CallbackQuery, user: User | None = None) -> None:
    """Instant 30-second constitutional guide on police stops."""
    if not callback.message:
        return
    lang = user.language if user else "uz"
    guide = (
        "🚨 <b>IIB xodimi to'xtatganda 3 ta oltin qoida:</b>\n\n"
        "1. <b>O'zini tanishtirishni talab qiling:</b>\n"
        "Xodim lavozimi, unvoni, familiyasi va xizmat guvohnomasini ko'rsatishi shart ('Ichki ishlar to'g'risida'gi qonun, 9-modda).\n\n"
        "2. <b>Sukut saqlash huquqi:</b>\n"
        "Konstitutsiyaning 28-moddasiga binoan, o'zingizga va yaqinlaringizga qarshi ko'rsatma bermaslikka haqlisiz. Advokatingiz kelmaguncha hech qanday hujjatga imzo chekmang!\n\n"
        "3. <b>Telefon qo'ng'irog'i huquqi:</b>\n"
        "Ushlanganingizdan so'ng darhol yaqinlaringizga yoki advokatingizga qo'ng'iroq qilib, qayerda ekanligingizni xabar qilish huquqingiz bor."
        if lang == "uz"
        else "🚨 <b>3 правила при остановке полицией:</b>\n\n"
        "1. <b>Требуйте представиться:</b>\n"
        "Сотрудник обязан назвать должность, звание, фамилию и предъявить служебное удостоверение (Закон «Об ОВД», ст. 9).\n\n"
        "2. <b>Право на молчание:</b>\n"
        "Согласно ст. 28 Конституции РУз, никто не обязан свидетельствовать против себя и близких. Не подписывайте протоколы без адвоката!\n\n"
        "3. <b>Право на один звонок:</b>\n"
        "Вы имеете право немедленно уведомить адвоката или близких о месте вашего нахождения."
    )
    await callback.answer()
    await callback.message.answer(guide)


@router.callback_query(F.data == "sos_guide:raid")
async def handle_raid_guide(callback: CallbackQuery, user: User | None = None) -> None:
    """Legal guide during searches and raids."""
    if not callback.message:
        return
    lang = user.language if user else "uz"
    guide = (
        "🏢 <b>Biznes tekshiruvi va tintuv paytidagi qoidalar:</b>\n\n"
        "1. <b>Qarorni talab qiling:</b>\n"
        "Tergovchi yoki prokurorning asoslantirilgan tintuv qarori (yoki sud ajrimi) taqdim etilishi shart (JPK 157-modda).\n\n"
        "2. <b>Xolislar (Ponitiye) ishtiroki:</b>\n"
        "Tintuv kamida 2 nafar xolis guvoh ishtirokida o'tkazilishi shart. Xolislarning xolisligiga e'tibor bering.\n\n"
        "3. <b>Advokat ishtirokini talab qiling:</b>\n"
        "Siz advokatingiz kelguniga qadar tintuvni boshlamaslikni talab qilishga va bayonnomaga o'z e'tirozingizni yozishga haqlisiz."
        if lang == "uz"
        else "🏢 <b>Правила при обыске или проверке бизнеса:</b>\n\n"
        "1. <b>Требуйте постановление:</b>\n"
        "Следователь обязан предъявить мотивированное постановление об обыске (ст. 157 УПК РУз).\n\n"
        "2. <b>Участие понятых:</b>\n"
        "Обыск проводится с обязательным участием не менее двух понятых.\n\n"
        "3. <b>Участие адвоката:</b>\n"
        "Вы вправе требовать присутствия вашего адвоката и вносить возражения в протокол."
    )
    await callback.answer()
    await callback.message.answer(guide)


@router.callback_query(F.data == "sos_call_lawyer")
async def handle_sos_call(callback: CallbackQuery, user: User | None = None) -> None:
    """Instant lawyer dispatch hotline."""
    if not callback.message:
        return
    lang = user.language if user else "uz"
    hotline = (
        "🚨 <b>Favqulodda Advokat Chaqiruvi:</b>\n\n"
        "Zudlik bilan navbatchi advokat bilan bog'laning:\n"
        "📞 <b>+998 (90) 000-00-00</b> (24/7 Shoshilinch liniya)\n\n"
        "<i>Qo'ng'iroq paytida shaxsingizni, hozirgi joylashuvingizni (geolokatsiyani) "
        "va sizni kim ushlab turganini qisqa va aniq ayting.</i>"
        if lang == "uz"
        else "🚨 <b>Срочный вызов адвоката:</b>\n\n"
        "Горячая линия дежурного адвоката:\n"
        "📞 <b>+998 (90) 000-00-00</b> (Круглосуточно)\n\n"
        "<i>Назовите ваше имя, текущее местоположение и орган, проводящий задержание.</i>"
    )
    await callback.answer()
    await callback.message.answer(hotline)
