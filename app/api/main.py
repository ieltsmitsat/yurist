"""FastAPI main application with lifespan, webhook, and background scheduler."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.chats import router as chats_router
from app.api.v1.crm import router as crm_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.helplines import router as helplines_router
from app.api.v1.instagram import router as instagram_router
from app.api.v1.mandatory_channels import router as channels_router
from app.api.v1.services import router as services_router
from app.api.v1.settings import router as settings_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.webhook import router as webhook_router
from app.bot.bot_instance import bot, dp
from app.bot.main import setup_bot_dispatcher
from app.core.config import settings
from app.core.redis import close_redis_client
from app.core.security import verify_admin_access
from app.db.session import AsyncSessionLocal
from app.services.scheduler_service import RetargetingSchedulerService

logger = logging.getLogger(__name__)

# Initialize background scheduler for lead nurturing
scheduler = AsyncIOScheduler()
retargeting_service = RetargetingSchedulerService()


async def _send_followups(hours: int) -> None:
    """Send follow-up messages to leads needing nurturing at the given hour mark."""
    async with AsyncSessionLocal() as session:
        leads = await retargeting_service.get_leads_needing_followup(session, hours=hours)
        for user, inquiry in leads:
            try:
                msg = await retargeting_service.generate_followup_message(
                    user, inquiry, hours=hours
                )
                await bot.send_message(chat_id=user.telegram_id, text=msg)
                logger.info("Sent %dh nurturing reminder to user %d", hours, user.id)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to send %dh reminder to user %d: %s", hours, user.id, e)


async def run_retargeting_job() -> None:
    """Hourly background job checking for leads needing 24h/48h reminders."""
    logger.info("Running lead nurturing retargeting check...")
    try:
        await _send_followups(24)
        await _send_followups(48)
    except Exception as e:  # noqa: BLE001
        logger.error("Error running retargeting job: %s", e)


async def run_instagram_window_watcher_job() -> None:
    """Quarter-hourly background job monitoring 24h Instagram window expirations and warnings."""
    try:
        from app.core.redis import get_redis_client
        from app.services.instagram.window_watcher import InstagramWindowWatcherService

        redis_client = await get_redis_client()
        async with AsyncSessionLocal() as session:
            count = await InstagramWindowWatcherService.run_window_check(
                session=session,
                redis_client=redis_client,
            )
            if count > 0:
                logger.info("Instagram window watcher sent %d closing warnings", count)
    except Exception as e:  # noqa: BLE001
        logger.error("Error in instagram_window_watcher_job: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing startup and shutdown tasks."""
    logger.info("Starting up Yurist LegalTech AI Platform...")

    # 1. Setup bot dispatcher with all routers
    setup_bot_dispatcher(dp)

    # 2. Setup webhook if URL provided
    if settings.WEBHOOK_URL:
        try:
            await bot.set_webhook(
                url=settings.WEBHOOK_URL,
                secret_token=settings.WEBHOOK_SECRET,
                drop_pending_updates=True,
            )
            logger.info("Configured Telegram webhook at: %s", settings.WEBHOOK_URL)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not set webhook (proceeding in local mode): %s", e)

    # 3. Start background lead nurturing & Instagram window watcher schedulers
    scheduler.add_job(run_retargeting_job, "interval", minutes=60, id="retargeting_job")
    scheduler.add_job(run_instagram_window_watcher_job, "interval", minutes=15, id="ig_window_watcher_job")
    scheduler.start()
    logger.info("Started background APScheduler")

    yield

    logger.info("Shutting down Yurist LegalTech AI Platform...")
    # Shutdown tasks
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await bot.session.close()
    await close_redis_client()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS for admin dashboard (Next.js dev server)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    admin_auth = [Depends(verify_admin_access)]

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(webhook_router, prefix="/api/v1")
    app.include_router(instagram_router, prefix="/api/v1")
    app.include_router(crm_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(dashboard_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(services_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(helplines_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(channels_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(transactions_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(chats_router, prefix="/api/v1", dependencies=admin_auth)
    app.include_router(settings_router, prefix="/api/v1", dependencies=admin_auth)

    return app


app = create_app()
