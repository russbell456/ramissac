from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.services.rq_item_service import RQItemService
from app.database.connection import get_db
from app.schemas.rq_item_schema import (
    RQItemCreate,
    RQItemResponse,
    RQItemPendienteResponse
)

# 🔐 DEPENDENCIA DE SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

# Organizamos bajo la etiqueta de gestión de necesidades
router = APIRouter(
    prefix="/rq-items",
    tags=["Gestión de Requerimientos (RQ)"]
)

@router.post(
    "/{rq_id}", 
    response_model=RQItemResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Añadir ítem a Requerimiento"
)
def create_item(
    rq_id: int,
    item: RQItemCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Agrega una herramienta o material específico a un Requerimiento (RQ) ya existente.
    
    - **Especificación**: Permite detallar cantidades, unidades de medida y descripción técnica.
    - **Trazabilidad**: El ítem queda vinculado permanentemente al folio del RQ para su posterior cotización u orden de compra.
    - **Seguridad**: Solo personal autorizado puede modificar la estructura de un requerimiento activo.
    """
    service = RQItemService(db)
    return service.create_item(item.dict(), rq_id)

@router.get(
    "/pendientes", 
    response_model=List[RQItemPendienteResponse],
    summary="Listar ítems pendientes de atención"
)
def listar_items_pendientes(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Vista global de todos los ítems que aún no han sido cubiertos por una Orden de Compra.
    
    - **Uso Crítico**: Esta es la herramienta principal del área de logística de **Ramis SAC** para consolidar compras y optimizar costos.
    - **Filtro Automático**: Excluye ítems ya comprados o anulados.
    """
    service = RQItemService(db)
    return service.obtener_items_pendientes_global()

@router.get(
    "/{rq_id}", 
    response_model=List[RQItemResponse],
    summary="Consultar desglose de un RQ"
)
def list_items(
    rq_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Recupera el listado detallado de ítems pertenecientes a un número de RQ específico.
    """
    service = RQItemService(db)
    return service.get_items_by_rq(rq_id)

@router.put(
    "/{item_id}/estado", 
    summary="Actualizar estado del ítem"
)
def update_item_estado(
    item_id: int,
    estado: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Permite transicionar el estado de un ítem (ej. Pendiente -> En Compra -> Recibido).
    
    - **Integridad**: El sistema valida que el estado sea coherente con el flujo de trabajo de la empresa.
    """
    service = RQItemService(db)
    return service.update_estado(item_id, estado)

@router.delete(
    "/{item_id}", 
    status_code=status.HTTP_200_OK,
    summary="Eliminar ítem del requerimiento"
)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Elimina permanentemente un ítem de la lista. 
    
    - **Nota**: Solo se recomienda si el ítem fue registrado por error y no tiene órdenes de compra asociadas.
    """
    service = RQItemService(db)
    return service.delete_item(item_id)