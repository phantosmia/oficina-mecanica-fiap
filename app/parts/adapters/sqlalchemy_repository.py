from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.shared.models import Part as PartORM
from app.parts.domain.entity import PartEntity
from app.parts.domain.repository import IPartRepository


def _to_entity(orm: PartORM) -> PartEntity:
    return PartEntity(
        id=orm.id,
        name=orm.name,
        sku=orm.sku,
        description=orm.description,
        unit_price=orm.unit_price,
        stock_quantity=orm.stock_quantity,
        min_stock_level=orm.min_stock_level,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SqlAlchemyPartRepository(IPartRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[PartEntity]:
        return [_to_entity(p) for p in self._session.scalars(select(PartORM).order_by(PartORM.id)).all()]

    def get_by_id(self, part_id: int) -> PartEntity | None:
        orm = self._session.get(PartORM, part_id)
        return _to_entity(orm) if orm else None

    def create(
        self,
        name: str,
        sku: str,
        description: str | None,
        unit_price: float,
        stock_quantity: int,
        min_stock_level: int,
    ) -> PartEntity:
        part = PartORM(
            name=name,
            sku=sku,
            description=description,
            unit_price=unit_price,
            stock_quantity=stock_quantity,
            min_stock_level=min_stock_level,
        )
        try:
            self._session.add(part)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValueError("SKU já cadastrado.") from exc
        self._session.refresh(part)
        return _to_entity(part)

    def update(self, part_id: int, fields: dict[str, object]) -> PartEntity | None:
        part = self._session.get(PartORM, part_id)
        if part is None:
            return None
        for key, value in fields.items():
            setattr(part, key, value)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValueError("SKU já cadastrado.") from exc
        self._session.refresh(part)
        return _to_entity(part)

    def delete(self, part_id: int) -> bool:
        part = self._session.get(PartORM, part_id)
        if part is None:
            return False
        self._session.delete(part)
        self._session.commit()
        return True
