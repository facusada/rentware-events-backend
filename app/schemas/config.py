import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class LogisticsConfigBase(BaseModel):
    base_fee: Decimal = 0
    hourly_vehicle_fee: Decimal = 0
    default_tolls: Decimal = 0
    notes: str | None = None


class LogisticsConfigCreate(LogisticsConfigBase):
    pass


class LogisticsConfigOut(LogisticsConfigBase):
    id: uuid.UUID
    updated_at: datetime

    model_config = {"from_attributes": True}


class SeasonBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    high_season: bool = False
    deposit_ratio: Decimal = 0.5


class SeasonCreate(SeasonBase):
    pass


class SeasonOut(SeasonBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class GuaranteeConfigBase(BaseModel):
    percentage: Decimal = 0.15
    apply_tax: bool = True
    tax_rate: Decimal = 0.21


class GuaranteeConfigCreate(GuaranteeConfigBase):
    pass


class GuaranteeConfigOut(GuaranteeConfigBase):
    id: uuid.UUID
    updated_at: datetime

    model_config = {"from_attributes": True}
