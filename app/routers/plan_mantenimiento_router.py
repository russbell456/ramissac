
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.mantenimiento_plan_service import PlanMantenimientoService
from app.schemas.mantenimiento_schema import (
    PlanMantenimientoCreate,
    PlanMantenimientoUpdate,
    PlanMantenimientoResponse,
)
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/planes-mantenimiento",
    tags=["Planes de Mantenimiento"],
    dependencies=[Depends(get_current_user)],
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_plan_manager(user: CurrentUserDep) -> User:
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para gestionar planes de mantenimiento.",
        )
    return user


@router.get("/", response_model=list[PlanMantenimientoResponse])
def listar_planes(db: DbDep, _: Annotated[User, Depends(require_plan_manager)]):
    return PlanMantenimientoService(db).get_all_planes()


@router.get("/vehiculo/{vehiculo_id}", response_model=list[PlanMantenimientoResponse])
def listar_planes_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_plan_manager)],
):
    return PlanMantenimientoService(db).get_planes_por_vehiculo(vehiculo_id)


@router.get("/{id}", response_model=PlanMantenimientoResponse)
def obtener_plan(
    id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_plan_manager)],
):
    return PlanMantenimientoService(db).get_plan_by_id(id)


@router.post(
    "/",
    response_model=PlanMantenimientoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_plan(
    schema: PlanMantenimientoCreate,
    db: DbDep,
    _: Annotated[User, Depends(require_plan_manager)],
):
    return PlanMantenimientoService(db).create_plan(schema)


@router.put("/{id}", response_model=PlanMantenimientoResponse)
def actualizar_plan(
    id: int,
    schema: PlanMantenimientoUpdate,
    db: DbDep,
    _: Annotated[User, Depends(require_plan_manager)],
):
    return PlanMantenimientoService(db).update_plan(id, schema)
