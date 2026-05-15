from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class InventarioEntity(BaseModel):
    """Esquema de respuesta para un solo ítem de inventario."""
    id: int
    codigo: str
    descripcion: str
    cantidad_disponible: int
    ubicacion: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True

class InventarioListResponse(BaseModel):
    """Esquema para listar el inventario completo."""
    items: List[InventarioEntity]
    total_items: int
    
    class Config:
        from_attributes = True