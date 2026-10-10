"""Services catalog CRUD API for admin panel."""

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.service import Service
from app.db.session import get_db_session

router = APIRouter(prefix="/services", tags=["services"])


class ServiceCreateRequest(BaseModel):
    title_uz: str
    title_ru: str
    description_uz: str | None = None
    description_ru: str | None = None
    price: Decimal
    service_type: str
    is_active: bool = True


class ServiceUpdateRequest(BaseModel):
    title_uz: str | None = None
    title_ru: str | None = None
    description_uz: str | None = None
    description_ru: str | None = None
    price: Decimal | None = None
    service_type: str | None = None
    is_active: bool | None = None


@router.get("")
async def list_services(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    """List all services in the catalog."""
    stmt = select(Service).order_by(Service.price.asc())
    res = await session.execute(stmt)
    services = res.scalars().all()
    return [
        {
            "id": s.id,
            "title_uz": s.title_uz,
            "title_ru": s.title_ru,
            "description_uz": s.description_uz,
            "description_ru": s.description_ru,
            "price": float(s.price),
            "service_type": s.service_type,
            "is_active": s.is_active,
        }
        for s in services
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Create a new legal service."""
    srv = Service(
        title_uz=payload.title_uz,
        title_ru=payload.title_ru,
        description_uz=payload.description_uz,
        description_ru=payload.description_ru,
        price=payload.price,
        service_type=payload.service_type,
        is_active=payload.is_active,
    )
    session.add(srv)
    await session.commit()
    await session.refresh(srv)
    return {"ok": True, "id": srv.id}


@router.put("/{service_id}")
async def update_service(
    service_id: int,
    payload: ServiceUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Update an existing service."""
    stmt = select(Service).where(Service.id == service_id)
    res = await session.execute(stmt)
    srv = res.scalar_one_or_none()
    if not srv:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(srv, field, value)

    await session.commit()
    await session.refresh(srv)
    return {"ok": True, "id": srv.id}


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Deactivate a service (soft delete)."""
    stmt = select(Service).where(Service.id == service_id)
    res = await session.execute(stmt)
    srv = res.scalar_one_or_none()
    if not srv:
        raise HTTPException(status_code=404, detail="Service not found")

    srv.is_active = False
    await session.commit()
    return {"ok": True, "id": srv.id}
