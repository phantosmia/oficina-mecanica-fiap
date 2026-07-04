"""add service order quote token

Revision ID: 20260704_0002
Revises: 20260704_0001
Create Date: 2026-07-04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260704_0002"
down_revision: str | None = "20260704_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("service_orders", sa.Column("quote_token", sa.String(), nullable=True))
    op.create_index("ix_service_orders_quote_token", "service_orders", ["quote_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_service_orders_quote_token", table_name="service_orders")
    op.drop_column("service_orders", "quote_token")