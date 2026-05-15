from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.schemas.orden_compra_schema import OrdenCompraResponse


class RQItemCreate(BaseModel):
    codigo: str
    descripcion: str
    cantidad: int
    unidad: str
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

class RQItemResponse(BaseModel):
    id: int
    codigo: str
    descripcion: str
    cantidad: int
    unidad: str
    ordenes_parciales: List[OrdenCompraResponse] = []

    model_config = {"from_attributes": True}
