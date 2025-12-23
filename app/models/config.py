import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LogisticsConfig(Base):
    __tablename__ = "logistics_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    hourly_vehicle_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    default_tolls: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    notes: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date]
    end_date: Mapped[date]
    high_season: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_ratio: Mapped[float] = mapped_column(Numeric(5, 2), default=0.5)


class GuaranteeConfig(Base):
    __tablename__ = "guarantee_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.15)
    apply_tax: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_rate: Mapped[float] = mapped_column(Numeric(4, 2), default=0.21)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
