
"""Runner script to launch Yurist Telegram Bot in polling mode with database auto-init."""

import asyncio
import logging

import uvicorn
from aiogram.exceptions import (
    TelegramConflictError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramUnauthorizedError,
)
from sqlalchemy import func, select, text

import app.db.models  # noqa: F401 - register all SQLAlchemy models
from app.api.main import app as fastapi_app
from app.bot.bot_instance import bot, dp
from app.bot.main import setup_bot_dispatcher
from app.core.config import settings
from app.db.base import Base
from app.db.models.legal_chunk import LegalChunk
from app.db.session import AsyncSessionLocal, engine
from app.services.access_service import AccessService
from app.services.ai.rag import RAGService
from app.services.chat_service import ChatService
from app.services.payment_service import PaymentService
from app.services.user_service import UserService
from scripts.seed_legal_db import SEED_LEGAL_ARTICLES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("yurist_runner")


async def init_database() -> None:
    """Create tables and seed legal knowledge base if empty."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure topic columns exist on system_access table in existing deployments
        for col in ["lead_topic_id", "contact_topic_id", "payment_topic_id"]:
            try:
                if "postgres" in settings.DATABASE_URL:
                    await conn.execute(text(f"ALTER TABLE system_access ADD COLUMN IF NOT EXISTS {col} BIGINT"))
                else:
                    await conn.execute(text(f"ALTER TABLE system_access ADD COLUMN {col} BIGINT"))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Column %s check or migration note: %s", col, exc)

        # Non-destructive migrations for Instagram omnichannel support
        extra_columns = [
            ("users", "instagram_id", "VARCHAR(100)"),
            ("users", "platform", "VARCHAR(50) DEFAULT 'telegram'"),
            ("users", "instagram_username", "VARCHAR(255)"),
            ("inquiries", "channel", "VARCHAR(50) DEFAULT 'telegram'"),
            ("inquiries", "detected_category", "VARCHAR(100)"),
            ("chat_messages", "channel", "VARCHAR(50) DEFAULT 'telegram'"),
            ("chat_messages", "instagram_message_id", "VARCHAR(255)"),
        ]
        for tbl, col, col_def in extra_columns:
            try:
                if "postgres" in settings.DATABASE_URL:
                    await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {col_def}"))
                else:
                    await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}"))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Column %s.%s migration note: %s", tbl, col, exc)

        try:
            if "postgres" in settings.DATABASE_URL:
                await conn.execute(text("ALTER TABLE services ALTER COLUMN price TYPE VARCHAR(100) USING price::text"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Services price column conversion note: %s", exc)

    # Seed if legal chunks empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(LegalChunk.id)))
        count = result.scalar() or 0
        if count == 0:
            logger.info("Knowledge base is empty. Seeding initial legislation...")
            rag = RAGService()
            for item in SEED_LEGAL_ARTICLES:
                try:
                    embedding = await rag.get_embedding(item["chunk_text"])
                except Exception as e:  # noqa: BLE001
                    logger.warning("Could not compute embedding for %s: %s", item["law_title"], e)
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
            logger.info(
                "Successfully seeded %d legal articles into database.",
                len(SEED_LEGAL_ARTICLES),
            )

        # Seed services if empty
        await PaymentService.seed_default_services(session)

        # Seed helplines if empty
        from app.services.helpline_service import HelplineService
        await HelplineService.seed_default_helplines(session)

        # Seed system access (lawyers, groups, admins) if empty
        await AccessService.seed_default_access(session)

        # Synchronize lawyer permissions for all registered active lawyers
        active_lawyer_ids = await AccessService.get_active_lawyer_ids(session)
        for lawyer_tg_id in active_lawyer_ids:
            await UserService.sync_lawyer_status(session, lawyer_tg_id, is_active_lawyer=True)

        # Backfill chat messages from inquiries if empty
        await ChatService.backfill_historical_inquiries(session)


async def main() -> None:
    """Start Telegram bot in polling mode with automatic network reconnect."""
    await init_database()

    setup_bot_dispatcher(dp)

    bot_info = None
    try:
        me = await bot.get_me()
        bot_info = f"@{me.username} (ID: {me.id})"
    except TelegramUnauthorizedError:
        logger.error(
            "❌ Telegram BOT_TOKEN noto'g'ri yoki bekor qilingan (Unauthorized)! "
            "Iltimos, Railway Variables bo'limida yangi BOT_TOKEN ni o'rnating."
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bot ma'lumotlarini yuklashda xatolik: %s", exc)

    logger.info("=" * 60)
    logger.info("🚀 Yurist LegalTech Bot & Web API ishga tushdi!")
    if bot_info:
        logger.info("🤖 Bot Username: %s", bot_info)
    else:
        logger.error("🤖 Bot: Ulanmadi (BOT_TOKEN tekshirilishi kerak)")
    logger.info("🌐 FastAPI Server: http://%s:%d", settings.HOST, settings.PORT)
    logger.info(
        "🧠 AI Modeli: Google %s (Fallback: %s)",
        settings.GEMINI_MODEL,
        settings.GEMINI_FALLBACK_MODEL,
    )
    logger.info("💾 Database URL: %s", settings.DATABASE_URL)
    logger.info("=" * 60)
    logger.info("Telegram'da botingizga /start buyrug'ini yuboring!")

    async def run_fastapi() -> None:
        config = uvicorn.Config(
            app=fastapi_app,
            host=settings.HOST,
            port=settings.PORT,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def run_bot() -> None:
        while True:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                await dp.start_polling(bot)
                break
            except TelegramUnauthorizedError:
                logger.error(
                    "❌ Telegram Unauthorized: BOT_TOKEN xato yoki bekor qilingan! "
                    "Railway Variables'da yangi BOT_TOKEN kiritilishini kutyapti (30s)..."
                )
                await asyncio.sleep(30)
            except TelegramConflictError as conflict_err:
                logger.warning(
                    "Telegram bot conflict (boshqa instansiya ishlamoqda: %s). 5 soniyadan so'ng qayta urinilmoqda...",
                    conflict_err,
                )
                await asyncio.sleep(5)
            except TelegramRetryAfter as retry_err:
                logger.warning("Telegram flood limit: %d soniya kutilmoqda...", retry_err.retry_after)
                await asyncio.sleep(retry_err.retry_after)
            except TelegramNetworkError as net_err:
                logger.warning("Telegram network glitch (%s). Reconnecting in 3s...", net_err)
                await asyncio.sleep(3)
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected error in bot polling (%s). Reconnecting in 5s...", exc)
                await asyncio.sleep(5)

    await asyncio.gather(run_fastapi(), run_bot())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
