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
    OrdenCompraItemUpdateCantidad
)

# 🔐 SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(
    prefix="/ordenes",
    tags=["Logística: Órdenes de Compra"]
)

@router.post(
    "/", 
    status_code=status.HTTP_201_CREATED,
    summary="Emitir Orden de Compra (M:M)"
)
def create_orden(
    orden: OrdenCompraCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Registra una transacción formal de adquisición en el sistema.
    
    - **Multicompra (M:M)**: Permite vincular múltiples ítems de requerimiento en una sola cabecera de orden.
    - **Validación Documental**: Verifica la integridad de los comprobantes adjuntos antes de procesar la entrada.
    - **Impacto en Stock**: Sincroniza las cantidades adquiridas con el Inventario General de **Ramis SAC**.
    """
    service = OrdenCompraService(db)
    try:
        return service.create_orden(orden)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Fallo en validación de negocio: {str(e)}"
        )

@router.get(
    "/item/{rq_item_id}", 
    response_model=List[OrdenCompraEntity],
    summary="Listar órdenes por ítem de RQ"
)
def get_ordenes(
    rq_item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Recupera el historial de adquisiciones parciales para un ítem específico.
    
    - **Trazabilidad**: Permite auditar qué órdenes han cubierto (o están cubriendo) la necesidad de un requerimiento.
    """
    service = OrdenCompraService(db)
    return service.get_ordenes_by_item(rq_item_id)

@router.patch(
    "/items/{oc_item_id}/cantidad", 
    status_code=status.HTTP_200_OK,
    summary="Ajustar cantidad comprada de un ítem"
)
def update_item_cantidad_comprada(
    oc_item_id: int,
    data: OrdenCompraItemUpdateCantidad,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Modifica la cantidad de una partida específica dentro de una orden ya existente.
    
    - **Sincronización de Inventario**: Al cambiar la cantidad, el sistema recalcula automáticamente el stock disponible.
    - **Restricción**: Útil para correcciones de errores de digitación o cambios de último minuto en la recepción física.
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
            detail=f"Error sistémico al ajustar cantidades: {str(e)}"
        )

@router.put(
    "/{orden_id}", 
    summary="Actualización integral de Orden"
)
def update_orden(
    orden_id: int,
    orden_data: OrdenCompraCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Reemplaza la totalidad de los datos de una Orden de Compra.
    
    - **Alcance**: Cabecera, relación de ítems y archivos de comprobantes.
    - **Integridad**: Re-valida todas las reglas de negocio como si fuera una orden nueva.
    """
    service = OrdenCompraService(db)
    try:
        return service.update_orden_completa(orden_id, orden_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch(
    "/{orden_id}/editar", 
    summary="Edición parcial (Patch) de Orden"
)
def editar_orden(
    orden_id: int,
    cambios: Dict[str, Optional[Any]] = Body(
        ...,
        example={
            "cantidad_comprada": 10,
            "ubicacion_envio": "Almacén Central",
            "comprobantes": [{"tipo_documento": "Factura", "archivo_ruta": "factura_v2.pdf"}]
        }
    ),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Permite modificar campos específicos de una orden sin afectar el resto.
    
    - **Flexibilidad**: Ideal para actualizar solo el estado de envío o adjuntar comprobantes faltantes.
    """
    service = OrdenCompraService(db)
    try:
        return service.patch_orden(orden_id, cambios)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/resumen", 
    summary="Generar reporte consolidado por RQ"
)
def resumen_ordenes(
    estado: Optional[str] = Query(None, description="Filtro por estado de la orden"),
    fecha_inicio: Optional[str] = Query(None, description="Rango inicial (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Rango final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Vista de auditoría que agrupa todas las adquisiciones por su Requerimiento de origen.
    
    - **Análisis de Datos**: Permite evaluar el cumplimiento de compras en rangos de tiempo específicos.
    """
    service = OrdenCompraService(db)
    try:
        return service.listar_ordenes_por_rq(estado, fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete(
    "/{orden_id}", 
    status_code=status.HTTP_200_OK,
    summary="Eliminar Orden y recalcular estados"
)
def delete_orden(
    orden_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Elimina permanentemente una orden del sistema.
    
    - **Cuidado**: Esta acción dispara el recalculo del estado del Requerimiento (RQ) y revierte el stock en inventario.
    - **Audit Trail**: Se recomienda usar con precaución para mantener la coherencia contable.
    """
    service = OrdenCompraService(db)
    try:
        return service.delete_orden(orden_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))