import uuid
from decimal import Decimal
from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.models.stock import StockMovementReason
from app.models.shared import DeliveryMethod


class WarehouseCreate(BaseModel):
    name: str
    address: str | None = None


class WarehouseOut(WarehouseCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class InventoryOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    warehouse_id: uuid.UUID
    available: int
    reserved: int

    model_config = {"from_attributes": True}


class StockMovementCreate(BaseModel):
    inventory_id: uuid.UUID
    quantity_change: int
    reason: StockMovementReason = StockMovementReason.manual
    reference: str | None = None
    amount: Decimal | None = None


class StockMovementOut(StockMovementCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class StockMovementWithMeta(BaseModel):
    id: uuid.UUID
    inventory_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    variant_id: uuid.UUID | None
    warehouse_id: uuid.UUID
    warehouse_name: str | None
    quantity_change: int
    reason: StockMovementReason
    reference: str | None = None
    amount: Decimal | None = None
    created_at: datetime
