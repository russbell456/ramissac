from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.incidente_service import IncidenteService
from app.schemas.incidente_schema import (
    IncidenteCreate,
    IncidenteUpdate,
    IncidenteResponse,
)
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/incidentes",
    tags=["Incidentes de Operación"],
    dependencies=[Depends(get_current_user)],
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_incidente_manager(user: CurrentUserDep) -> User:
    if user.role not in ["admin", "trabajador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para gestionar incidentes.",
        )
    return user


def require_operational_actor(user: CurrentUserDep) -> User:
    """Permite reportar incidentes al conductor y a los roles administrativos."""
    if user.role not in ["admin", "trabajador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para reportar incidentes.",
        )
    return user


@router.get("/", response_model=list[IncidenteResponse])
def listar_incidentes(db: DbDep, _: Annotated[User, Depends(require_incidente_manager)]):
    return IncidenteService(db).get_all_incidentes()


@router.get("/vehiculo/{vehiculo_id}", response_model=list[IncidenteResponse])
def listar_incidentes_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_incidente_manager)],
):
    return IncidenteService(db).get_incidentes_por_vehiculo(vehiculo_id)


@router.get(
    "/vehiculo/{vehiculo_id}/historial",
    response_model=list[IncidenteResponse],
)
def historial_incidentes_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_incidente_manager)],
):
    return IncidenteService(db).get_incidentes_por_vehiculo(vehiculo_id)


@router.get("/{id}", response_model=IncidenteResponse)
def obtener_incidente(
    id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_incidente_manager)],
):
    return IncidenteService(db).get_incidente_by_id(id)


@router.post(
    "/",
    response_model=IncidenteResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_incidente(
    schema: IncidenteCreate,
    db: DbDep,
    user: Annotated[User, Depends(require_operational_actor)],
):
    return IncidenteService(db).create_incidente(schema, user.id)


@router.put("/{id}", response_model=IncidenteResponse)
def actualizar_incidente(
    id: int,
    schema: IncidenteUpdate,
    db: DbDep,
    _: Annotated[User, Depends(require_incidente_manager)],
):
    return IncidenteService(db).update_incidente(id, schema)
