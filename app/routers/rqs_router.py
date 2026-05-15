from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.services.rq_service import RQService
from app.services.rq_item_service import RQItemService

from app.schemas.rq_schema import RQCreate, RQResponse, RQItemPendienteResponse
from app.schemas.rq_estado_schema import RQEstadoUpdate
from app.schemas.rq_compra_schema import RQCompraEstadoResponse

from app.dependencies.auth_dependencies import get_current_user

# Organizamos bajo la etiqueta principal de requerimientos
router = APIRouter(
    prefix="/rqs",
    tags=["Gestión de Requerimientos (RQ)"]
)

@router.post(
    "/", 
    response_model=RQResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo folio de requerimiento"
)
def create_rq(
    rq: RQCreate, 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Inicia un nuevo proceso de requerimiento en el sistema **RamisToolX**.
    
    - **Fase Inicial**: El RQ se crea por defecto en estado 'Pendiente'.
    - **Trazabilidad**: Genera un identificador único para el seguimiento de compras y logística.
    - **Seguridad**: Solo personal autorizado puede dar apertura a nuevos folios.
    """
    service = RQService(db)
    try:
        return service.create_rq(rq.dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error en la creación del folio: {str(e)}"
        )

@router.get(
    "/", 
    response_model=List[RQResponse], 
    summary="Listar todos los folios registrados"
)
def list_rqs(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Recupera la lista completa de Requerimientos (RQ) históricos y activos.
    """
    service = RQService(db)
    return service.get_all_rqs()

@router.get(
    "/{rq_id}", 
    response_model=RQResponse, 
    summary="Consultar detalle de un RQ específico"
)
def get_rq(
    rq_id: int, 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Obtiene la información de cabecera de un Requerimiento mediante su ID.
    """
    service = RQService(db)
    try:
        return service.get_rq(rq_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put(
    "/{rq_id}/estado", 
    response_model=RQResponse, 
    summary="Actualizar fase del ciclo de vida del RQ"
)
def update_rq_estado(
    rq_id: int,
    rq_estado: RQEstadoUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Permite cambiar el estado global del requerimiento (ej. De 'Pendiente' a 'En Proceso' o 'Finalizado').
    
    - **Control de Flujo**: El sistema valida que la transición de estado sea permitida según las reglas de negocio.
    """
    service = RQService(db)
    try:
        return service.update_rq_estado(rq_id, rq_estado.estado)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/{rq_id}/items/pendientes", 
    response_model=List[RQItemPendienteResponse], 
    summary="Ver ítems pendientes de este RQ"
)
def listar_items_pendientes_compra(
    rq_id: int, 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Filtra los ítems de un requerimiento específico que aún requieren ser comprados.
    """
    service = RQService(db)
    try:
        return service.listar_items_pendientes_compra(rq_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/{rq_id}/estado-compra", 
    response_model=RQCompraEstadoResponse, 
    summary="Auditoría de cumplimiento de compra"
)
def ver_estado_compra(
    rq_id: int, 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Proporciona un resumen ejecutivo del estado de atención del requerimiento.
    
    - **Visualización**: Permite saber qué porcentaje del RQ ya ha sido cubierto por Órdenes de Compra.
    - **Toma de Decisiones**: Útil para identificar cuellos de botella en la adquisición de materiales.
    """
    service = RQService(db)
    try:
        return service.obtener_estado_compra(rq_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete(
    "/{rq_id}", 
    summary="Eliminar requerimiento y sus dependencias"
)
def delete_rq(
    rq_id: int, 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Elimina el registro del RQ. 
    
    - **Advertencia**: Esta acción puede afectar la trazabilidad de los ítems y órdenes de compra asociadas. Se recomienda usar solo para registros erróneos.
    """
    service = RQService(db)
    try:
        service.delete_rq(rq_id)
        return {"detail": f"El Requerimiento con ID {rq_id} ha sido eliminado satisfactoriamente."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/pendientes/global", 
    response_model=List[RQItemPendienteResponse], 
    summary="Reporte global de ítems desatendidos"
)
def listar_items_pendientes_global(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Muestra todos los ítems pendientes de todos los RQs abiertos en el sistema.
    """
    service = RQItemService(db)
    return service.obtener_items_pendientes_global()