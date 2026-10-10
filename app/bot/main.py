"""Bot setup and router registration."""

import logging

from aiogram import Dispatcher

from app.bot.handlers.business.messages import router as business_router
from app.bot.handlers.public.audit import router as audit_router
from app.bot.handlers.public.helplines import router as helplines_router
from app.bot.handlers.public.inquiry import router as inquiry_router
from app.bot.handlers.public.referral import router as referral_router
from app.bot.handlers.public.registration import router as registration_router
from app.bot.handlers.public.services import router as services_router
from app.bot.handlers.public.sos import router as sos_router
from app.bot.handlers.public.start import router as start_router
from app.bot.middlewares.db_middleware import DbSessionMiddleware
from app.bot.middlewares.user_middleware import UserContextMiddleware

logger = logging.getLogger(__name__)

_dispatcher_configured: bool = False


def setup_bot_dispatcher(dp: Dispatcher) -> None:
    """Register all middlewares and routers on the Dispatcher idempotently."""
    global _dispatcher_configured
    if _dispatcher_configured:
        return

    # Middlewares
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(UserContextMiddleware())

    # Routers
    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(services_router)
    dp.include_router(referral_router)
    dp.include_router(sos_router)
    dp.include_router(helplines_router)
    dp.include_router(audit_router)
    dp.include_router(inquiry_router)  # inquiry text/voice handlers last to catch generic messages
    dp.include_router(business_router)  # Telegram Business mode

    _dispatcher_configured = True
    logger.info("Successfully registered all bot routers and middlewares")

