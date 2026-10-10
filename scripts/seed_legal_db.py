"""Database seeding script for Uzbekistan Legal Knowledge Base (Lex.uz RAG)."""

import asyncio
import logging

from app.db.models.legal_chunk import LegalChunk
from app.db.session import AsyncSessionLocal
from app.services.ai.rag import RAGService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample core articles from Uzbekistan legislation for initial RAG seeding
SEED_LEGAL_ARTICLES = [
    {
        "law_title": "O'zbekiston Respublikasi Konstitutsiyasi",
        "article_number": "28-modda",
        "chunk_text": (
            "Hech kim o'ziga va yaqin qarindoshlariga qarshi guvohlik berishga majbur emas. "
            "Agar shaxsning o'z aybini tan olganligi to'g'risidagi ko'rsatmalari unga qarshi yagona dalil bo'lsa, "
            "u aybdor deb topilishi yoki jazoga tortilishi mumkin emas. "
            "Ozodlikdan mahrum etilgan shaxslar o'ziga nisbatan insoniy munosabatda bo'linishi va qadr-qimmati hurmat qilinishi huquqiga ega."
        ),
        "lex_url": "https://lex.uz/docs/6445145",
    },
    {
        "law_title": "O'zbekiston Respublikasi Fuqarolik kodeksi",
        "article_number": "356-modda",
        "chunk_text": (
            "Shartnoma tuzish to'g'risidagi taklif (oferta) bir yoki bir necha muayyan shaxsga yuborilgan, "
            "etarlicha aniq bo'lgan va taklif qiluvchi shaxsning o'zini taklif qabul qilingan taqdirda "
            "shartnoma tuzgan deb hisoblash niyatini ifodalaydigan taklif oferta deb e'tirof etiladi."
        ),
        "lex_url": "https://lex.uz/docs/111189",
    },
    {
        "law_title": "O'zbekiston Respublikasi Fuqarolik kodeksi",
        "article_number": "1134-modda",
        "chunk_text": (
            "Meros ochilgan kundan e'tiboran olti oy ichida meros qabul qilib olinishi mumkin. "
            "Meros qabul qilish merosxo'rning meros ochilgan joydagi notariusga merosni qabul qilganligi yoki "
            "merosga bo'lgan huquq to'g'risida guvohnoma berish haqidagi arizasini topshirish orqali amalga oshiriladi."
        ),
        "lex_url": "https://lex.uz/docs/180550",
    },
    {
        "law_title": "O'zbekiston Respublikasi Mehnat kodeksi",
        "article_number": "161-modda",
        "chunk_text": (
            "Xodim bilan tuzilgan mehnat shartnomasini ish beruvchining tashabbusi bilan bekor qilish asoslari: "
            "tashkilot (uning alohida bo'linmasi) tugatilganligi; xodimlar soni yoki shtati qisqarganligi; "
            "xodimning malakasi yetarli bo'lmaganligi sababli egallab turgan lavozimiga yoki bajarayotgan ishiga nomuvofiqligi."
        ),
        "lex_url": "https://lex.uz/docs/6257288",
    },
    {
        "law_title": "O'zbekiston Respublikasi Oila kodeksi",
        "article_number": "96-modda",
        "chunk_text": (
            "Ota-ona voyaga yetmagan bolalariga ta'minot berishi shart. "
            "Voyaga yetmagan bolalariga ta'minot berish majburiyatini ixtiyoriy ravishda bajarmagan ota (ona)dan "
            "sudning hal qiluv qaroriga yoki sud buyrug'iga asosan aliment undiriladi."
        ),
        "lex_url": "https://lex.uz/docs/104720",
    },
    {
        "law_title": "O'zbekiston Respublikasining 'Ichki ishlar organlari to'g'risida'gi Qonuni",
        "article_number": "9-modda",
        "chunk_text": (
            "Ichki ishlar organi xodimi fuqaroga murojaat etganda o'z lavozimini, unvonini, familiyasini aytishi, "
            "fuqaroning talabiga ko'ra xizmat guvohnomasini ko'rsatishi, shundan so'ng murojaat etishining sababi va maqsadini ma'lum qilishi shart. "
            "Fuqaroning huquq va erkinliklarini cheklovchi choralar qo'llanilgan taqdirda, bunday choralar qo'llanilishining sabab va asoslarini tushuntirishi shart."
        ),
        "lex_url": "https://lex.uz/docs/3027843",
    },
]


async def seed_database() -> None:
    """Seed sample laws and compute vectors."""
    logger.info("Starting Lex.uz legal database seeding...")
    rag = RAGService()

    async with AsyncSessionLocal() as session:
        for item in SEED_LEGAL_ARTICLES:
            logger.info(
                "Generating embedding for %s (%s)...", item["law_title"], item["article_number"]
            )
            try:
                embedding = await rag.get_embedding(item["chunk_text"])
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not generate OpenAI embedding (skipping vector): %s", e)
                embedding = None

            chunk = LegalChunk(
                law_title=item["law_title"],
                article_number=item["article_number"],
                chunk_text=item["chunk_text"],
                lex_url=item["lex_url"],
                embedding=embedding,
            )
            session.add(chunk)

        await session.commit()
        logger.info("Seeding completed successfully! Added %d articles.", len(SEED_LEGAL_ARTICLES))


if __name__ == "__main__":
    asyncio.run(seed_database())
