from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import (
    get_current_user,
)
from app.schemas.almacen_articulo_schema import (
    ArticuloCreateSchema,
    ArticuloImagenSchema,
    ArticuloSchema,
    ArticuloUpdateSchema,
)
from app.services.almacen_articulo_service import (
    AlmacenArticuloService,
)


router = APIRouter(
    prefix="/articulo",
    tags=["Artículos"],
)

DbDep = Annotated[
    Session,
    Depends(get_db),
]

UserDep = Annotated[
    dict,
    Depends(get_current_user),
]


ALLOWED_ROLES = {
    "admin",
    "almacenero",
}


def validar_rol(user: dict) -> None:
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )


@router.post(
    "",
    response_model=ArticuloSchema,
    status_code=status.HTTP_201_CREATED,
)
def crear_articulo(
    data: ArticuloCreateSchema,
    db: DbDep,
    user: UserDep,
):
    validar_rol(user)

    service = AlmacenArticuloService(db)

    try:
        return service.crear_articulo(
            data.model_dump(),
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[ArticuloSchema],
)
def listar_articulos(
    db: DbDep,
):
    service = AlmacenArticuloService(db)

    return service.repo.get_all()


@router.get(
    "/disponibles",
    response_model=list[ArticuloSchema],
)
def listar_disponibles(
    db: DbDep,
):
    service = AlmacenArticuloService(db)

    return service.repo.get_all_disponibles()


@router.get(
    "/buscar",
    response_model=list[ArticuloSchema],
)
def buscar_articulos(
    q: str = "",
    db: DbDep = None,
):
    service = AlmacenArticuloService(db)

    return service.buscar_articulos(q)


@router.get(
    "/{articulo_id}",
    response_model=ArticuloSchema,
)
def obtener_articulo(
    articulo_id: int,
    db: DbDep,
):
    service = AlmacenArticuloService(db)

    try:
        return service.obtener_articulo(
            articulo_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/{articulo_id}",
    response_model=ArticuloSchema,
)
def actualizar_articulo(
    articulo_id: int,
    data: ArticuloUpdateSchema,
    db: DbDep,
    user: UserDep,
):
    validar_rol(user)

    service = AlmacenArticuloService(db)

    try:
        return service.actualizar_articulo(
            articulo_id,
            data.model_dump(
                exclude_unset=True
            ),
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{articulo_id}/desactivar",
    response_model=ArticuloSchema,
)
def desactivar_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep,
):
    validar_rol(user)

    service = AlmacenArticuloService(db)

    try:
        return service.desactivar_articulo(
            articulo_id,
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{articulo_id}/activar",
    response_model=ArticuloSchema,
)
def activar_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep,
):
    validar_rol(user)

    service = AlmacenArticuloService(db)

    try:
        return service.activar_articulo(
            articulo_id,
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{articulo_id}/imagenes",
    response_model=ArticuloImagenSchema,
    status_code=status.HTTP_201_CREATED,
)
async def subir_imagen(
    articulo_id: int,
    file: UploadFile = File(...),
    db: DbDep = None,
    user: UserDep = None,
):
    validar_rol(user)

    service = AlmacenArticuloService(db)

    try:
        return await service.guardar_imagen(
            articulo_id,
            file,
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/imagenes/{imagen_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_imagen(
    imagen_id: int,
    db: DbDep,
    user: UserDep,
):
    validar_rol(user)

    service = AlmacenArticuloService(db)

    try:
        service.eliminar_imagen(
            imagen_id,
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc