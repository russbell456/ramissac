from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(
    prefix="/rq-items",
    tags=["RQ Items"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)


@router.post("/{rq_id}", response_model=RQItemResponse)
def create_item(
    rq_id: int,
    item: RQItemCreate,
    db: Session = Depends(get_db)
):
    service = RQItemService(db)
    return service.create_item(item.dict(), rq_id)


@router.get("/pendientes", response_model=List[RQItemPendienteResponse])
def listar_items_pendientes(
    db: Session = Depends(get_db)
):
    service = RQItemService(db)
    return service.obtener_items_pendientes_global()


@router.get("/{rq_id}", response_model=List[RQItemResponse])
def list_items(
    rq_id: int,
    db: Session = Depends(get_db)
):
    service = RQItemService(db)
    return service.get_items_by_rq(rq_id)


@router.put("/{item_id}/estado")
def update_item_estado(
    item_id: int,
    estado: str,
    db: Session = Depends(get_db)
):
    service = RQItemService(db)
    return service.update_estado(item_id, estado)


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    service = RQItemService(db)
    return service.delete_item(item_id)
