from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any

from app.services.orden_compra_service import OrdenCompraService
from app.database.connection import get_db
from app.schemas.orden_compra_schema import (
    OrdenCompraCreate,
    OrdenCompraSummaryResponse,
    OrdenCompraEntity,
    ComprobanteItem,
    MERCADERIA_COMPROBANTE,
    GUIA_REMISION,
    OrdenCompraItemUpdateCantidad
)

# 🔐 SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(
    prefix="/ordenes",
    tags=["Órdenes Parciales"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_orden(
    orden: OrdenCompraCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una orden de compra (Cabecera) permitiendo la compra de múltiples ítems (M:M)
    y valida la subida de comprobantes.
    """
    service = OrdenCompraService(db)
    try:
        return service.create_orden(orden)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/item/{rq_item_id}", response_model=List[OrdenCompraEntity])
def get_ordenes(
    rq_item_id: int,
    db: Session = Depends(get_db)
):
    """
    Listar todas las órdenes parciales asociadas a un item del RQ.
    """
    service = OrdenCompraService(db)
    return service.get_ordenes_by_item(rq_item_id)


@router.patch("/items/{oc_item_id}/cantidad", status_code=status.HTTP_200_OK)
def update_item_cantidad_comprada(
    oc_item_id: int,
    data: OrdenCompraItemUpdateCantidad,
    db: Session = Depends(get_db)
):
    """
    Actualiza solo la cantidad comprada de un ÍTEM ESPECÍFICO
    y ajusta la cantidad disponible en el Inventario.
    """
    try:
        service = OrdenCompraService(db)
        return service.update_item_cantidad(
            oc_item_id=oc_item_id,
            nueva_cantidad=data.nueva_cantidad
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.put("/{orden_id}")
def update_orden(
    orden_id: int,
    orden_data: OrdenCompraCreate,
    db: Session = Depends(get_db)
):
    """
    Actualiza la orden de compra completamente:
    cabecera, comprobantes e ítems.
    """
    service = OrdenCompraService(db)
    try:
        return service.update_orden_completa(orden_id, orden_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error desconocido al actualizar: {str(e)}"
        )


@router.patch("/{orden_id}/editar")
def editar_orden(
    orden_id: int,
    cambios: Dict[str, Optional[Any]] = Body(
        ...,
        example={
            "cantidad_comprada": 10,
            "ubicacion_envio": "Almacén Central",
            "comprobantes": [
                {
                    "tipo_documento": MERCADERIA_COMPROBANTE,
                    "archivo_ruta": "factura_001.pdf",
                    "numero_comprobante": "F001-1234",
                    "es_factura": True,
                    "fecha": "2025-12-04"
                },
                {
                    "tipo_documento": GUIA_REMISION,
                    "archivo_ruta": "guia_001.pdf"
                }
            ]
        }
    ),
    db: Session = Depends(get_db)
):
    """
    Edita parcialmente la orden de compra.
    """
    service = OrdenCompraService(db)
    try:
        return service.patch_orden(orden_id, cambios)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/resumen")
def resumen_ordenes(
    estado: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retorna órdenes de compra agrupadas por RQ.
    """
    service = OrdenCompraService(db)
    try:
        return service.listar_ordenes_por_rq(estado, fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{orden_id}")
def delete_orden(
    orden_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina una orden parcial y recalcula el estado del RQ.
    """
    service = OrdenCompraService(db)
    try:
        return service.delete_orden(orden_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
