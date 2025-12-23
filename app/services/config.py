from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import GuaranteeConfig, LogisticsConfig, Season


async def upsert_logistics(db: AsyncSession, payload: LogisticsConfig) -> LogisticsConfig:
    db.add(payload)
    await db.commit()
    await db.refresh(payload)
    return payload


async def get_logistics(db: AsyncSession) -> LogisticsConfig:
    result = await db.execute(select(LogisticsConfig).order_by(LogisticsConfig.updated_at.desc()))
    current = result.scalars().first()
    if current:
        return current
    config = LogisticsConfig()
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def set_logistics(db: AsyncSession, base_fee: float, hourly_vehicle_fee: float, default_tolls: float, notes: str | None = None) -> LogisticsConfig:
    config = await get_logistics(db)
    config.base_fee = base_fee
    config.hourly_vehicle_fee = hourly_vehicle_fee
    config.default_tolls = default_tolls
    config.notes = notes
    await db.commit()
    await db.refresh(config)
    return config


async def list_seasons(db: AsyncSession):
    result = await db.execute(select(Season).order_by(Season.start_date))
    return result.scalars().all()


async def create_season(db: AsyncSession, payload: Season) -> Season:
    db.add(payload)
    await db.commit()
    await db.refresh(payload)
    return payload


async def get_guarantee(db: AsyncSession) -> GuaranteeConfig:
    result = await db.execute(select(GuaranteeConfig).order_by(GuaranteeConfig.updated_at.desc()))
    instance = result.scalars().first()
    if instance:
        return instance
    instance = GuaranteeConfig()
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


async def set_guarantee(db: AsyncSession, percentage: float, apply_tax: bool, tax_rate: float) -> GuaranteeConfig:
    config = await get_guarantee(db)
    config.percentage = percentage
    config.apply_tax = apply_tax
    config.tax_rate = tax_rate
    await db.commit()
    await db.refresh(config)
    return config
