from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_admin
from app.shared.http_errors import domain_error_handler
from app.parts.adapters.presenter import to_response
from app.parts.adapters.sqlalchemy_repository import SqlAlchemyPartRepository
from app.parts.application.use_cases import (
    CreatePartUseCase,
    DeletePartUseCase,
    GetPartUseCase,
    ListPartsUseCase,
    UpdatePartUseCase,
)
from app.parts.domain.repository import IPartRepository
from app.parts.schemas import PartCreate, PartRead, PartUpdate

router = APIRouter(prefix="/parts", tags=["parts"])


def _get_repo(session: Session = Depends(get_db)) -> IPartRepository:
    return SqlAlchemyPartRepository(session)


@router.get("", response_model=list[PartRead], dependencies=[Depends(get_current_admin)])
def get_parts(repo: IPartRepository = Depends(_get_repo)) -> list[PartRead]:
    return [to_response(p) for p in ListPartsUseCase(repo).execute()]


@router.get("/{part_id}", response_model=PartRead, dependencies=[Depends(get_current_admin)])
def get_part(part_id: int, repo: IPartRepository = Depends(_get_repo)) -> PartRead:
    with domain_error_handler():
        return to_response(GetPartUseCase(repo).execute(part_id))


@router.post("", response_model=PartRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_part(payload: PartCreate, repo: IPartRepository = Depends(_get_repo)) -> PartRead:
    with domain_error_handler():
        return to_response(
            CreatePartUseCase(repo).execute(
                name=payload.name,
                sku=payload.sku,
                description=payload.description,
                unit_price=payload.unit_price,
                stock_quantity=payload.stock_quantity,
                min_stock_level=payload.min_stock_level,
            )
        )


@router.put("/{part_id}", response_model=PartRead, dependencies=[Depends(get_current_admin)])
def put_part(part_id: int, payload: PartUpdate, repo: IPartRepository = Depends(_get_repo)) -> PartRead:
    with domain_error_handler():
        return to_response(UpdatePartUseCase(repo).execute(part_id, payload.model_dump(exclude_none=True)))


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_part(part_id: int, repo: IPartRepository = Depends(_get_repo)) -> Response:
    with domain_error_handler():
        DeletePartUseCase(repo).execute(part_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
