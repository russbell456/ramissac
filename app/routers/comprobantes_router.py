from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.services.comprobante_service import ComprobanteService
from app.repositories.orden_compra_repository import OrdenCompraRepository
from app.dependencies.auth_dependencies import get_current_user

# Organizamos bajo un tag que denote gestión documental
router = APIRouter(
    prefix="/ordenes",
    tags=["Gestión de Comprobantes"]
)

@router.post(
    "/{orden_id}/comprobantes/upload", 
    status_code=status.HTTP_201_CREATED,
    summary="Cargar comprobante digital a una orden"
)
def upload_comprobante(
    orden_id: int,
    file: UploadFile = File(...),
    tipo_documento: str = Form(..., description="Ej: Factura, Boleta, Guía de Remisión"),
    numero_comprobante: str | None = Form(None, description="Número de serie y correlativo"),
    es_factura: bool | None = Form(None, description="Indicar si el documento es una factura para efectos tributarios"),
    fecha: date | None = Form(None, description="Fecha de emisión del documento (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Sube y vincula un archivo digital a una Orden de Compra específica.
    
    - **Validación de Orden**: El sistema verifica que la Orden de Compra exista en la base de datos de Ramis SAC.
    - **Metadata**: Permite registrar el número, tipo y fecha del comprobante para facilitar búsquedas contables posteriores.
    - **Almacenamiento**: El archivo se procesa y se guarda en el servidor, manteniendo la trazabilidad con la orden de origen.
    - **Seguridad**: Requiere autenticación. (Se recomienda rol administrativo/contable).
    """
    # Verificamos si la orden existe antes de intentar subir nada
    repo = OrdenCompraRepository(db)
    orden = repo.get_by_id(orden_id)

    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Error: La Orden de Compra con ID {orden_id} no fue encontrada."
        )

    service = ComprobanteService(db)

    try:
        comprobante = service.subir_comprobante(
            orden_id=orden_id,
            file=file,
            tipo_documento=tipo_documento,
            numero_comprobante=numero_comprobante,
            es_factura=es_factura,
            fecha=fecha
        )

        return {
            "message": "Comprobante vinculado y subido correctamente.",
            "comprobante_id": comprobante.id,
            "archivo_ruta": comprobante.archivo_ruta
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error al procesar el archivo: {str(e)}"
        )