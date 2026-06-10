from app.parts.domain.entity import PartEntity
from app.parts.schemas import PartRead


def to_response(entity: PartEntity) -> PartRead:
    return PartRead(
        id=entity.id,
        name=entity.name,
        sku=entity.sku,
        description=entity.description,
        unit_price=entity.unit_price,
        stock_quantity=entity.stock_quantity,
        min_stock_level=entity.min_stock_level,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
