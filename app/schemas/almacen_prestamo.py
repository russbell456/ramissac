from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from enum import Enum


class TipoArticuloSchema(str, Enum):
    EQUIPO = "equipo"
    CONSUMIBLE = "consumible"


class ItemPrestamo(BaseModel):
    articulo_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)


class PrestamoDetalleSchema(BaseModel):
    id: int
    articulo_id: int
    cantidad_prestada: int
    cantidad_devuelta: int
    esta_devuelto: bool
    articulo_nombre: str
    articulo_tipo: str
    articulo_unidad: str

    class Config:
        from_attributes = True


class PrestamoQRData(BaseModel):
    trabajador_id: int = Field(..., gt=0)
    codigo_unico: str = Field(..., min_length=1)
    dni: str = Field(..., pattern=r"^\d{8}$")
    nombres_completos: str = Field(..., min_length=2)
    cargo: str = Field(..., min_length=1)
    fecha_prestamo: datetime
    fecha_devolucion_prevista: datetime
    items: List[ItemPrestamo] = Field(..., min_length=1)
    firma_base64: str = Field(..., min_length=1)


class PrestamoResponse(BaseModel):
    id: int
    codigo_unico: str
    estado: str
    message: str = "Préstamo registrado correctamente"


class ArticuloPrestamoSchema(BaseModel):
    trabajador_id: int
    nombres_completos: str
    dni: str
    cargo: str
    fecha_prestamo: datetime
    cantidad_pendiente: int


class PrestamoSchema(BaseModel):
    id: int
    trabajador_id: int
    nombres_completos: str
    dni: str
    cargo: str
    codigo_unico: str
    fecha_prestamo: datetime
    fecha_devolucion_prevista: datetime
    firma_base64: str
    estado: str
    registrado_por: str
    fecha_registro: datetime
    detalles: List[PrestamoDetalleSchema]

    class Config:
        from_attributes = True
