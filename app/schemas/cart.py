import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.shared import DeliveryMethod
from app.models.order import OrderStatus


class CartBase(BaseModel):
    delivery_type: DeliveryMethod = DeliveryMethod.pickup
    delivery_address: str | None = None
    event_start: date | None = None
    event_end: date | None = None
    logistics_hours: int = 1
    tolls: int = 0
    notes: str | None = None


class CartCreate(CartBase):
    session_token: str


class CartUpdate(CartBase):
    pass


class CartItemBase(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(1, gt=0)
    days: int = Field(1, gt=0)


class CartItemCreate(CartItemBase):
    price_per_day: Decimal
    requires_guarantee: bool = False
    units_per_box: int = 1


class CartItemUpdate(BaseModel):
    quantity: int | None = None
    days: int | None = None


class CartItemOut(CartItemBase):
    id: uuid.UUID
    price_per_day: Decimal
    requires_guarantee: bool
    units_per_box: int

    model_config = {"from_attributes": True}


class CartOut(CartBase):
    id: uuid.UUID
    session_token: str
    items: List[CartItemOut] = []
    order_id: uuid.UUID | None = None
    order_status: OrderStatus | None = None

    model_config = {"from_attributes": True}
