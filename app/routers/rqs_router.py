from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.services.rq_service import RQService
from app.services.rq_item_service import RQItemService

from app.schemas.rq_schema import RQCreate, RQResponse, RQItemPendienteResponse
from app.schemas.rq_estado_schema import RQEstadoUpdate
from app.schemas.rq_compra_schema import RQCompraEstadoResponse

from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/rqs",
    tags=["RQs"],
    #dependencies=[Depends(get_current_user)]#
)


@router.post("/", response_model=RQResponse)
def create_rq(rq: RQCreate, db: Session = Depends(get_db)):
    service = RQService(db)
    try:
        return service.create_rq(rq.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[RQResponse])
def list_rqs(db: Session = Depends(get_db)):
    service = RQService(db)
    return service.get_all_rqs()


@router.get("/{rq_id}", response_model=RQResponse)
def get_rq(rq_id: int, db: Session = Depends(get_db)):
    service = RQService(db)
    try:
        return service.get_rq(rq_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{rq_id}/estado", response_model=RQResponse)
def update_rq_estado(
    rq_id: int,
    rq_estado: RQEstadoUpdate,
    db: Session = Depends(get_db)
):
    service = RQService(db)
    try:
        return service.update_rq_estado(rq_id, rq_estado.estado)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{rq_id}/items/pendientes", response_model=List[RQItemPendienteResponse])
def listar_items_pendientes_compra(rq_id: int, db: Session = Depends(get_db)):
    service = RQService(db)
    try:
        return service.listar_items_pendientes_compra(rq_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{rq_id}")
def delete_rq(rq_id: int, db: Session = Depends(get_db)):
    service = RQService(db)
    try:
        service.delete_rq(rq_id)
        return {"detail": "RQ eliminada"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{rq_id}/estado-compra", response_model=RQCompraEstadoResponse)
def ver_estado_compra(rq_id: int, db: Session = Depends(get_db)):
    service = RQService(db)
    try:
        return service.obtener_estado_compra(rq_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/pendientes", response_model=List[RQItemPendienteResponse])
def listar_items_pendientes(db: Session = Depends(get_db)):
    service = RQItemService(db)
    return service.obtener_items_pendientes_global()
