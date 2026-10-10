"""Payment and legal services ledger service (Safe abstraction adhering to Off-limits rule)."""

import logging
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.service import Service
from app.db.models.transaction import Transaction
from app.db.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_LEGAL_SERVICES: list[dict[str, Any]] = [
    {
        "title_uz": "📞 Shaxsiy advokat konsultatsiyasi",
        "title_ru": "📞 Индивидуальная консультация адвоката",
        "description_uz": (
            "Advokat bilan 45 daqiqalik yakkama-yakka muloqot (onlayn yoki ofisda).\n"
            "• Vaziyatingiz va mavjud hujjatlarning chuqur huquqiy tahlili;\n"
            "• Huquqiy xavf-xatarlarni oldindan aniqlash;\n"
            "• Muammoni hal qilishning eng samarali va qonuniy yo'llari xaritasi."
        ),
        "description_ru": (
            "45-минутная индивидуальная консультация с опытным адвокатом (онлайн или в офисе).\n"
            "• Полный правовой анализ вашей ситуации и документов;\n"
            "• Оценка юридических и финансовых рисков;\n"
            "• Пошаговый алгоритм защиты ваших интересов."
        ),
        "price": Decimal("150000.00"),
        "service_type": "consultation",
    },
    {
        "title_uz": "📑 Shartnoma auditi va huquqiy ekspertiza",
        "title_ru": "📑 Экспертиза и полный аудит договора",
        "description_uz": (
            "Oldi-sotdi, ijara, qarz, mehnat yoki tijorat shartnomalarining chuqur ekspertizasi.\n"
            "• Yashirin xavfli bandlar va noqulay majburiyatlarni aniqlash;\n"
            "• O'zbekiston qonunchiligiga zid joylarni to'g'rilash;\n"
            "• Mijoz foydasiga tuzilgan tahrir va advokat xulosasi."
        ),
        "description_ru": (
            "Глубокая юридическая экспертиза любых договоров (купли-продажи, займа, аренды, услуг).\n"
            "• Выявление скрытых ловушек, штрафов и невыгодных условий;\n"
            "• Проверка на соответствие законодательству Республики Узбекистан;\n"
            "• Внесение правок в ваших интересах и заключение адвоката."
        ),
        "price": Decimal("300000.00"),
        "service_type": "audit",
    },
    {
        "title_uz": "📝 Da'vo arizasi va talabnoma tuzish",
        "title_ru": "📝 Составление иска и претензии",
        "description_uz": (
            "Sudgacha hal etish talabnomasi yoki sudga rasmiy da'vo arizasi tayyorlash.\n"
            "• Qarzni undirish, yetkazilgan zararni qoplash, mulk nizolari;\n"
            "• Qonun moddalari va Oliy Sud amaliyoti bilan asoslangan hujjat;\n"
            "• Davlat boji hisob-kitobi va sudga topshirish bo'yicha ko'rsatma."
        ),
        "description_ru": (
            "Составление досудебной претензии или официального искового заявления в суд.\n"
            "• Взыскание долгов, возмещение ущерба, имущественные и трудовые споры;\n"
            "• Нормативное обоснование статьями кодексов и практикой ВС РУз;\n"
            "• Расчет госпошлины и инструкция по подаче в суд."
        ),
        "price": Decimal("500000.00"),
        "service_type": "claim",
    },
    {
        "title_uz": "⚖️ Sudda advokat himoyasi va vakilligi",
        "title_ru": "⚖️ Представительство и защита в суде",
        "description_uz": (
            "Fuqarolik, iqtisodiy va ma'muriy sudlarda ishingizni to'liq olib borish.\n"
            "• Ish materiallari bilan tanishish va ishonchli himoya strategiyasi;\n"
            "• Barcha sud majlislarida advokatning shaxsan ishtirok etishi;\n"
            "• Dalillar to'plash, iltimosnomalar va shikoyatlar kiritish."
        ),
        "description_ru": (
            "Полное судебное представительство в гражданских, экономических и административных судах.\n"
            "• Формирование выигрышной правовой позиции и стратегии защиты;\n"
            "• Личное участие адвоката во всех судебных заседаниях;\n"
            "• Сбор доказательств, ходатайства, апелляция и кассация."
        ),
        "price": Decimal("2500000.00"),
        "service_type": "court",
    },
    {
        "title_uz": "🏢 Biznes uchun oylik yuridik hamrohlik",
        "title_ru": "🏢 Абонентское юридическое обслуживание бизнеса",
        "description_uz": (
            "Kompaniya va YaTTlar uchun to'liq yuridik autsorsing paketi (oyiga).\n"
            "• Korporativ shartnomalarni cheksiz tezkor tekshirish va tuzish;\n"
            "• Kadrlar va mehnat munosabatlari hujjatlari auditi;\n"
            "• Davlat organlari tekshiruvlarida tezkor advokat maslahati va himoyasi."
        ),
        "description_ru": (
            "Комплексный юридический аутсорсинг для компаний и ИП (в месяц).\n"
            "• Неограниченная проверка и составление коммерческих контрактов;\n"
            "• Аудит трудовых отношений и кадровой документации;\n"
            "• Защита при проверках госорганов и приоритетные консультации."
        ),
        "price": Decimal("4000000.00"),
        "service_type": "retainer",
    },
]


class PaymentService:
    """Manages service catalog, transaction creation, and payment statuses safely."""

    @classmethod
    async def get_active_services(cls, session: AsyncSession) -> Sequence[Service]:
        """Fetch all currently active legal services."""
        stmt = select(Service).where(Service.is_active.is_(True)).order_by(Service.price.asc())
        res = await session.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_service_by_id(cls, session: AsyncSession, service_id: int) -> Service | None:
        """Fetch service by ID."""
        stmt = select(Service).where(Service.id == service_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def create_transaction(
        cls,
        session: AsyncSession,
        user: User,
        amount: Decimal,
        payment_method: str,
        inquiry_id: int | None = None,
        appointment_id: int | None = None,
        transaction_ref: str | None = None,
    ) -> Transaction:
        """Record a new payment transaction in pending state."""
        tx = Transaction(
            user_id=user.id,
            inquiry_id=inquiry_id,
            appointment_id=appointment_id,
            amount=amount,
            payment_method=payment_method,
            payment_status="pending",
            transaction_ref=transaction_ref,
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        logger.info(
            "Created pending transaction #%d for user #%d: amount=%s", tx.id, user.id, str(amount)
        )
        return tx

    @classmethod
    async def confirm_payment(
        cls,
        session: AsyncSession,
        transaction_id: int,
        transaction_ref: str | None = None,
    ) -> Transaction | None:
        """Mark transaction as completed and activate service."""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()
        if tx and tx.payment_status != "completed":
            tx.payment_status = "completed"
            if transaction_ref:
                tx.transaction_ref = transaction_ref
            await session.commit()
            await session.refresh(tx)
            logger.info("Confirmed payment for transaction #%d", tx.id)
        return tx

    @classmethod
    async def get_service_by_type(
        cls, session: AsyncSession, service_type: str
    ) -> Service | None:
        """Fetch first active service matching service_type."""
        stmt = (
            select(Service)
            .where(Service.service_type == service_type)
            .where(Service.is_active.is_(True))
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def seed_default_services(cls, session: AsyncSession) -> int:
        """Seed initial legal services catalog if empty."""
        stmt = select(func.count(Service.id))
        res = await session.execute(stmt)
        count = res.scalar() or 0
        if count > 0:
            return 0

        for item in DEFAULT_LEGAL_SERVICES:
            srv = Service(**item)
            session.add(srv)
        await session.commit()
        logger.info(
            "Successfully seeded %d legal services into catalog.", len(DEFAULT_LEGAL_SERVICES)
        )
        return len(DEFAULT_LEGAL_SERVICES)
