import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.models.shared import DeliveryMethod


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str | None = None
    variant_id: uuid.UUID | None
    variant_label: str | None = None
    quantity: int
    days: int
    unit_price: Decimal
    total_price: Decimal
    requires_guarantee: bool
    units_per_box: int

    model_config = {"from_attributes": True}


class OrderBase(BaseModel):
    delivery_type: DeliveryMethod
    delivery_address: str | None = None
    delivery_window: str | None = None
    return_window: str | None = None
    event_start: date | None = None
    event_end: date | None = None
    logistics_hours: int = 1
    tolls: int = 0
    notes: str | None = None


class OrderOut(OrderBase):
    id: uuid.UUID
    code: str
    status: OrderStatus
    days: int
    subtotal: Decimal
    logistics_cost: Decimal
    guarantee_amount: Decimal
    total: Decimal
    reservation_required: Decimal
    outstanding_balance: Decimal
    requires_guarantee: bool
    high_season: bool
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class CheckoutRequest(BaseModel):
    cart_id: uuid.UUID | None = None
    session_token: str | None = None


class OrderReturnCreate(BaseModel):
    breakage_cost: Decimal = Field(0, ge=0)
    missing_cost: Decimal = Field(0, ge=0)
    notes: str | None = None
