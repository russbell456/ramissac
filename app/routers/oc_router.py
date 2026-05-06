from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.oc_service import OCService
from app.database.connection import get_db

# 🔐 SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(
    prefix="/ordenes_parciales",
    tags=["ordenes_parciales"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)


@router.post("/")
def create_oc(
    rq_item_id: int,
    cantidad_comprada: int,
    proveedor: str,
    ubicacion_envio: str,
    db: Session = Depends(get_db)
):
    service = OCService(db)
    try:
        return service.create_oc(
            rq_item_id,
            cantidad_comprada,
            proveedor,
            ubicacion_envio
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/")
def list_oc(
    rq_item_id: int,
    db: Session = Depends(get_db)
):
    service = OCService(db)
    return service.list_oc_by_rq_item(rq_item_id)


@router.put("/{oc_id}/estado")
def update_oc_estado(
    oc_id: int,
    estado: str,
    db: Session = Depends(get_db)
):
    service = OCService(db)
    try:
        return service.update_oc_estado(oc_id, estado)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
