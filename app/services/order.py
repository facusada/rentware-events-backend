import math
import time
import uuid
from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart
from app.models.config import GuaranteeConfig, LogisticsConfig, Season
from app.models.order import Order, OrderItem, OrderReturn, OrderStatus
from app.models.shared import DeliveryMethod
from app.models.stock import Inventory, StockMovement, StockMovementReason
from app.schemas.order import OrderReturnCreate


def generate_order_code() -> str:
    return f"ORD-{int(time.time() * 1000)}"


def overlaps_high_season(event_start: Optional[date], event_end: Optional[date], seasons: Iterable[Season]) -> Optional[Season]:
    if not event_start or not event_end:
        return None
    for season in seasons:
        if season.start_date <= event_end and event_start <= season.end_date:
            if season.high_season:
                return season
    return None


def calculate_totals(
    cart: Cart,
    logistics_config: LogisticsConfig,
    guarantee_config: GuaranteeConfig,
    seasons: Iterable[Season],
) -> dict[str, Decimal | int | bool]:
    subtotal = Decimal("0")
    guarantee_base = Decimal("0")
    days = 1
    for item in cart.items:
        days = max(days, item.days)
        line_subtotal = Decimal(item.price_per_day) * item.quantity * item.days
        subtotal += line_subtotal
        if item.requires_guarantee:
            guarantee_base += line_subtotal
    logistics_cost = Decimal(logistics_config.base_fee or 0) + Decimal(logistics_config.default_tolls or 0)
    logistics_cost += Decimal(logistics_config.hourly_vehicle_fee or 0) * Decimal(cart.logistics_hours or 1)
    logistics_cost += Decimal(cart.tolls or 0)

    guarantee_amount = guarantee_base * Decimal(guarantee_config.percentage or 0)
    if guarantee_config.apply_tax:
        guarantee_amount *= Decimal(1) + Decimal(guarantee_config.tax_rate or 0)

    season = overlaps_high_season(cart.event_start, cart.event_end, seasons)
    requires_deposit = season is not None
    deposit_ratio = Decimal(season.deposit_ratio) if season else Decimal("0")
    reservation_required = (subtotal + logistics_cost + guarantee_amount) * deposit_ratio if requires_deposit else Decimal("0")
    total = subtotal + logistics_cost + guarantee_amount
    outstanding_balance = total - reservation_required

    return {
        "days": days,
        "subtotal": subtotal.quantize(Decimal("0.01")),
        "logistics_cost": logistics_cost.quantize(Decimal("0.01")),
        "guarantee_amount": guarantee_amount.quantize(Decimal("0.01")),
        "total": total.quantize(Decimal("0.01")),
        "reservation_required": reservation_required.quantize(Decimal("0.01")),
        "outstanding_balance": outstanding_balance.quantize(Decimal("0.01")),
        "requires_guarantee": guarantee_base > 0,
        "high_season": bool(season),
    }


async def get_singleton(db: AsyncSession, model):
    result = await db.execute(select(model).order_by(model.updated_at.desc())) if hasattr(model, "updated_at") else await db.execute(select(model))
    instance = result.scalars().first()
    if instance:
        return instance
    if model is LogisticsConfig:
        instance = LogisticsConfig(base_fee=0, hourly_vehicle_fee=0, default_tolls=0)
    elif model is GuaranteeConfig:
        instance = GuaranteeConfig(percentage=0.15, apply_tax=True, tax_rate=0.21)
    else:
        instance = model()
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


async def create_order_from_cart(db: AsyncSession, cart: Cart) -> Order:
    if "items" in inspect(cart).unloaded:
        result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id))
        cart = result.scalars().first() or cart

    # Idempotence: reuse existing order for this cart
    existing_order = await db.execute(select(Order).where(Order.cart_id == cart.id))
    found = existing_order.scalars().first()
    if found:
        return found

    logistics_config = await get_singleton(db, LogisticsConfig)
    guarantee_config = await get_singleton(db, GuaranteeConfig)
    seasons = (await db.execute(select(Season))).scalars().all()

    totals = calculate_totals(cart, logistics_config, guarantee_config, seasons)
    initial_status = OrderStatus.pending_reservation
    order = Order(
        code=generate_order_code(),
        cart_id=cart.id,
        user_id=cart.user_id,
        delivery_type=cart.delivery_type,
        delivery_address=cart.delivery_address,
        event_start=cart.event_start,
        event_end=cart.event_end,
        days=totals["days"],
        logistics_hours=cart.logistics_hours,
        tolls=cart.tolls,
        subtotal=totals["subtotal"],
        logistics_cost=totals["logistics_cost"],
        guarantee_amount=totals["guarantee_amount"],
        total=totals["total"],
        reservation_required=totals["reservation_required"],
        outstanding_balance=totals["outstanding_balance"],
        requires_guarantee=totals["requires_guarantee"],
        high_season=totals["high_season"],
        status=initial_status,
    )
    # Inicializar la relación para evitar lazy loads en async
    order.items = []
    db.add(order)
    await db.flush()

    for item in cart.items:
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                days=item.days,
                unit_price=item.price_per_day,
                total_price=Decimal(item.price_per_day) * item.quantity * item.days,
                requires_guarantee=item.requires_guarantee,
                units_per_box=item.units_per_box,
            )
        )
    await db.commit()
    await db.refresh(order)
    return order


ALLOWED_TRANSITIONS = {
    OrderStatus.draft: {OrderStatus.pending_reservation, OrderStatus.cancelled},
    OrderStatus.pending_reservation: {OrderStatus.reservation_confirmed, OrderStatus.cancelled},
    OrderStatus.reservation_confirmed: {OrderStatus.ready_for_delivery, OrderStatus.cancelled},
    OrderStatus.ready_for_delivery: {OrderStatus.delivered, OrderStatus.cancelled},
    OrderStatus.delivered: {OrderStatus.returned, OrderStatus.cancelled},
    OrderStatus.returned: set(),
    OrderStatus.cancelled: set(),
}


def ensure_transition(current: OrderStatus, new: OrderStatus):
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Cannot transition from {current} to {new}")


async def update_order_status(db: AsyncSession, order: Order, new_status: OrderStatus) -> Order:
    ensure_transition(order.status, new_status)
    order.status = new_status
    await db.commit()
    await db.refresh(order)
    return order


async def register_return(db: AsyncSession, order: Order, payload: OrderReturnCreate) -> Order:
    report = OrderReturn(order_id=order.id, breakage_cost=payload.breakage_cost, missing_cost=payload.missing_cost, notes=payload.notes)
    db.add(report)
    adjustment = payload.breakage_cost + payload.missing_cost
    if adjustment > 0:
        original_guarantee = Decimal(order.guarantee_amount)
        remaining_guarantee = max(original_guarantee - adjustment, Decimal(0))
        order.guarantee_amount = remaining_guarantee
        if adjustment > original_guarantee:
            order.outstanding_balance = Decimal(order.outstanding_balance) + (adjustment - original_guarantee)
    order.status = OrderStatus.returned
    await db.commit()
    await db.refresh(order)
    return order


async def reserve_stock(db: AsyncSession, order: Order) -> None:
    for item in order.items:
        remaining = item.quantity
        inventories = (await db.execute(select(Inventory).where(Inventory.product_id == item.product_id))).scalars().all()
        if not inventories:
            raise ValueError("No inventory for product")
        for inv in inventories:
            available = inv.available
            take = min(available, remaining)
            inv.available -= take
            inv.reserved += take
            db.add(StockMovement(inventory_id=inv.id, quantity_change=-take, reason=StockMovementReason.reservation, reference=str(order.code)))
            remaining -= take
            if remaining == 0:
                break
        if remaining > 0:
            raise ValueError("Insufficient stock for reservation")
    await db.commit()


async def release_stock(db: AsyncSession, order: Order) -> None:
    for item in order.items:
        inventories = (await db.execute(select(Inventory).where(Inventory.product_id == item.product_id))).scalars().all()
        for inv in inventories:
            inv.available += inv.reserved
            inv.reserved = 0
    await db.commit()
