# app/schemas/almacen.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class TipoArticuloSchema(str, Enum):
    EQUIPO = "equipo"
    CONSUMIBLE = "consumible"
class ArticuloSchema(BaseModel):
    id: int
    nombre: str
    unidad_medida: str
    tipo: TipoArticuloSchema
    stock_actual: int
    codigo_excel: str

    class Config:
        from_attributes = True