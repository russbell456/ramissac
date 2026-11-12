import json

from typing import Annotated
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    status,
    UploadFile,
)

from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database.connection import (
    get_db,
)

from app.dependencies.auth_dependencies import (
    get_current_user,
)

from app.schemas.almacen_devolucion import (
    DevolucionQRData,
    DevolucionResponse,
)

from app.services.almacen_devolucion_service import (
    AlmacenDevolucionService,
)
from app.utils.evidence_storage import (
    delete_stored_upload,
    save_image_upload,
    save_mapped_photos,
    public_asset_url,
)


router = APIRouter(
    prefix="/almacen",
    tags=["Almacén Devolución"],
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
    "/registrar-devolucion-qr",
    response_model=DevolucionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_devolucion_qr(
    db: DbDep,
    user: UserDep,
    datos: str = Form(...),
    firma: UploadFile = File(...),
    fotos: list[UploadFile] = File(default=[]),
    fotos_metadata: str = Form(default="[]"),
):

    # ==========================================
    # AUTORIZACIÓN
    # ==========================================

    if user.role not in [
        "almacenero",
        "admin",
    ]:

        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Solo almacenero o admin "
                "puede registrar devoluciones"
            ),
        )

    service = (
        AlmacenDevolucionService(
            db
        )
    )

    archivos_guardados: list[str] = []
    try:
        body = json.loads(datos)
        if not isinstance(body, dict):
            raise ValueError("Los datos de devolución deben ser un objeto JSON")
        if "firma_base64" in body or "foto_estado_devuelto" in body:
            raise ValueError("Firma y fotos deben enviarse como archivos multipart")
        firma_path = await save_image_upload(
            firma,
            "firmas/devoluciones",
            signature=True,
        )
        archivos_guardados.append(firma_path)
        fotos_por_detalle, fotos_guardadas = await save_mapped_photos(
            fotos,
            fotos_metadata,
            "devoluciones/evidencias",
            "prestamo_detalle_id",
        )
        archivos_guardados.extend(fotos_guardadas)
        body_items = body.get("items", [])
        if not isinstance(body_items, list):
            raise ValueError("items debe ser una lista")
        if any(not isinstance(item, dict) or "foto_estado_devuelto" in item for item in body_items):
            raise ValueError("Las fotos de artículos deben enviarse como archivos multipart")
        ids_detalles = {
            int(item["prestamo_detalle_id"])
            for item in body_items
            if isinstance(item, dict) and "prestamo_detalle_id" in item
        }
        if not set(fotos_por_detalle).issubset(ids_detalles):
            raise ValueError("Se adjuntó una foto para un artículo que no está en la devolución")
        for item in body_items:
            detalle_id = int(item.get("prestamo_detalle_id", 0))
            if detalle_id in fotos_por_detalle:
                item["foto_estado_devuelto"] = fotos_por_detalle[detalle_id]
        body["firma_base64"] = firma_path
        data = DevolucionQRData.model_validate(body)

        devolucion = (
            service.registrar_devolucion_desde_qr(
                data,
                user.id,
            )
        )

        archivos_guardados.clear()
        return DevolucionResponse(

            id=devolucion.id,

            codigo_unico=(
                devolucion.codigo_unico
            ),

            estado=(
                devolucion.estado.value
            ),

            fecha_devolucion=(
                devolucion.fecha_devolucion
            ),

            detalles=[
                {
                    "prestamo_detalle_id": detalle.prestamo_detalle_id,
                    "cantidad_devuelta": detalle.cantidad_devuelta,
                    "minutos_efectivos": detalle.minutos_efectivos,
                    "dias_tarifa": detalle.dias_tarifa,
                    "minutos_residuales": detalle.minutos_residuales,
                    "costo_hora_aplicado": detalle.costo_hora_aplicado,
                    "costo_dia_aplicado": detalle.costo_dia_aplicado,
                    "importe_informativo": detalle.importe_informativo,
                    "foto_estado_fin_url": public_asset_url(
                        detalle.foto_estado_devuelto
                    ),
                }
                for detalle in devolucion.detalles
            ],

            importe_informativo_total=sum(
                (
                    detalle.importe_informativo
                    for detalle in devolucion.detalles
                ),
                Decimal("0.00"),
            ),
            almacenero_id=devolucion.almacenero_id,
            almacenero_nombre=(
                " ".join(filter(None, [
                    getattr(devolucion.almacenero, "nombre", None),
                    getattr(devolucion.almacenero, "apellidos", None),
                ])) or None
            ),
            firma_url=public_asset_url(devolucion.firma_base64),
        )

    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        for path in archivos_guardados:
            delete_stored_upload(path)

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc
    except Exception:
        for path in archivos_guardados:
            delete_stored_upload(path)
        raise
