import uuid
from decimal import Decimal

import pytest

from app.models.cart import Cart, CartItem
from app.models.catalog import Category, Product
from app.models.config import GuaranteeConfig, LogisticsConfig
from app.services.order import create_order_from_cart


@pytest.mark.asyncio
async def test_checkout_idempotent(session):
    category = Category(name="Test", description="desc")
    session.add(category)
    await session.commit()
    await session.refresh(category)

    product = Product(
        name="Silla", description="Silla plegable", category_id=category.id, base_price=Decimal("50"), units_per_box=10
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)

    # Config defaults
    session.add(LogisticsConfig(base_fee=0, hourly_vehicle_fee=0, default_tolls=0))
    session.add(GuaranteeConfig(percentage=0.0, apply_tax=False, tax_rate=0))
    await session.commit()

    cart = Cart(session_token="testtoken")
    session.add(cart)
    await session.commit()
    await session.refresh(cart)

    item = CartItem(cart_id=cart.id, product_id=product.id, quantity=1, days=2, price_per_day=product.base_price)
    session.add(item)
    await session.commit()
    await session.refresh(cart)

    order1 = await create_order_from_cart(session, cart)
    order2 = await create_order_from_cart(session, cart)

    assert order1.id == order2.id
