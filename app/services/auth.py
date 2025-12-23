from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(
    db: AsyncSession, email: str, password: str, full_name: str | None = None, role: UserRole = UserRole.client
) -> User:
    user = User(email=email, hashed_password=get_password_hash(password), full_name=full_name or email, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
