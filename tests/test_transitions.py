from decimal import Decimal

import pytest

from app.models.order import Order, OrderStatus
from app.services.order import update_order_status


@pytest.mark.asyncio
async def test_order_state_transitions(session):
    order = Order(code="ORD-1", subtotal=Decimal("100"), total=Decimal("100"))
    session.add(order)
    await session.commit()
    await session.refresh(order)

    updated = await update_order_status(session, order, OrderStatus.pending_reservation)
    assert updated.status == OrderStatus.pending_reservation

    with pytest.raises(ValueError):
        await update_order_status(session, updated, OrderStatus.returned)

    updated = await update_order_status(session, updated, OrderStatus.reservation_confirmed)
    assert updated.status == OrderStatus.reservation_confirmed
