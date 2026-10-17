"""OS Service da Fase 4: orquestrador da saga

Catálogo e peças saem deste banco (agora são os microsserviços de Catálogo e
Estoque, RFC-0006); os itens da OS passam a ser uma cópia do diagnóstico
(ADR-0010), sem chave estrangeira. Entram o estado da saga (ADR-0008), o
histórico de status, a idempotência e a outbox (RFC-0007). O token do
orçamento sai (agora é do serviço de Orçamento, RFC-0008).

Revision ID: 20261010_0004
Revises: 20260815_0003
Create Date: 2026-10-10
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261010_0004"
down_revision: str | None = "20260815_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("service_order_services")
    op.drop_table("service_order_parts")
    op.drop_table("services_catalog")
    op.drop_table("parts")

    op.drop_index("ix_service_orders_quote_token", table_name="service_orders")
    op.drop_column("service_orders", "quote_token")
    op.add_column("service_orders", sa.Column("paid_at", sa.DateTime(), nullable=True))
    op.add_column("service_orders", sa.Column("cancelled_at", sa.DateTime(), nullable=True))

    op.create_table(
        "service_order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_order_items_service_order_id", "service_order_items", ["service_order_id"])

    op.create_table(
        "service_order_status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=True),
        sa.Column("to_status", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_order_status_history_service_order_id", "service_order_status_history", ["service_order_id"])

    op.create_table(
        "sagas",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("pending_compensations", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("final_status", sa.String(), nullable=True),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("last_command", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["service_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("idx_sagas_deadline", "sagas", ["deadline_at"], postgresql_where="deadline_at IS NOT NULL")

    op.create_table(
        "processed_messages",
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("message_type", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("message_type", sa.String(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("envelope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace_headers", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index("idx_outbox_messages_pending", "outbox_messages", ["id"], postgresql_where="published_at IS NULL")


def downgrade() -> None:
    op.drop_index("idx_outbox_messages_pending", table_name="outbox_messages", postgresql_where="published_at IS NULL")
    op.drop_table("outbox_messages")
    op.drop_table("processed_messages")
    op.drop_index("idx_sagas_deadline", table_name="sagas", postgresql_where="deadline_at IS NOT NULL")
    op.drop_table("sagas")
    op.drop_index("ix_service_order_status_history_service_order_id", table_name="service_order_status_history")
    op.drop_table("service_order_status_history")
    op.drop_index("ix_service_order_items_service_order_id", table_name="service_order_items")
    op.drop_table("service_order_items")

    op.drop_column("service_orders", "cancelled_at")
    op.drop_column("service_orders", "paid_at")
    op.add_column("service_orders", sa.Column("quote_token", sa.String(), nullable=True))
    op.create_index("ix_service_orders_quote_token", "service_orders", ["quote_token"], unique=True)

    # Recria catálogo, peças e itens exatamente como no baseline (20260704_0001).
    op.create_table(
        "parts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("min_stock_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_table(
        "services_catalog",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("base_price", sa.Float(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "service_order_parts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "service_order_services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services_catalog.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
