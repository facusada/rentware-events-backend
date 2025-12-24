"""Change photo_url to Text to allow data URLs

Revision ID: 0002_photo_url_text
Revises: 0001_initial
Create Date: 2025-12-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_photo_url_text"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
  # Allow larger payloads (e.g., data URLs) for product photo
  with op.batch_alter_table("products") as batch_op:
    batch_op.alter_column("photo_url", type_=sa.Text(), existing_type=sa.String(length=255))


def downgrade() -> None:
  with op.batch_alter_table("products") as batch_op:
    batch_op.alter_column("photo_url", type_=sa.String(length=255), existing_type=sa.Text())
