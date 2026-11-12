from typing import Annotated
import base64
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session
from fastapi.responses import Response
from app.schemas.rq_campo import RqAdjuntoCreate

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
    "logistica",
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


@router.post(
    "/importar-excel",
    status_code=status.HTTP_201_CREATED,
)
async def importar_excel(
    file: UploadFile = File(...),
    db: DbDep = None,
    user: UserDep = None,
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )

    service = AlmacenArticuloService(db)
    cantidad = await service.procesar_inventario_excel(file)
    return {
        "message": f"Se cargaron {cantidad} artículos correctamente."
    }


@router.get(
    "/articulos",
    response_model=list[ArticuloSchema],
)
def obtener_catalogo(
    db: DbDep,
):
    service = AlmacenArticuloService(db)
    return service.repo.get_all_disponibles()


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
        articulo = service.desactivar_articulo(
            articulo_id,
            user.id,
        )
        res = ArticuloSchema.model_validate(articulo)
        res.message = "Artículo desactivado correctamente"
        res.articulo_id = articulo.id
        return res
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
        articulo = service.activar_articulo(
            articulo_id,
            user.id,
        )
        res = ArticuloSchema.model_validate(articulo)
        res.message = "Artículo activado correctamente"
        res.articulo_id = articulo.id
        return res
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


@router.post("/{articulo_id}/ficha-tecnica")
async def subir_ficha_tecnica(articulo_id: int, db: DbDep, user: UserDep, file: UploadFile = File(...)):
    validar_rol(user)
    try:
        service = AlmacenArticuloService(db)
        articulo = service.obtener_articulo(articulo_id)
        datos = await file.read(5 * 1024 * 1024 + 1)
        adjunto = RqAdjuntoCreate(nombre=file.filename or "ficha.pdf", tipo_mime="application/pdf",
                                contenido_base64=base64.b64encode(datos).decode())
        ficha = articulo._ficha()
        ficha.nombre_documento = adjunto.nombre
        ficha.documento_base64 = adjunto.contenido_base64
        db.commit()
        return {"nombre": ficha.nombre_documento}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Seleccione una ficha técnica PDF válida de hasta 5 MB") from exc


@router.get("/{articulo_id}/ficha-tecnica")
def descargar_ficha_tecnica(articulo_id: int, db: DbDep, user: UserDep):
    service = AlmacenArticuloService(db)
    try:
        articulo = service.obtener_articulo(articulo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not articulo.ficha or not articulo.ficha.documento_base64:
        raise HTTPException(status_code=404, detail="El artículo no tiene ficha técnica")
    return Response(base64.b64decode(articulo.ficha.documento_base64), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(articulo.ficha.nombre_documento)}"})
