from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.helpline import Helpline
from app.db.session import get_db_session

router = APIRouter(prefix="/helplines", tags=["helplines"])

class HelplineBase(BaseModel):
    category_uz: str = "Boshqa"
    category_ru: str = "Другие"
    organization_uz: str
    organization_ru: str
    phone_number: str
    description_uz: str | None = None
    description_ru: str | None = None
    order: int = 0
    is_active: bool = True

class HelplineCreate(HelplineBase):
    pass

class HelplineUpdate(HelplineBase):
    pass

class HelplineResponse(HelplineBase):
    id: int
    
    class Config:
        from_attributes = True

@router.get("", response_model=list[HelplineResponse])
async def get_helplines(db: AsyncSession = Depends(get_db_session)) -> Any:  # noqa: B008
    """Get all helplines."""
    stmt = select(Helpline).order_by(Helpline.order.asc(), Helpline.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=HelplineResponse)
async def create_helpline(
    helpline_in: HelplineCreate, db: AsyncSession = Depends(get_db_session)  # noqa: B008
) -> Any:
    """Create new helpline."""
    helpline = Helpline(**helpline_in.model_dump())
    db.add(helpline)
    await db.commit()
    await db.refresh(helpline)
    return helpline

@router.put("/{helpline_id}", response_model=HelplineResponse)
async def update_helpline(
    helpline_id: int, helpline_in: HelplineUpdate, db: AsyncSession = Depends(get_db_session)  # noqa: B008
) -> Any:
    """Update a helpline."""
    helpline = await db.get(Helpline, helpline_id)
    if not helpline:
        raise HTTPException(status_code=404, detail="Helpline not found")
    
    for field, value in helpline_in.model_dump().items():
        setattr(helpline, field, value)
        
    await db.commit()
    await db.refresh(helpline)
    return helpline

@router.delete("/{helpline_id}")
async def delete_helpline(helpline_id: int, db: AsyncSession = Depends(get_db_session)) -> Any:  # noqa: B008
    """Delete a helpline."""
    helpline = await db.get(Helpline, helpline_id)
    if not helpline:
        raise HTTPException(status_code=404, detail="Helpline not found")
    
    await db.delete(helpline)
    await db.commit()
    return {"ok": True}
