from __future__ import annotations

from pydantic import BaseModel
from datetime import date
from typing import List, Optional
from app.schemas.rq_item_schema import RQItemResponse

class RQCreate(BaseModel):
    nro_rq: str
    proyecto: str
    solicitante: str
    fecha_emision: date
    estado: Optional[str] = "pendiente"
    items: List[dict]  # lista de RQItemCreate como diccionarios
class RQItemPendienteResponse(BaseModel):
    rq_item_id: int
    codigo: str
    descripcion: str
    cantidad_requerida: int
    cantidad_comprada: float
    cantidad_pendiente: float

    model_config = {"from_attributes": True}
class RQItemPendienteResponse(BaseModel):
    rq_id: int
    nro_rq: str
    rq_item_id: int
    codigo: str
    descripcion: str
    cantidad_requerida: float
    cantidad_comprada: float
    cantidad_pendiente: float

    model_config = {"from_attributes": True}
class RQResponse(BaseModel):
    id: int
    nro_rq: str
    proyecto: str
    solicitante: str
    fecha_emision: date
    estado: str
    estado_compra: str
    progreso_compra: float
    items: List[RQItemResponse] = []

    model_config = {"from_attributes": True}
