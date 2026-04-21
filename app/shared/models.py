from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, func
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


class CatalogService(Base, TimestampMixin):
    __tablename__ = "services_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    service_order_items: Mapped[list["ServiceOrderService"]] = relationship(back_populates="service")


class Part(Base, TimestampMixin):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    min_stock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    service_order_items: Mapped[list["ServiceOrderPart"]] = relationship(back_populates="part")


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
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped[Client] = relationship(back_populates="service_orders")
    vehicle: Mapped[Vehicle] = relationship(back_populates="service_orders")
    service_items: Mapped[list["ServiceOrderService"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
    )
    part_items: Mapped[list["ServiceOrderPart"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
    )


class ServiceOrderService(Base):
    __tablename__ = "service_order_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services_catalog.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    service_order: Mapped[ServiceOrder] = relationship(back_populates="service_items")
    service: Mapped[CatalogService] = relationship(back_populates="service_order_items")


class ServiceOrderPart(Base):
    __tablename__ = "service_order_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    service_order: Mapped[ServiceOrder] = relationship(back_populates="part_items")
    part: Mapped[Part] = relationship(back_populates="service_order_items")