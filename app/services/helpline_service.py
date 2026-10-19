"""Service for managing public helplines and categories."""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.helpline import Helpline

logger = logging.getLogger(__name__)

DEFAULT_HELPLINES: list[dict[str, Any]] = [
    # 1. Huquqni muhofaza qiluvchi organlar
    {
        "category_uz": "Huquqni muhofaza qiluvchi organlar",
        "category_ru": "Правоохранительные органы",
        "organization_uz": "Ichki ishlar vazirligi (IIV)",
        "organization_ru": "Министерство внутренних дел (МВД)",
        "phone_number": "102 / 1102",
        "description_uz": "Huquqbuzarliklar va jinoyatlar haqida xabar berish",
        "description_ru": "Сообщения о правонарушениях и преступлениях",
        "order": 1,
    },
    {
        "category_uz": "Huquqni muhofaza qiluvchi organlar",
        "category_ru": "Правоохранительные органы",
        "organization_uz": "Bosh prokuratura ishonch telefoni",
        "organization_ru": "Генеральная прокуратура Республики Узбекистан",
        "phone_number": "1007",
        "description_uz": "Qonun buzilishi, korrupsiya va tergov faoliyati ustidan shikoyatlar",
        "description_ru": "Жалобы на нарушения закона, коррупцию и действия следствия",
        "order": 2,
    },
    {
        "category_uz": "Huquqni muhofaza qiluvchi organlar",
        "category_ru": "Правоохранительные органы",
        "organization_uz": "Davlat xavfsizlik xizmati (DXX)",
        "organization_ru": "Служба государственной безопасности (СГБ)",
        "phone_number": "1630",
        "description_uz": "Davlat va jamoat xavfsizligiga tahdidlar bo'yicha",
        "description_ru": "По угрозам государственной и общественной безопасности",
        "order": 3,
    },
    {
        "category_uz": "Huquqni muhofaza qiluvchi organlar",
        "category_ru": "Правоохранительные органы",
        "organization_uz": "Milliy gvardiya ishonch telefoni",
        "organization_ru": "Телефон доверия Национальной гвардии",
        "phone_number": "191",
        "description_uz": "Jamoat tartibini saqlash bo'yicha murojaatlar",
        "description_ru": "Обращения по охране общественного порядка",
        "order": 4,
    },
    {
        "category_uz": "Huquqni muhofaza qiluvchi organlar",
        "category_ru": "Правоохранительные органы",
        "organization_uz": "Korrupsiyaga qarshi kurashish agentligi",
        "organization_ru": "Агентство по противодействию коррупции",
        "phone_number": "1084",
        "description_uz": "Mansabdor shaxslar korrupsiyasi va manfaatlar to'qnashuvi",
        "description_ru": "Сообщения о коррупции должностных лиц",
        "order": 5,
    },

    # 2. Sud tizimi
    {
        "category_uz": "Sud tizimi",
        "category_ru": "Судебная система",
        "organization_uz": "Oliy sud (Call-markaz & Ishonch telefoni)",
        "organization_ru": "Верховный суд Республики Узбекистан",
        "phone_number": "1144 / 1161",
        "description_uz": "Sud ishlari holati, sudya xatti-harakatlari va shikoyatlar",
        "description_ru": "Статус судебных дел, жалобы на действия судей",
        "order": 1,
    },
    {
        "category_uz": "Sud tizimi",
        "category_ru": "Судебная система",
        "organization_uz": "Toshkent shahar sudi (Fuqarolik ishlari)",
        "organization_ru": "Ташкентский городской суд (по гражданским делам)",
        "phone_number": "+998 71 244-12-98",
        "description_uz": "Fuqarolik, uy-joy, meros va oilaviy nizolar",
        "description_ru": "Гражданские, жилищные, наследственные и семейные споры",
        "order": 2,
    },
    {
        "category_uz": "Sud tizimi",
        "category_ru": "Судебная система",
        "organization_uz": "Toshkent shahar Iqtisodiy sudi",
        "organization_ru": "Ташкентский городской Экономический суд",
        "phone_number": "+998 71 233-14-11",
        "description_uz": "Tadbirkorlik faoliyati va shartnomaviy nizolar",
        "description_ru": "Предпринимательские и хозяйственные споры",
        "order": 3,
    },
    {
        "category_uz": "Sud tizimi",
        "category_ru": "Судебная система",
        "organization_uz": "Toshkent shahar Ma'muriy sudi",
        "organization_ru": "Ташкентский городской Административный суд",
        "phone_number": "+998 71 244-46-17",
        "description_uz": "Davlat organlari va mansabdor shaxslar qarorlari ustidan nizolar",
        "description_ru": "Споры по решениям государственных органов и должностных лиц",
        "order": 4,
    },
    {
        "category_uz": "Sud tizimi",
        "category_ru": "Судебная система",
        "organization_uz": "Sudyalar oliy kengashi ishonch telefoni",
        "organization_ru": "Высший судейский совет Республики Узбекистан",
        "phone_number": "1038",
        "description_uz": "Sudyalar daxlsizligi va odob-axloq qoidalarining buzilishi",
        "description_ru": "Вопросы судейской этики и неприкосновенности судей",
        "order": 5,
    },

    # 3. Davlat organlari va vazirliklar
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "O'zbekiston Respublikasi Prezidenti Xalq qabulxonasi",
        "organization_ru": "Народная приемная Президента Республики Узбекистан",
        "phone_number": "1000 / 0-800-210-00-00",
        "description_uz": "Aholining har qanday ijtimoiy-huquqiy masaladagi murojaatlari",
        "description_ru": "Все виды социально-правовых обращений граждан",
        "order": 1,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Adliya vazirligi ishonch telefoni",
        "organization_ru": "Министерство юстиции Республики Узбекистан",
        "phone_number": "1008",
        "description_uz": "Notariat, FXDYo, FHDYo, davlat xizmatlari va bepul huquqiy maslahat",
        "description_ru": "Госуслуги, нотариат, ЗАГС и правовая помощь",
        "order": 2,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Ombudsman (Inson huquqlari bo'yicha vakil)",
        "organization_ru": "Уполномоченный по правам человека (Омбудсман)",
        "phone_number": "1096",
        "description_uz": "Fuqarolarning konstitutsiyaviy huquqlari buzilishi bo'yicha",
        "description_ru": "По фактам нарушения конституционных прав граждан",
        "order": 3,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Biznes-ombudsman (Tadbirkorlar huquqlarini himoya qilish)",
        "organization_ru": "Бизнес-омбудсман (Защита прав предпринимателей)",
        "phone_number": "1100",
        "description_uz": "Tadbirkorlar faoliyatiga noqonuniy aralashuvlar va tekshiruvlar",
        "description_ru": "Защита бизнеса от незаконных проверок и вмешательства",
        "order": 4,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Soliq qo'mitasi ishonch telefoni",
        "organization_ru": "Налоговый комитет Республики Узбекистан",
        "phone_number": "1198",
        "description_uz": "Soliq qonunchiligi buzilishi va hisob-kitoblar bo'yicha",
        "description_ru": "Налоговые споры, консультации и нарушения",
        "order": 5,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Bojxona qo'mitasi ishonch telefoni",
        "organization_ru": "Таможенный комитет Республики Узбекистан",
        "phone_number": "1108",
        "description_uz": "Bojxona rasmiylashtiruvi va chegaradan o'tish masalalari",
        "description_ru": "Таможенное оформление и правила пересечения границы",
        "order": 6,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Mehnat inspeksiyasi ishonch telefoni",
        "organization_ru": "Государственная инспекция труда",
        "phone_number": "1176 / +998 71 200-06-00",
        "description_uz": "Noqonuniy ishdan bo'shatish, oylik maosh kechikishi va mehnat nizolari",
        "description_ru": "Незаконные увольнения, задержки зарплат и трудовые споры",
        "order": 7,
    },
    {
        "category_uz": "Davlat organlari va vazirliklar",
        "category_ru": "Государственные органы и министерства",
        "organization_uz": "Raqobat qo'mitasi (Iste'molchilar huquqlarini himoya qilish)",
        "organization_ru": "Комитет по развитию конкуренции (Защита прав потребителей)",
        "phone_number": "1159",
        "description_uz": "Sifatsiz tovarlar, aldamchi reklama va iste'molchi huquqlari buzilishi",
        "description_ru": "Защита прав потребителей от некачественных товаров и услуг",
        "order": 8,
    },

    # 4. Favqulodda va ijtimoiy yordam
    {
        "category_uz": "Favqulodda va ijtimoiy yordam",
        "category_ru": "Экстренные службы и социальная помощь",
        "organization_uz": "Yagona favqulodda xizmat (FVV Qutqaruv)",
        "organization_ru": "Единая служба спасения (МЧС)",
        "phone_number": "101 / 1050",
        "description_uz": "Favqulodda vaziyatlar, yong'in va qutqaruv operatsiyalari",
        "description_ru": "Чрезвычайные ситуации, пожарная охрана и спасатели",
        "order": 1,
    },
    {
        "category_uz": "Favqulodda va ijtimoiy yordam",
        "category_ru": "Экстренные службы и социальная помощь",
        "organization_uz": "Tez tibbiy yordam",
        "organization_ru": "Скорая медицинская помощь",
        "phone_number": "103",
        "description_uz": "Shoshilinch tibbiy yordam chaqiruvi",
        "description_ru": "Срочный вызов медицинской помощи",
        "order": 2,
    },
    {
        "category_uz": "Favqulodda va ijtimoiy yordam",
        "category_ru": "Экстренные службы и социальная помощь",
        "organization_uz": "Gaz avariya dispetcherlik xizmati",
        "organization_ru": "Аварийная газовая служба",
        "phone_number": "104",
        "description_uz": "Gaz sizib chiqishi va avariya holatlari bo'yicha",
        "description_ru": "Утечки газа и аварийные ситуации",
        "order": 3,
    },
    {
        "category_uz": "Favqulodda va ijtimoiy yordam",
        "category_ru": "Экстренные службы и социальная помощь",
        "organization_uz": "Xotin-qizlar va bolalarni zo'ravonlikdan himoya qilish ishonch telefoni",
        "organization_ru": "Национальная горячая линия помощи женщинам и детям",
        "phone_number": "1146",
        "description_uz": "Tazyiq va zo'ravonlikka uchragan ayollar va bolalar uchun 24/7 bepul psixologik-huquqiy yordam",
        "description_ru": "Круглосуточная правовая и психологическая помощь жертвам насилия",
        "order": 4,
    },
    {
        "category_uz": "Favqulodda va ijtimoiy yordam",
        "category_ru": "Экстренные службы и социальная помощь",
        "organization_uz": "Bolalar ombudsmani ishonch telefoni",
        "organization_ru": "Телефон доверия Детского омбудсмана",
        "phone_number": "150",
        "description_uz": "Voyaga yetmaganlarning qonuniy manfaatlari va huquqlarini himoya qilish",
        "description_ru": "Защита прав и законных интересов несовершеннолетних",
        "order": 5,
    },
]


class HelplineService:
    """Service to handle database operations for helplines."""

    @classmethod
    async def get_all(cls, session: AsyncSession) -> list[Helpline]:
        """Fetch all helplines sorted by category and order."""
        stmt = select(Helpline).order_by(Helpline.order.asc(), Helpline.id.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_active_categories(cls, session: AsyncSession) -> list[tuple[str, str]]:
        """Get distinct active categories (category_uz, category_ru)."""
        stmt = (
            select(Helpline.category_uz, Helpline.category_ru)
            .where(Helpline.is_active.is_(True))
            .distinct()
            .order_by(Helpline.category_uz.asc())
        )
        res = await session.execute(stmt)
        return list(res.all())

    @classmethod
    async def get_by_category(
        cls, session: AsyncSession, category_name: str
    ) -> list[Helpline]:
        """Get all active helplines for given category (matched by uz or ru)."""
        stmt = (
            select(Helpline)
            .where(
                Helpline.is_active.is_(True),
                (Helpline.category_uz == category_name) | (Helpline.category_ru == category_name),
            )
            .order_by(Helpline.order.asc(), Helpline.id.asc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def seed_default_helplines(cls, session: AsyncSession) -> None:
        """Seed default helplines if table is empty."""
        count_stmt = select(func.count(Helpline.id))
        count_res = await session.execute(count_stmt)
        count = count_res.scalar() or 0

        if count == 0:
            logger.info("Helplines table is empty. Seeding default public helplines...")
            for item in DEFAULT_HELPLINES:
                helpline = Helpline(**item)
                session.add(helpline)
            await session.commit()
            logger.info("Successfully seeded %d default helplines.", len(DEFAULT_HELPLINES))
