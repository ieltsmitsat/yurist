import asyncio
from app.db.session import AsyncSessionLocal, engine
from app.db.base import Base
from app.db.models.helpline import Helpline
from sqlalchemy import select

async def seed_helplines():
    helplines = [
        # --- Huquqni muhofaza qiluvchi organlar ---
        {
            "category_uz": "Huquqni muhofaza qiluvchi organlar",
            "category_ru": "Правоохранительные органы",
            "organization_uz": "O'zbekiston Respublikasi Ichki ishlar vazirligi (IIV)",
            "organization_ru": "Министерство внутренних дел РУз (МВД)",
            "phone_number": "102 / 1102",
            "description_uz": "Huquqbuzarliklar va jinoyatlar haqida xabar berish uchun",
            "description_ru": "Для сообщений о правонарушениях и преступлениях",
            "order": 1
        },
        {
            "category_uz": "Huquqni muhofaza qiluvchi organlar",
            "category_ru": "Правоохранительные органы",
            "organization_uz": "O'zbekiston Respublikasi Bosh prokuraturasi",
            "organization_ru": "Генеральная прокуратура Республики Узбекистан",
            "phone_number": "1007",
            "description_uz": "Qonun buzilish holatlari, korrupsiya va inson huquqlari buzilishi bo'yicha",
            "description_ru": "По фактам нарушения закона, коррупции и нарушения прав человека",
            "order": 2
        },
        {
            "category_uz": "Huquqni muhofaza qiluvchi organlar",
            "category_ru": "Правоохранительные органы",
            "organization_uz": "Davlat xavfsizlik xizmati (DXX)",
            "organization_ru": "Служба государственной безопасности (СГБ)",
            "phone_number": "1630",
            "description_uz": "Davlat va jamiyat xavfsizligiga tahdidlar bo'yicha",
            "description_ru": "По угрозам государственной и общественной безопасности",
            "order": 3
        },
        {
            "category_uz": "Huquqni muhofaza qiluvchi organlar",
            "category_ru": "Правоохранительные органы",
            "organization_uz": "Milliy gvardiya ishonch telefoni",
            "organization_ru": "Телефон доверия Национальной гвардии",
            "phone_number": "191",
            "description_uz": "Jamoat tartibini saqlash bo'yicha murojaatlar",
            "description_ru": "Обращения по охране общественного порядка",
            "order": 4
        },
        {
            "category_uz": "Huquqni muhofaza qiluvchi organlar",
            "category_ru": "Правоохранительные органы",
            "organization_uz": "Korrupsiyaga qarshi kurashish agentligi",
            "organization_ru": "Агентство по противодействию коррупции",
            "phone_number": "1084",
            "description_uz": "Korrupsiya holatlari haqida xabar berish",
            "description_ru": "Для сообщений о фактах коррупции",
            "order": 5
        },
        
        # --- Sud tizimi (Oliy va hududiy sudlar) ---
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "O'zbekiston Respublikasi Oliy sudi (Ishonch telefoni)",
            "organization_ru": "Верховный суд Республики Узбекистан (Телефон доверия)",
            "phone_number": "1144 / 1161",
            "description_uz": "Sud ishlari va sudya xatti-harakatlari yuzasidan umumiy murojaatlar",
            "description_ru": "Общие обращения по судебным делам и действиям судей",
            "order": 1
        },
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "Oliy sud Jamoatchilik va OAV bilan aloqalar boshqarmasi",
            "organization_ru": "Управление по связям с общественностью ВС РУз",
            "phone_number": "+998 71 239-01-36",
            "description_uz": "Oliy sud matbuot xizmati",
            "description_ru": "Пресс-служба Верховного суда",
            "order": 2
        },
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "Toshkent shahar sudi (Jinoyat ishlari bo'yicha)",
            "organization_ru": "Ташкентский городской суд (по уголовным делам)",
            "phone_number": "+998 71 244-12-88",
            "description_uz": "Poytaxt jinoyat ishlari sudlov hay'ati",
            "description_ru": "Судебная коллегия по уголовным делам столицы",
            "order": 3
        },
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "Toshkent shahar sudi (Fuqarolik ishlari bo'yicha)",
            "organization_ru": "Ташкентский городской суд (по гражданским делам)",
            "phone_number": "+998 71 244-12-98",
            "description_uz": "Poytaxt fuqarolik ishlari sudlov hay'ati",
            "description_ru": "Судебная коллегия по гражданским делам столицы",
            "order": 4
        },
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "Toshkent shahar Iqtisodiy sudi",
            "organization_ru": "Ташкентский городской Экономический суд",
            "phone_number": "+998 71 233-14-11",
            "description_uz": "Tadbirkorlik va iqtisodiy nizolar bo'yicha",
            "description_ru": "По предпринимательским и экономическим спорам",
            "order": 5
        },
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "Toshkent shahar Ma'muriy sudi",
            "organization_ru": "Ташкентский городской Административный суд",
            "phone_number": "+998 71 244-46-17",
            "description_uz": "Davlat organlari qarorlari ustidan shikoyatlar bo'yicha",
            "description_ru": "По жалобам на решения государственных органов",
            "order": 6
        },
        {
            "category_uz": "Sud tizimi",
            "category_ru": "Судебная система",
            "organization_uz": "O'zbekiston Respublikasi Konstitutsiyaviy sudi",
            "organization_ru": "Конституционный суд Республики Узбекистан",
            "phone_number": "+998 71 239-01-00",
            "description_uz": "Konstitutsiyaga oid ishlarni ko'rib chiqish",
            "description_ru": "Рассмотрение дел, касающихся Конституции",
            "order": 7
        },

        # --- Davlat organlari va idoralari ---
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "O'zbekiston Respublikasi Prezidentining Xalq qabulxonasi",
            "organization_ru": "Народная приемная Президента Республики Узбекистан",
            "phone_number": "1000 / 0-800-210-00-00",
            "description_uz": "Barcha turdagi ijtimoiy-huquqiy muammolar bo'yicha",
            "description_ru": "По всем видам социально-правовых проблем",
            "order": 1
        },
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "O'zbekiston Respublikasi Adliya vazirligi",
            "organization_ru": "Министерство юстиции Республики Узбекистан",
            "phone_number": "1008",
            "description_uz": "Davlat xizmatlari va huquqiy yordam bo'yicha murojaatlar",
            "description_ru": "Обращения по государственным услугам и правовой помощи",
            "order": 2
        },
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "Oliy Majlisning Inson huquqlari bo'yicha vakili (Ombudsman)",
            "organization_ru": "Уполномоченный по правам человека (Омбудсман)",
            "phone_number": "1096",
            "description_uz": "Inson huquqlari va erkinliklari buzilishi yuzasidan",
            "description_ru": "По фактам нарушения прав и свобод человека",
            "order": 3
        },
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "Oila va xotin-qizlar qo'mitasi (Zo'ravonlikka qarshi)",
            "organization_ru": "Комитет семьи и женщин (Против насилия)",
            "phone_number": "1146",
            "description_uz": "Oilaviy zo'ravonlik va tazyiqqa uchragan xotin-qizlar uchun",
            "description_ru": "Для женщин, подвергшихся домашнему насилию и притеснениям",
            "order": 4
        },
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "Soliq qo'mitasi ishonch telefoni",
            "organization_ru": "Телефон доверия Налогового комитета",
            "phone_number": "1198",
            "description_uz": "Soliqqa oid huquqbuzarliklar va maslahatlar",
            "description_ru": "Налоговые правонарушения и консультации",
            "order": 5
        },
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "Bojxona qo'mitasi ishonch telefoni",
            "organization_ru": "Телефон доверия Таможенного комитета",
            "phone_number": "1108",
            "description_uz": "Bojxona tizimidagi muammolar bo'yicha",
            "description_ru": "По проблемам в таможенной системе",
            "order": 6
        },
        {
            "category_uz": "Davlat organlari",
            "category_ru": "Государственные органы",
            "organization_uz": "Monopoliyaga qarshi kurashish qo'mitasi",
            "organization_ru": "Антимонопольный комитет",
            "phone_number": "1159",
            "description_uz": "Iste'molchilar huquqlarini himoya qilish",
            "description_ru": "Защита прав потребителей",
            "order": 7
        }
    ]

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(Helpline))
        existing = result.scalars().all()
        if existing:
            print("Already seeded!")
            return

        for data in helplines:
            h = Helpline(**data)
            session.add(h)
        await session.commit()
        print("Successfully seeded helplines!")

if __name__ == "__main__":
    asyncio.run(seed_helplines())
