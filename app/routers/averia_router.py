from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.averia_service import AveriaService
from app.schemas.averia_schema import AveriaCreate, AveriaUpdate, AveriaResponse
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/averias",
    tags=["Averías de Vehículos"],
    dependencies=[Depends(get_current_user)],
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_averia_manager(user: CurrentUserDep) -> User:
    if user.role not in ["admin", "trabajador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para gestionar averías.",
        )
    return user


def require_operational_actor(user: CurrentUserDep) -> User:
    """Permite reportar averías al conductor y a los roles administrativos."""
    if user.role not in ["admin", "trabajador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para reportar averías.",
        )
    return user


@router.get("/", response_model=list[AveriaResponse])
def listar_averias(db: DbDep, _: Annotated[User, Depends(require_averia_manager)]):
    return AveriaService(db).get_all_averias()


@router.get("/vehiculo/{vehiculo_id}", response_model=list[AveriaResponse])
def listar_averias_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_averia_manager)],
):
    return AveriaService(db).get_averias_por_vehiculo(vehiculo_id)


@router.get(
    "/vehiculo/{vehiculo_id}/historial",
    response_model=list[AveriaResponse],
)
def historial_averias_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_averia_manager)],
):
    return AveriaService(db).get_averias_por_vehiculo(vehiculo_id)


@router.get("/{id}", response_model=AveriaResponse)
def obtener_averia(
    id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_averia_manager)],
):
    return AveriaService(db).get_averia_by_id(id)


@router.post(
    "/",
    response_model=AveriaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_averia(
    schema: AveriaCreate,
    db: DbDep,
    user: Annotated[User, Depends(require_operational_actor)],
):
    return AveriaService(db).create_averia(schema, user.id)


@router.put("/{id}", response_model=AveriaResponse)
def actualizar_averia(
    id: int,
    schema: AveriaUpdate,
    db: DbDep,
    user: Annotated[User, Depends(require_averia_manager)],
):
    return AveriaService(db).update_averia(id, schema, user.id)


@router.patch("/{id}/resolver", response_model=AveriaResponse)
def resolver_averia(
    id: int,
    db: DbDep,
    user: Annotated[User, Depends(require_averia_manager)],
):
    return AveriaService(db).resolver_averia(id, user.id)


@router.patch("/{id}/cerrar", response_model=AveriaResponse)
def cerrar_averia(
    id: int,
    db: DbDep,
    user: Annotated[User, Depends(require_averia_manager)],
):
    return AveriaService(db).cerrar_averia(id, user.id)
