"""add client status

Revision ID: 20260815_0003
Revises: 20260704_0002
Create Date: 2026-08-15
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260815_0003"
down_revision: str | None = "20260704_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("status", sa.String(), nullable=False, server_default="ativo"),
    )


def downgrade() -> None:
    op.drop_column("clients", "status")
