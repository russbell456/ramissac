from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.database.connection import get_db
from app.services.comprobante_service import ComprobanteService
from app.repositories.orden_compra_repository import OrdenCompraRepository

# 🔐 SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(
    prefix="/ordenes",
    tags=["Comprobantes"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)


@router.post("/{orden_id}/comprobantes/upload")
def upload_comprobante(
    orden_id: int,
    file: UploadFile = File(...),
    tipo_documento: str = Form(...),
    numero_comprobante: str | None = Form(None),
    es_factura: bool | None = Form(None),
    fecha: date | None = Form(None),
    db: Session = Depends(get_db)
):
    repo = OrdenCompraRepository(db)
    orden = repo.get_by_id(orden_id)

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no existe")

    service = ComprobanteService(db)

    comprobante = service.subir_comprobante(
        orden_id=orden_id,
        file=file,
        tipo_documento=tipo_documento,
        numero_comprobante=numero_comprobante,
        es_factura=es_factura,
        fecha=fecha
    )

    return {
        "message": "Comprobante subido correctamente",
        "comprobante_id": comprobante.id,
        "archivo": comprobante.archivo_ruta
    }
