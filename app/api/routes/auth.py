from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User, UserRole
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, Token
from app.schemas.user import UserCreate, UserOut
from app.services.auth import authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=AuthResponse)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = await create_user(db, payload.email, payload.password, payload.full_name, UserRole.client)
    token = Token(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return AuthResponse(user=UserOut.model_validate(user), token=token, issued_at=datetime.now(timezone.utc))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = Token(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return AuthResponse(user=UserOut.model_validate(user), token=token, issued_at=datetime.now(timezone.utc))


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest):
    try:
        data = jwt.decode(payload.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a refresh token")
    new_access = create_access_token(data.get("sub"), data.get("role", "client"))
    new_refresh = create_refresh_token(data.get("sub"))
    return Token(access_token=new_access, refresh_token=new_refresh)
