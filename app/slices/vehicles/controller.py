from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_admin
from app.shared.http_errors import domain_error_handler
from app.slices.vehicles.adapters.presenter import to_response
from app.slices.vehicles.adapters.sqlalchemy_repository import SqlAlchemyVehicleRepository
from app.slices.vehicles.application.use_cases import (
    CreateVehicleUseCase,
    DeleteVehicleUseCase,
    GetVehicleUseCase,
    ListVehiclesUseCase,
    UpdateVehicleUseCase,
)
from app.slices.vehicles.domain.repository import IVehicleRepository
from app.slices.vehicles.schemas import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _get_repo(session: Session = Depends(get_db)) -> IVehicleRepository:
    return SqlAlchemyVehicleRepository(session)


@router.get("", response_model=list[VehicleRead], dependencies=[Depends(get_current_admin)])
def get_vehicles(repo: IVehicleRepository = Depends(_get_repo)) -> list[VehicleRead]:
    return [to_response(v) for v in ListVehiclesUseCase(repo).execute()]


@router.get("/{vehicle_id}", response_model=VehicleRead, dependencies=[Depends(get_current_admin)])
def get_vehicle(vehicle_id: int, repo: IVehicleRepository = Depends(_get_repo)) -> VehicleRead:
    with domain_error_handler():
        return to_response(GetVehicleUseCase(repo).execute(vehicle_id))


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
def post_vehicle(payload: VehicleCreate, repo: IVehicleRepository = Depends(_get_repo)) -> VehicleRead:
    return to_response(
        CreateVehicleUseCase(repo).execute(
            client_id=payload.client_id,
            brand=payload.brand,
            model=payload.model,
            year=payload.year,
            license_plate=payload.license_plate,
        )
    )


@router.put("/{vehicle_id}", response_model=VehicleRead, dependencies=[Depends(get_current_admin)])
def put_vehicle(vehicle_id: int, payload: VehicleUpdate, repo: IVehicleRepository = Depends(_get_repo)) -> VehicleRead:
    with domain_error_handler():
        return to_response(UpdateVehicleUseCase(repo).execute(vehicle_id, payload.model_dump(exclude_none=True)))


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def remove_vehicle(vehicle_id: int, repo: IVehicleRepository = Depends(_get_repo)) -> Response:
    with domain_error_handler():
        DeleteVehicleUseCase(repo).execute(vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
