import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_operator_or_admin
from app.models.cart import Cart
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import CheckoutRequest, OrderOut, OrderReturnCreate, OrderStatusUpdate
from app.services.order import create_order_from_cart, register_return, reserve_stock, update_order_status

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_load_options():
    items = selectinload(Order.items)
    return (
        items.selectinload(OrderItem.product),
        items.selectinload(OrderItem.variant),
    )


async def _get_order_or_404(db: AsyncSession, order_id: uuid.UUID) -> Order:
    result = await db.execute(select(Order).options(*_order_load_options()).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get("/", response_model=list[OrderOut])
async def list_orders(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Order).options(*_order_load_options())
    if user.role == UserRole.client:
        query = query.where(Order.user_id == user.id)
    result = await db.execute(query.order_by(Order.created_at.desc()))
    orders = result.scalars().unique().all()
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    order = await _get_order_or_404(db, order_id)
    if user.role == UserRole.client and order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return OrderOut.model_validate(order)


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def checkout(payload: CheckoutRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    cart: Cart | None = None
    if payload.cart_id:
        result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == payload.cart_id))
        cart = result.scalars().first()
    elif payload.session_token:
        result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.session_token == payload.session_token))
        cart = result.scalars().first()
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    if cart.user_id and cart.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cart belongs to another user")
    if cart.user_id is None:
        cart.user_id = user.id
    order = await create_order_from_cart(db, cart)
    order = await _get_order_or_404(db, order.id)
    return OrderOut.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderOut)
async def change_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_operator_or_admin),
):
    order = await _get_order_or_404(db, order_id)
    try:
        updated = await update_order_status(db, order, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    updated = await _get_order_or_404(db, updated.id)
    return OrderOut.model_validate(updated)


@router.post("/{order_id}/confirm-reservation", response_model=OrderOut)
async def confirm_reservation(order_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_operator_or_admin)):
    order = await _get_order_or_404(db, order_id)
    try:
        await reserve_stock(db, order)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    try:
        updated = await update_order_status(db, order, OrderStatus.reservation_confirmed)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    updated = await _get_order_or_404(db, updated.id)
    return OrderOut.model_validate(updated)


@router.post("/{order_id}/return", response_model=OrderOut)
async def register_order_return(
    order_id: uuid.UUID,
    payload: OrderReturnCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_operator_or_admin),
):
    order = await _get_order_or_404(db, order_id)
    order = await register_return(db, order, payload)
    order = await _get_order_or_404(db, order.id)
    return OrderOut.model_validate(order)
