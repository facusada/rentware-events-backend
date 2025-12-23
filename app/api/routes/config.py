import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_operator_or_admin
from app.models.config import GuaranteeConfig, LogisticsConfig, Season
from app.schemas.config import (
    GuaranteeConfigCreate,
    GuaranteeConfigOut,
    LogisticsConfigCreate,
    LogisticsConfigOut,
    SeasonCreate,
    SeasonOut,
)
from app.services import config as config_service

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/logistics", response_model=LogisticsConfigOut)
async def get_logistics(db: AsyncSession = Depends(get_db)):
    config = await config_service.get_logistics(db)
    return LogisticsConfigOut.model_validate(config)


@router.put("/logistics", response_model=LogisticsConfigOut)
async def update_logistics(payload: LogisticsConfigCreate, db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    config = await config_service.get_logistics(db)
    config.base_fee = payload.base_fee
    config.hourly_vehicle_fee = payload.hourly_vehicle_fee
    config.default_tolls = payload.default_tolls
    config.notes = payload.notes
    await db.commit()
    await db.refresh(config)
    return LogisticsConfigOut.model_validate(config)


@router.get("/seasons", response_model=list[SeasonOut])
async def get_seasons(db: AsyncSession = Depends(get_db)):
    seasons = await config_service.list_seasons(db)
    return [SeasonOut.model_validate(s) for s in seasons]


@router.post("/seasons", response_model=SeasonOut, status_code=status.HTTP_201_CREATED)
async def create_season(payload: SeasonCreate, db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    season = Season(**payload.model_dump())
    db.add(season)
    await db.commit()
    await db.refresh(season)
    return SeasonOut.model_validate(season)


@router.get("/guarantee", response_model=GuaranteeConfigOut)
async def get_guarantee(db: AsyncSession = Depends(get_db)):
    config = await config_service.get_guarantee(db)
    return GuaranteeConfigOut.model_validate(config)


@router.put("/guarantee", response_model=GuaranteeConfigOut)
async def update_guarantee(payload: GuaranteeConfigCreate, db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    config = await config_service.get_guarantee(db)
    config.percentage = payload.percentage
    config.apply_tax = payload.apply_tax
    config.tax_rate = payload.tax_rate
    await db.commit()
    await db.refresh(config)
    return GuaranteeConfigOut.model_validate(config)
