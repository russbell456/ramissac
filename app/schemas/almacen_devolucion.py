from pydantic import BaseModel
from typing import List
from datetime import datetime

class ItemDevolucion(BaseModel):
    prestamo_detalle_id: int
    cantidad: int

class DevolucionQRData(BaseModel):
    trabajador_id: int
    codigo_unico: str
    dni: str
    nombres_completos: str
    cargo: str
    fecha_devolucion: datetime
    prestamo_id: int  # Referencia al préstamo original
    items: List[ItemDevolucion]
    firma_base64: str

class DevolucionResponse(BaseModel):
    id: int
    codigo_unico: str
    estado: str
    message: str = "Devolución registrada correctamente"