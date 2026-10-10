"""Dashboard analytics and statistics API for admin panel."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inquiry import Inquiry
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.db.session import get_db_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Aggregate dashboard statistics for admin overview cards."""
    # Total users
    res_users = await session.execute(select(func.count(User.id)))
    total_users = res_users.scalar() or 0

    # Total inquiries
    res_inq = await session.execute(select(func.count(Inquiry.id)))
    total_inquiries = res_inq.scalar() or 0

    # Total revenue (completed transactions)
    res_rev = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.payment_status == "completed"
        )
    )
    total_revenue = float(res_rev.scalar() or 0)

    # Pending transactions
    res_pending = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.payment_status == "pending"
        )
    )
    pending_payments = res_pending.scalar() or 0

    # Users today
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    res_today = await session.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    users_today = res_today.scalar() or 0

    # Inquiries today
    res_inq_today = await session.execute(
        select(func.count(Inquiry.id)).where(Inquiry.created_at >= today_start)
    )
    inquiries_today = res_inq_today.scalar() or 0

    # Referral users (who were referred)
    res_ref = await session.execute(
        select(func.count(User.id)).where(User.referred_by_id.is_not(None))
    )
    referred_users = res_ref.scalar() or 0

    # Subscribers
    res_subs = await session.execute(
        select(func.count(User.id)).where(User.is_subscribed.is_(True))
    )
    subscribers = res_subs.scalar() or 0

    return {
        "total_users": total_users,
        "users_today": users_today,
        "total_inquiries": total_inquiries,
        "inquiries_today": inquiries_today,
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,
        "referred_users": referred_users,
        "subscribers": subscribers,
    }


@router.get("/pipeline")
async def get_lead_pipeline(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    """CRM pipeline: count of users in each lead_status stage."""
    stmt = (
        select(User.lead_status, func.count(User.id).label("count"))
        .group_by(User.lead_status)
        .order_by(func.count(User.id).desc())
    )
    res = await session.execute(stmt)
    rows = res.all()
    return [{"status": row[0], "count": row[1]} for row in rows]


@router.get("/risk-breakdown")
async def get_risk_breakdown(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    """Breakdown of inquiries by risk level."""
    stmt = (
        select(
            func.coalesce(Inquiry.risk_level, "unrated").label("level"),
            func.count(Inquiry.id).label("count"),
        )
        .group_by(Inquiry.risk_level)
        .order_by(func.count(Inquiry.id).desc())
    )
    res = await session.execute(stmt)
    rows = res.all()
    return [{"level": row[0], "count": row[1]} for row in rows]


@router.get("/users-chart")
async def get_users_chart(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = 30,
) -> list[dict[str, Any]]:
    """Daily new user registrations for chart."""
    since = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    res = await session.execute(stmt)
    rows = res.all()
    return [{"date": str(row[0]), "count": row[1]} for row in rows]


@router.get("/inquiries-chart")
async def get_inquiries_chart(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = 30,
) -> list[dict[str, Any]]:
    """Daily inquiry volume for chart."""
    since = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(
            func.date(Inquiry.created_at).label("date"),
            func.count(Inquiry.id).label("count"),
        )
        .where(Inquiry.created_at >= since)
        .group_by(func.date(Inquiry.created_at))
        .order_by(func.date(Inquiry.created_at))
    )
    res = await session.execute(stmt)
    rows = res.all()
    return [{"date": str(row[0]), "count": row[1]} for row in rows]


@router.get("/revenue-chart")
async def get_revenue_chart(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = 30,
) -> list[dict[str, Any]]:
    """Daily revenue from completed transactions for chart."""
    since = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(
            func.date(Transaction.created_at).label("date"),
            func.coalesce(func.sum(Transaction.amount), 0).label("revenue"),
        )
        .where(Transaction.payment_status == "completed")
        .where(Transaction.created_at >= since)
        .group_by(func.date(Transaction.created_at))
        .order_by(func.date(Transaction.created_at))
    )
    res = await session.execute(stmt)
    rows = res.all()
    return [{"date": str(row[0]), "revenue": float(row[1])} for row in rows]


@router.get("/referral-stats")
async def get_referral_analytics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Referral program analytics."""
    # Total referred
    res_total = await session.execute(
        select(func.count(User.id)).where(User.referred_by_id.is_not(None))
    )
    total_referred = res_total.scalar() or 0

    # Verified referrals (with phone)
    res_verified = await session.execute(
        select(func.count(User.id)).where(
            User.referred_by_id.is_not(None),
            User.phone_number.is_not(None),
        )
    )
    verified = res_verified.scalar() or 0

    # Top referrers
    stmt_top = (
        select(
            User.referred_by_id,
            func.count(User.id).label("referral_count"),
        )
        .where(User.referred_by_id.is_not(None))
        .group_by(User.referred_by_id)
        .order_by(func.count(User.id).desc())
        .limit(10)
    )
    res_top = await session.execute(stmt_top)
    top_rows = res_top.all()

    top_referrers = []
    for row in top_rows:
        referrer_res = await session.execute(
            select(User.full_name, User.telegram_id).where(User.id == row[0])
        )
        referrer_data = referrer_res.first()
        if referrer_data:
            top_referrers.append({
                "full_name": referrer_data[0] or "Unknown",
                "telegram_id": referrer_data[1],
                "referral_count": row[1],
            })

    # Conversion rate
    conversion_rate = (verified / total_referred * 100) if total_referred > 0 else 0

    return {
        "total_referred": total_referred,
        "verified_referred": verified,
        "conversion_rate": round(conversion_rate, 1),
        "top_referrers": top_referrers,
    }
