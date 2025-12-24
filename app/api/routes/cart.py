import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_optional_user, get_session_token
from app.models.cart import Cart, CartItem
from app.models.user import User
from app.schemas.cart import CartCreate, CartItemCreate, CartItemOut, CartItemUpdate, CartOut, CartUpdate
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


async def _resolve_cart(db: AsyncSession, session_token: str | None, user: User | None) -> Cart:
    cart = None
    session_cart = None
    user_cart = None

    if session_token:
        session_cart = await cart_service.get_cart_by_session(db, session_token)
        if session_cart and user and session_cart.user_id is None:
            session_cart.user_id = user.id
            await db.commit()
            await db.refresh(session_cart)

    if user:
        result = await db.execute(select(Cart).options(selectinload(Cart.order)).where(Cart.user_id == user.id))
        user_cart = result.scalars().first()

    if session_cart:
        cart = session_cart
    elif user_cart:
        # Si el carrito del usuario ya generó un pedido y el token de sesión cambió, evita reusarlo
        if user_cart.order and session_token and user_cart.session_token != session_token:
            cart = None
        else:
            cart = user_cart

    if not cart and session_token:
        cart = await cart_service.create_cart(db, session_token, user.id if user else None)

    if not cart and user_cart:
        cart = user_cart

    if not cart:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart not found")

    result = await db.execute(select(Cart).options(selectinload(Cart.items), selectinload(Cart.order)).where(Cart.id == cart.id))
    return result.scalars().unique().first()


@router.get("", response_model=CartOut)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
    user: User | None = Depends(get_optional_user),
):
    cart = await _resolve_cart(db, session_token, user)
    return CartOut.model_validate(cart)


@router.post("", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def create_cart(payload: CartCreate, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    existing = await cart_service.get_cart_by_session(db, payload.session_token)
    if existing:
        resolved = await _resolve_cart(db, payload.session_token, user)
        return CartOut.model_validate(resolved)
    cart = await cart_service.create_cart(db, payload.session_token, user.id if user else None)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if hasattr(cart, field):
            setattr(cart, field, value)
    await db.commit()
    resolved = await _resolve_cart(db, payload.session_token, user)
    return CartOut.model_validate(resolved)


@router.post("/items", response_model=CartOut)
async def add_item(
    payload: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
    user: User | None = Depends(get_optional_user),
):
    cart = await _resolve_cart(db, session_token, user)
    cart = await cart_service.add_item(db, cart, payload)
    refreshed = await _resolve_cart(db, session_token, user)
    return CartOut.model_validate(refreshed)


@router.patch("/items/{item_id}", response_model=CartOut)
async def update_item(
    item_id: uuid.UUID,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
    user: User | None = Depends(get_optional_user),
):
    cart = await _resolve_cart(db, session_token, user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")
    await cart_service.update_item(db, item, payload.quantity, payload.days)
    refreshed = await _resolve_cart(db, session_token, user)
    return CartOut.model_validate(refreshed)


@router.delete("/items/{item_id}", response_model=CartOut)
async def delete_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
    user: User | None = Depends(get_optional_user),
):
    cart = await _resolve_cart(db, session_token, user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await db.delete(item)
    await db.commit()
    refreshed = await _resolve_cart(db, session_token, user)
    return CartOut.model_validate(refreshed)


@router.post("/merge", response_model=CartOut)
async def merge_cart(
    db: AsyncSession = Depends(get_db),
    session_token: str = Depends(get_session_token),
    user: User = Depends(get_current_user),
):
    guest_cart = await cart_service.get_cart_by_session(db, session_token)
    if guest_cart:
        await db.refresh(guest_cart, attribute_names=["items"])
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user.id))
    user_cart = result.scalars().first()
    if guest_cart and user_cart:
        merged = await cart_service.merge_carts(db, user_cart, guest_cart)
        refreshed = await _resolve_cart(db, session_token, user)
        return CartOut.model_validate(refreshed)
    if guest_cart and not user_cart:
        guest_cart.user_id = user.id
        await db.commit()
        refreshed = await _resolve_cart(db, session_token, user)
        return CartOut.model_validate(refreshed)
    if user_cart:
        refreshed = await _resolve_cart(db, session_token, user)
        return CartOut.model_validate(refreshed)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No carts to merge")


@router.patch("", response_model=CartOut)
async def update_cart_details(
    payload: CartUpdate,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
    user: User | None = Depends(get_optional_user),
):
    cart = await _resolve_cart(db, session_token, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cart, field, value)
    await db.commit()
    refreshed = await _resolve_cart(db, session_token, user)
    return CartOut.model_validate(refreshed)
