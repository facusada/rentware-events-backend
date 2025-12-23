import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.catalog import Product, ProductVariant
from app.models.shared import DeliveryMethod
from app.schemas.cart import CartItemCreate


def calculate_days(event_start: Optional[date], event_end: Optional[date], fallback: int = 1) -> int:
    if event_start and event_end and event_end >= event_start:
        return (event_end - event_start).days + 1
    return fallback


async def get_cart_by_session(db: AsyncSession, session_token: str) -> Cart | None:
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.session_token == session_token))
    return result.scalars().first()


async def get_cart_by_id(db: AsyncSession, cart_id: uuid.UUID) -> Cart | None:
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id))
    return result.scalars().first()


async def create_cart(db: AsyncSession, session_token: str, user_id: Optional[uuid.UUID] = None) -> Cart:
    cart = Cart(session_token=session_token, user_id=user_id)
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return cart


async def add_item(db: AsyncSession, cart: Cart, payload: CartItemCreate) -> Cart:
    product = await db.get(Product, payload.product_id)
    if not product:
        raise ValueError("Product not found")
    variant = None
    if payload.variant_id:
        variant = await db.get(ProductVariant, payload.variant_id)
    price = variant.price_override if variant and variant.price_override is not None else product.base_price
    item = CartItem(
        cart_id=cart.id,
        product_id=payload.product_id,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
        days=payload.days,
        price_per_day=price,
        requires_guarantee=product.requires_guarantee,
        units_per_box=product.units_per_box,
    )
    db.add(item)
    await db.commit()
    await db.refresh(cart)
    return cart


async def update_item(db: AsyncSession, item: CartItem, quantity: Optional[int] = None, days: Optional[int] = None) -> CartItem:
    if quantity is not None:
        item.quantity = quantity
    if days is not None:
        item.days = days
    await db.commit()
    await db.refresh(item)
    return item


async def merge_carts(db: AsyncSession, user_cart: Cart, guest_cart: Cart) -> Cart:
    # Aseguramos tener los items cargados
    await db.refresh(user_cart, attribute_names=["items"])
    await db.refresh(guest_cart, attribute_names=["items"])
    for guest_item in guest_cart.items:
        existing = next((i for i in user_cart.items if i.product_id == guest_item.product_id and i.variant_id == guest_item.variant_id), None)
        if existing:
            existing.quantity += guest_item.quantity
            existing.days = max(existing.days, guest_item.days)
        else:
            user_cart.items.append(
                CartItem(
                    product_id=guest_item.product_id,
                    variant_id=guest_item.variant_id,
                    quantity=guest_item.quantity,
                    days=guest_item.days,
                    price_per_day=guest_item.price_per_day,
                    requires_guarantee=guest_item.requires_guarantee,
                    units_per_box=guest_item.units_per_box,
                )
            )
    await db.delete(guest_cart)
    await db.commit()
    refreshed = (
        await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == user_cart.id))
    ).scalars().first()
    return refreshed or user_cart
