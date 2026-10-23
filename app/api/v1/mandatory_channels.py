from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mandatory_channel import MandatoryChannel
from app.db.session import get_db_session

router = APIRouter(prefix="/channels", tags=["mandatory-channels"])


class MandatoryChannelBase(BaseModel):
    title: str
    chat_id: str
    url: str
    order: int = 0
    is_active: bool = True


class MandatoryChannelCreate(MandatoryChannelBase):
    pass


class MandatoryChannelUpdate(BaseModel):
    title: str | None = None
    chat_id: str | None = None
    url: str | None = None
    order: int | None = None
    is_active: bool | None = None


class MandatoryChannelResponse(MandatoryChannelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


@router.get("", response_model=list[MandatoryChannelResponse])
async def get_mandatory_channels(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Get all mandatory subscription channels and groups."""
    stmt = select(MandatoryChannel).order_by(MandatoryChannel.order.asc(), MandatoryChannel.id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=MandatoryChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_mandatory_channel(
    channel_in: MandatoryChannelCreate,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Create a new mandatory subscription channel or group."""
    channel = MandatoryChannel(**channel_in.model_dump())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.put("/{channel_id}", response_model=MandatoryChannelResponse)
async def update_mandatory_channel(
    channel_id: int,
    channel_in: MandatoryChannelUpdate,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Update an existing mandatory subscription channel."""
    stmt = select(MandatoryChannel).where(MandatoryChannel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    update_data = channel_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(channel, field, val)

    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}")
async def delete_mandatory_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Delete a mandatory subscription channel."""
    stmt = select(MandatoryChannel).where(MandatoryChannel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    await db.delete(channel)
    await db.commit()
    return {"ok": True}


@router.patch("/{channel_id}/toggle", response_model=MandatoryChannelResponse)
async def toggle_mandatory_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Any:
    """Toggle active/inactive status of a mandatory channel."""
    stmt = select(MandatoryChannel).where(MandatoryChannel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    channel.is_active = not channel.is_active
    await db.commit()
    await db.refresh(channel)
    return channel
