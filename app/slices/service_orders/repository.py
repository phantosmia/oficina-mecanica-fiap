from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.shared.models import CatalogService, Client, Part, ServiceOrder, ServiceOrderPart, ServiceOrderService, Vehicle

def get_order_or_404(session: Session, order_id: int) -> ServiceOrder:
    statement = (
        select(ServiceOrder)
        .options(
            joinedload(ServiceOrder.client),
            joinedload(ServiceOrder.vehicle),
            selectinload(ServiceOrder.service_items).joinedload(ServiceOrderService.service),
            selectinload(ServiceOrder.part_items).joinedload(ServiceOrderPart.part),
        )
        .where(ServiceOrder.id == order_id)
    )
    order = session.execute(statement).unique().scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada.")

    return order


def list_orders(session: Session) -> list[ServiceOrder]:
    statement = (
        select(ServiceOrder)
        .options(joinedload(ServiceOrder.client), joinedload(ServiceOrder.vehicle))
        .order_by(ServiceOrder.id.desc())
    )
    return list(session.scalars(statement).all())


def find_client_by_document(session: Session, document_number: str) -> Client | None:
    return session.scalar(select(Client).where(Client.document_number == document_number))


def find_vehicle_by_plate(session: Session, plate: str) -> Vehicle | None:
    return session.scalar(select(Vehicle).where(Vehicle.license_plate == plate))


def find_catalog_service(session: Session, service_id: int) -> CatalogService | None:
    return session.scalar(select(CatalogService).where(CatalogService.id == service_id, CatalogService.active.is_(True)))


def find_part(session: Session, part_id: int) -> Part | None:
    return session.get(Part, part_id)


def fetch_tracking(session: Session, order_id: int, document_number: str) -> ServiceOrder:
    statement = (
        select(ServiceOrder)
        .options(joinedload(ServiceOrder.client), joinedload(ServiceOrder.vehicle))
        .join(ServiceOrder.client)
        .where(ServiceOrder.id == order_id, Client.document_number == document_number)
    )
    order = session.scalars(statement).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada para o documento informado.")

    return order


def fetch_average_execution_time(session: Session) -> dict[str, float | int]:
    average_expression = (func.julianday(ServiceOrder.finished_at) - func.julianday(ServiceOrder.started_at)) * 24 * 60
    finished_orders = session.scalar(
        select(func.count(ServiceOrder.id)).where(ServiceOrder.started_at.is_not(None), ServiceOrder.finished_at.is_not(None))
    ) or 0
    average_minutes = session.scalar(
        select(func.coalesce(func.avg(average_expression), 0)).where(
            ServiceOrder.started_at.is_not(None),
            ServiceOrder.finished_at.is_not(None),
        )
    ) or 0
    return {"finished_orders": int(finished_orders), "average_minutes": round(float(average_minutes), 2)}
