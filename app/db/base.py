from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models here so Alembic can autogenerate metadata
from app.models import (  # noqa: E402,F401
    cart,
    catalog,
    config as config_models,
    order,
    stock,
    user,
)
