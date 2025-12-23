import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as PgEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.shared import DeliveryMethod


class OrderStatus(str, Enum):
    draft = "draft"
    pending_reservation = "pending_reservation"
    reservation_confirmed = "reservation_confirmed"
    ready_for_delivery = "ready_for_delivery"
    delivered = "delivered"
    returned = "returned"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("cart_id", name="uq_orders_cart"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    cart_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("carts.id", ondelete="SET NULL"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[OrderStatus] = mapped_column(PgEnum(OrderStatus), default=OrderStatus.draft, index=True)
    delivery_type: Mapped[DeliveryMethod] = mapped_column(PgEnum(DeliveryMethod), default=DeliveryMethod.pickup)
    delivery_address: Mapped[Optional[str]] = mapped_column(String(255))
    delivery_window: Mapped[Optional[str]] = mapped_column(String(100))
    return_window: Mapped[Optional[str]] = mapped_column(String(100))
    event_start: Mapped[Optional[date]] = mapped_column(Date)
    event_end: Mapped[Optional[date]] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer, default=1)
    logistics_hours: Mapped[int] = mapped_column(Integer, default=1)
    tolls: Mapped[int] = mapped_column(Integer, default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    logistics_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    guarantee_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    reservation_required: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    outstanding_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    requires_guarantee: Mapped[bool] = mapped_column(Boolean, default=False)
    high_season: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    cart = relationship("Cart", back_populates="order")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    returns = relationship("OrderReturn", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    days: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    total_price: Mapped[float] = mapped_column(Numeric(12, 2))
    requires_guarantee: Mapped[bool] = mapped_column(Boolean, default=False)
    units_per_box: Mapped[int] = mapped_column(Integer, default=1)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    @property
    def product_name(self) -> str | None:
        return getattr(self.product, "name", None)

    @property
    def variant_label(self) -> str | None:
        if not self.variant:
            return None
        parts: list[str] = []
        if getattr(self.variant, "color", None):
            parts.append(self.variant.color)
        if getattr(self.variant, "material", None):
            parts.append(self.variant.material)
        return " · ".join(parts) if parts else None


class OrderReturn(Base):
    __tablename__ = "order_returns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"))
    breakage_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    missing_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    order = relationship("Order", back_populates="returns")
