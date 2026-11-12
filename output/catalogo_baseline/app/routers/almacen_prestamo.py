import json
import os

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    status,
    UploadFile,
)

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database.connection import get_db

from app.dependencies.auth_dependencies import (
    get_current_user,
)

from app.schemas.almacen_prestamo import (
    ArticuloPrestamoSchema,
    ConfirmacionSolicitudPrestamo,
    PrestamoQRData,
    PrestamoResponse,
    PrestamoSchema,
    SolicitudPrestamoCreada,
    SolicitudPrestamoData,
    SolicitudPrestamoResumen,
)

from app.services.almacen_prestamo_service import (
    AlmacenPrestamoService,
)
from app.utils.evidence_storage import (
    delete_stored_upload,
    save_image_upload,
    save_mapped_photos,
)


router = APIRouter(
    prefix="/almacen",
    tags=["Almacén"],
)


DbDep = Annotated[
    Session,
    Depends(get_db),
]


UserDep = Annotated[
    dict,
    Depends(get_current_user),
]


@router.post(
    "/solicitudes-prestamo",
    response_model=SolicitudPrestamoCreada,
    status_code=status.HTTP_201_CREATED,
)
def crear_solicitud_prestamo(
    data: SolicitudPrestamoData,
    db: DbDep,
    user: UserDep,
):
    if user.role != "trabajador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un trabajador puede crear una solicitud QR",
        )

    try:
        prestamo = AlmacenPrestamoService(db).crear_solicitud_trabajador(
            user.id,
            data,
        )
        return SolicitudPrestamoCreada(
            id=prestamo.id,
            codigo_unico=prestamo.codigo_unico,
            estado=prestamo.estado.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/solicitudes-prestamo/{codigo_unico}",
    response_model=SolicitudPrestamoResumen,
)
def obtener_solicitud_prestamo(
    codigo_unico: str,
    db: DbDep,
    user: UserDep,
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo almacenero o admin puede revisar solicitudes",
        )
    try:
        return AlmacenPrestamoService(db).obtener_solicitud_qr(codigo_unico)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/solicitudes-prestamo/{prestamo_id}/confirmar",
    response_model=PrestamoResponse,
)
async def confirmar_solicitud_prestamo(
    prestamo_id: int,
    db: DbDep,
    user: UserDep,
    datos: str = Form(...),
    firma: UploadFile = File(...),
    fotos: list[UploadFile] = File(default=[]),
    fotos_metadata: str = Form(default="[]"),
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo almacenero o admin puede confirmar la entrega",
        )
    archivos_guardados: list[str] = []
    try:
        body = json.loads(datos)
        if not isinstance(body, dict):
            raise ValueError("Los datos del préstamo deben ser un objeto JSON")
        if "firma_base64" in body or "fotos" in body:
            raise ValueError("Firma y fotos deben enviarse como archivos multipart")
        firma_path = await save_image_upload(
            firma,
            "firmas/prestamos",
            signature=True,
        )
        archivos_guardados.append(firma_path)
        fotos_por_articulo, fotos_guardadas = await save_mapped_photos(
            fotos,
            fotos_metadata,
            "prestamos/evidencias",
            "articulo_id",
        )
        archivos_guardados.extend(fotos_guardadas)
        body["firma_base64"] = firma_path
        body["fotos"] = [
            {"articulo_id": articulo_id, "foto_estado_inicio": foto_path}
            for articulo_id, foto_path in fotos_por_articulo.items()
        ]
        data = ConfirmacionSolicitudPrestamo.model_validate(body)
        prestamo = AlmacenPrestamoService(db).confirmar_solicitud_qr(
            prestamo_id,
            user.id,
            data,
        )
        archivos_guardados.clear()
        return PrestamoResponse(
            id=prestamo.id,
            codigo_unico=prestamo.codigo_unico,
            estado=prestamo.estado.value,
            pdf_url=f"/almacen/prestamo/{prestamo.id}/pdf",
        )
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        for path in archivos_guardados:
            delete_stored_upload(path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        for path in archivos_guardados:
            delete_stored_upload(path)
        raise


@router.post(
    "/registrar-prestamo-qr",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/registrar-prestamo-manual",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_prestamo_qr(
    db: DbDep,
    user: UserDep,
    datos: str = Form(...),
    firma: UploadFile = File(...),
    fotos: list[UploadFile] = File(default=[]),
    fotos_metadata: str = Form(default="[]"),
):

    if user.role not in [
        "almacenero",
        "admin",
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Solo almacenero o admin "
                "puede registrar préstamos"
            ),
        )

    service = AlmacenPrestamoService(
        db
    )

    archivos_guardados: list[str] = []
    try:
        body = json.loads(datos)
        if not isinstance(body, dict):
            raise ValueError("Los datos del préstamo deben ser un objeto JSON")
        if "firma_base64" in body or "foto_estado_inicio" in body:
            raise ValueError("Firma y fotos deben enviarse como archivos multipart")
        firma_path = await save_image_upload(
            firma,
            "firmas/prestamos",
            signature=True,
        )
        archivos_guardados.append(firma_path)
        fotos_por_articulo, fotos_guardadas = await save_mapped_photos(
            fotos,
            fotos_metadata,
            "prestamos/evidencias",
            "articulo_id",
        )
        archivos_guardados.extend(fotos_guardadas)
        body_items = body.get("items", [])
        if not isinstance(body_items, list):
            raise ValueError("items debe ser una lista")
        if any(not isinstance(item, dict) or "foto_estado_inicio" in item for item in body_items):
            raise ValueError("Las fotos de artículos deben enviarse como archivos multipart")
        ids_articulos = {
            int(item["articulo_id"])
            for item in body_items
            if isinstance(item, dict) and "articulo_id" in item
        }
        if not set(fotos_por_articulo).issubset(ids_articulos):
            raise ValueError("Se adjuntó una foto para un artículo que no está en el préstamo")
        for item in body_items:
            articulo_id = int(item.get("articulo_id", 0))
            if articulo_id in fotos_por_articulo:
                item["foto_estado_inicio"] = fotos_por_articulo[articulo_id]
        body["firma_base64"] = firma_path
        data = PrestamoQRData.model_validate(body)

        prestamo = (
            service.registrar_prestamo_desde_qr(
                data,
                user.id,
            )
        )

        archivos_guardados.clear()
        return PrestamoResponse(
            id=prestamo.id,
            codigo_unico=(
                prestamo.codigo_unico
            ),
            estado=(
                prestamo.estado.value
            ),
            pdf_url=(
                f"/almacen/prestamo/{prestamo.id}/pdf"
            ),
        )
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        for path in archivos_guardados:
            delete_stored_upload(path)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        for path in archivos_guardados:
            delete_stored_upload(path)
        raise


@router.get(
    "/prestamo/{prestamo_id}/pdf",
)
def descargar_pdf(
    prestamo_id: int,
):

    pdf_path = (
        f"static/prestamos/"
        f"prestamo_{prestamo_id}.pdf"
    )

    if not os.path.exists(pdf_path):

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF no encontrado",
        )

    return FileResponse(
        pdf_path,
        filename=(
            f"prestamo_{prestamo_id}.pdf"
        ),
    )


@router.get(
    "/trabajador/{trabajador_id}/prestamos",
    response_model=list[PrestamoSchema],
)
def obtener_prestamos_trabajador(
    trabajador_id: int,
    db: DbDep,
    user: UserDep,
):

    if (
        user.role
        not in [
            "almacenero",
            "admin",
        ]
        and user.id != trabajador_id
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No autorizado para "
                "ver préstamos ajenos"
            ),
        )

    service = AlmacenPrestamoService(
        db
    )

    return (
        service.obtener_prestamos_trabajador(
            trabajador_id
        )
    )


@router.get(
    "/articulo/{articulo_id}/prestamos",
    response_model=list[
        ArticuloPrestamoSchema
    ],
)
def obtener_prestamos_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep,
):

    if user.role not in [
        "almacenero",
        "admin",
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )

    service = AlmacenPrestamoService(
        db
    )

    return (
        service.obtener_prestamos_articulo(
            articulo_id
        )
    )
