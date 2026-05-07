from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.services.oc_service import OCService
from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user

# Usamos una etiqueta que agrupe toda la logística de compras
router = APIRouter(
    prefix="/ordenes_parciales",
    tags=["Gestión de Órdenes de Compra"]
)

@router.post(
    "/", 
    status_code=status.HTTP_201_CREATED,
    summary="Generar nueva Orden de Compra"
)
def create_oc(
    rq_item_id: int,
    cantidad_comprada: int,
    proveedor: str,
    ubicacion_envio: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Registra una adquisición formal para un ítem de requerimiento específico.
    
    - **Gestión Parcial**: Permite comprar cantidades menores a las solicitadas originalmente, manteniendo el rastro de lo pendiente.
    - **Logística**: Registra el proveedor adjudicado y la ubicación física de recepción en **Ramis SAC**.
    - **Seguridad**: Solo personal autorizado puede emitir órdenes de compra.
    """
    service = OCService(db)
    try:
        return service.create_oc(
            rq_item_id,
            cantidad_comprada,
            proveedor,
            ubicacion_envio
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Error en la creación: {str(e)}"
        )

@router.get(
    "/", 
    summary="Consultar historial de órdenes por ítem"
)
def list_oc(
    rq_item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Recupera el historial completo de adquisiciones vinculadas a un ítem de requerimiento.
    
    - **Trazabilidad**: Útil para verificar cuántas órdenes se han emitido para un mismo producto y quiénes son los proveedores.
    """
    service = OCService(db)
    return service.list_oc_by_rq_item(rq_item_id)

@router.put(
    "/{oc_id}/estado", 
    summary="Actualizar flujo de estado de la OC"
)
def update_oc_estado(
    oc_id: int,
    estado: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Modifica la etapa actual de la Orden de Compra (ej. Pendiente, Recibido, Cancelado).
    
    - **Control de Ciclo de Vida**: Permite al almacenero marcar el ingreso de la mercadería una vez recibida físicamente.
    - **Validación**: El sistema verifica la existencia de la orden antes de aplicar el cambio.
    """
    service = OCService(db)
    try:
        return service.update_oc_estado(oc_id, estado)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Error de actualización: La Orden de Compra {oc_id} no existe o el estado es inválido."
        )