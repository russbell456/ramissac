from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.inspeccion_service import InspeccionService
from app.schemas.inspeccion_schema import (
    ChecklistItemCreate,
    ChecklistItemResponse,
    InspeccionCreate,
    InspeccionResolver,
    InspeccionResponse,
)
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.transportes_enums import TipoInspeccion

router = APIRouter(
    prefix="/api/inspecciones",
    tags=["Inspecciones de Vehículos"],
    dependencies=[Depends(get_current_user)],
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_inspector(user: CurrentUserDep) -> User:
    """Admin y almacenero pueden gestionar inspecciones. Los trabajadores ejecutan
    sólo operaciones propias (se valida en el endpoint)."""
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para gestionar inspecciones.",
        )
    return user


def require_inspection_actor(user: CurrentUserDep) -> User:
    """Permite registrar inspecciones al personal operativo y administrativo."""
    if user.role not in ["trabajador", "almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para registrar inspecciones.",
        )
    return user


# ----------------------------------------------------------------------
# Checklist items (catálogo reutilizable)
# ----------------------------------------------------------------------
@router.get("/checklist-items", response_model=list[ChecklistItemResponse])
def listar_checklist_items(db: DbDep, _: Annotated[User, Depends(require_inspector)]):
    return InspeccionService(db).get_all_checklist_items()


@router.post(
    "/checklist-items",
    response_model=ChecklistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_checklist_item(
    schema: ChecklistItemCreate,
    db: DbDep,
    _: Annotated[User, Depends(require_inspector)],
):
    return InspeccionService(db).create_checklist_item(schema)


# ----------------------------------------------------------------------
# Inspecciones
# ----------------------------------------------------------------------
@router.get("/", response_model=list[InspeccionResponse])
def listar_inspecciones(db: DbDep, _: Annotated[User, Depends(require_inspector)]):
    return InspeccionService(db).get_all_inspecciones()


@router.get("/vehiculo/{vehiculo_id}", response_model=list[InspeccionResponse])
def listar_inspecciones_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_inspector)],
):
    return InspeccionService(db).get_inspecciones_por_vehiculo(vehiculo_id)


@router.get("/{id}", response_model=InspeccionResponse)
def obtener_inspeccion(
    id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_inspector)],
):
    return InspeccionService(db).get_inspeccion_by_id(id)


@router.post(
    "/",
    response_model=InspeccionResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_inspeccion(
    schema: InspeccionCreate,
    db: DbDep,
    user: Annotated[User, Depends(require_inspection_actor)],
):
    return InspeccionService(db).create_inspeccion(schema, user.id)


@router.patch("/{id}/resolver", response_model=InspeccionResponse)
def resolver_inspeccion(
    id: int,
    schema: InspeccionResolver,
    db: DbDep,
    user: Annotated[User, Depends(require_inspector)],
):
    service = InspeccionService(db)
    inspeccion = service.get_inspeccion_by_id(id)

    # Si es POST_MANTENIMIENTO, se aplica la liberación del vehículo según
    # el resultado (aprobada -> disponible, rechazada -> permanece observado).
    if inspeccion.tipo == TipoInspeccion.POST_MANTENIMIENTO.value:
        return service.resolver_post_mantenimiento(id, schema, user.id)

    return service.resolver_inspeccion(id, schema, user.id)
