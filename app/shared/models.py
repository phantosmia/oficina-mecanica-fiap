from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[str | None] = mapped_column(String, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ativo")

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    service_orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    license_plate: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    client: Mapped[Client] = relationship(back_populates="vehicles")
    service_orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")


class ServiceOrder(Base, TimestampMixin):
    __tablename__ = "service_orders"
    __table_args__ = (
        Index("idx_service_orders_status", "status"),
        Index("idx_service_orders_client_id", "client_id"),
        Index("idx_service_orders_vehicle_id", "vehicle_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    problem_description: Mapped[str] = mapped_column(String, nullable=False)
    diagnosis_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    labor_total: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    parts_total: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    quote_total: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    quote_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped[Client] = relationship(back_populates="service_orders")
    vehicle: Mapped[Vehicle] = relationship(back_populates="service_orders")
    items: Mapped[list["ServiceOrderItem"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceOrderItem.id",
    )
    status_history: Mapped[list["ServiceOrderStatusHistory"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceOrderStatusHistory.id",
    )


class ServiceOrderItem(Base):
    """Serviço ou peça da OS, copiado do diagnóstico (Execução, que copiou os
    preços do Catálogo). Sem chave estrangeira: catálogo e peças agora vivem
    em outros microsserviços (RFC-0006); o snapshot é o que vale para a OS."""

    __tablename__ = "service_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # "servico" ou "peca"
    item_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    service_order: Mapped[ServiceOrder] = relationship(back_populates="items")


class ServiceOrderStatusHistory(Base):
    """Cada mudança de status da OS, com o motivo (evento da saga ou ação do admin)."""

    __tablename__ = "service_order_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    service_order: Mapped[ServiceOrder] = relationship(back_populates="status_history")


class Saga(Base):
    """Estado da saga de uma OS (ADR-0008): gravado na mesma transação que o
    status da OS, o histórico e os comandos na outbox."""

    __tablename__ = "sagas"
    __table_args__ = (Index("idx_sagas_deadline", "deadline_at", postgresql_where="deadline_at IS NOT NULL"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    # Dados acumulados ao longo da saga (cliente, diagnóstico, orçamento, cobrança...).
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    # Compensações ainda por fazer, na ordem; a primeira é a que está em andamento.
    pending_compensations: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    final_status: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # Último comando enviado, para reenvio quando o prazo de resposta vence.
    last_command: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessedMessage(Base):
    """Idempotência (docs/saga.md): `message_id` de todo evento já tratado."""

    __tablename__ = "processed_messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    message_type: Mapped[str] = mapped_column(String, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutboxMessage(Base):
    """*Transactional outbox* (RFC-0007). Aqui as mensagens são comandos para
    a fila SQS de um participante (`destination`), não eventos num tópico."""

    __tablename__ = "outbox_messages"
    __table_args__ = (Index("idx_outbox_messages_pending", "id", postgresql_where="published_at IS NULL"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    message_type: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trace_headers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
