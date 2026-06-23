from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class ItemDevolucion(BaseModel):
    prestamo_detalle_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)


class DevolucionQRData(BaseModel):
    trabajador_id: int = Field(..., gt=0)
    codigo_unico: str = Field(..., min_length=1)
    dni: str = Field(..., pattern=r"^\d{8}$")
    nombres_completos: str = Field(..., min_length=2)
    cargo: str = Field(..., min_length=1)
    fecha_devolucion: datetime
    prestamo_id: int = Field(..., gt=0)
    items: List[ItemDevolucion] = Field(..., min_length=1)
    firma_base64: str = Field(..., min_length=1)


class DevolucionResponse(BaseModel):
    id: int
    codigo_unico: str
    estado: str
    message: str = "Devolución registrada correctamente"
