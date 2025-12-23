"""Initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    userrole = sa.Enum("admin", "operator", "client", name="userrole")
    orderstatus = sa.Enum(
        "draft",
        "pending_reservation",
        "reservation_confirmed",
        "ready_for_delivery",
        "delivered",
        "returned",
        "cancelled",
        name="orderstatus",
    )
    deliverymethod = sa.Enum("delivery", "pickup", name="deliverymethod")
    movementreason = sa.Enum("manual", "sale", "reservation", "return_in", "adjustment", name="stockmovementreason")

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id")),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("requires_guarantee", sa.Boolean(), default=False),
        sa.Column("units_per_box", sa.Integer(), default=1),
        sa.Column("piece_type", sa.String(length=100)),
        sa.Column("condition_status", sa.String(length=100)),
        sa.Column("photo_url", sa.String(length=255)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE")),
        sa.Column("color", sa.String(length=100)),
        sa.Column("material", sa.String(length=100)),
        sa.Column("price_override", sa.Numeric(10, 2)),
    )

    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE")),
        sa.Column("url", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "product_tags",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False, unique=True),
        sa.Column("address", sa.String(length=255)),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", userrole, nullable=False, server_default="client"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "logistics_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base_fee", sa.Numeric(10, 2), server_default="0"),
        sa.Column("hourly_vehicle_fee", sa.Numeric(10, 2), server_default="0"),
        sa.Column("default_tolls", sa.Numeric(10, 2), server_default="0"),
        sa.Column("notes", sa.String(length=255)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("high_season", sa.Boolean(), server_default=sa.false()),
        sa.Column("deposit_ratio", sa.Numeric(5, 2), server_default="0.5"),
    )

    op.create_table(
        "guarantee_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("percentage", sa.Numeric(5, 2), server_default="0.15"),
        sa.Column("apply_tax", sa.Boolean(), server_default=sa.true()),
        sa.Column("tax_rate", sa.Numeric(4, 2), server_default="0.21"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "inventories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE")),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL")),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE")),
        sa.Column("available", sa.Integer(), server_default="0"),
        sa.Column("reserved", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_token", sa.String(length=64), index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("delivery_type", deliverymethod, server_default="pickup"),
        sa.Column("delivery_address", sa.String(length=255)),
        sa.Column("event_start", sa.Date()),
        sa.Column("event_end", sa.Date()),
        sa.Column("logistics_hours", sa.Integer(), server_default="1"),
        sa.Column("tolls", sa.Integer(), server_default="0"),
        sa.Column("notes", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("carts.id", ondelete="CASCADE")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE")),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL")),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("days", sa.Integer(), server_default="1"),
        sa.Column("price_per_day", sa.Numeric(10, 2)),
        sa.Column("requires_guarantee", sa.Boolean(), server_default=sa.false()),
        sa.Column("units_per_box", sa.Integer(), server_default="1"),
    )

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=20), unique=True, index=True),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("carts.id", ondelete="SET NULL")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", orderstatus, server_default="draft", index=True),
        sa.Column("delivery_type", deliverymethod, server_default="pickup"),
        sa.Column("delivery_address", sa.String(length=255)),
        sa.Column("delivery_window", sa.String(length=100)),
        sa.Column("return_window", sa.String(length=100)),
        sa.Column("event_start", sa.Date()),
        sa.Column("event_end", sa.Date()),
        sa.Column("days", sa.Integer(), server_default="1"),
        sa.Column("logistics_hours", sa.Integer(), server_default="1"),
        sa.Column("tolls", sa.Integer(), server_default="0"),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"),
        sa.Column("logistics_cost", sa.Numeric(12, 2), server_default="0"),
        sa.Column("guarantee_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("reservation_required", sa.Numeric(12, 2), server_default="0"),
        sa.Column("outstanding_balance", sa.Numeric(12, 2), server_default="0"),
        sa.Column("requires_guarantee", sa.Boolean(), server_default=sa.false()),
        sa.Column("high_season", sa.Boolean(), server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cart_id", name="uq_orders_cart"),
    )

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE")),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL")),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("days", sa.Integer(), server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2)),
        sa.Column("total_price", sa.Numeric(12, 2)),
        sa.Column("requires_guarantee", sa.Boolean(), server_default=sa.false()),
        sa.Column("units_per_box", sa.Integer(), server_default="1"),
    )

    op.create_table(
        "order_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("breakage_cost", sa.Numeric(10, 2), server_default="0"),
        sa.Column("missing_cost", sa.Numeric(10, 2), server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="CASCADE")),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("reason", movementreason, server_default="manual"),
        sa.Column("reference", sa.String(length=100)),
        sa.Column("amount", sa.Numeric(10, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("order_returns")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("inventories")
    op.drop_table("guarantee_config")
    op.drop_table("seasons")
    op.drop_table("logistics_config")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("warehouses")
    op.drop_table("product_tags")
    op.drop_table("product_images")
    op.drop_table("product_variants")
    op.drop_table("products")
    op.drop_table("tags")
    op.drop_table("categories")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="orderstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="deliverymethod").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="stockmovementreason").drop(op.get_bind(), checkfirst=True)
