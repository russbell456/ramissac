from __future__ import annotations
from pydantic import BaseModel
from typing import List


class RQItemCompraEstado(BaseModel):
    item_id: int
    codigo: str
    descripcion: str
    cantidad_pedida: int
    cantidad_comprada: int
    cantidad_faltante: int
    progreso: float  # %

    model_config = {"from_attributes": True}


class RQCompraEstadoResponse(BaseModel):
    rq_id: int
    nro_rq: str
    estado_compra: str
    progreso_compra: float
    items: List[RQItemCompraEstado]

    model_config = {"from_attributes": True}
