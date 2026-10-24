from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime

class VehiculoBase(BaseModel):
    placa: str = Field(..., description="Placa única del vehículo")
    marca: str = Field(default='Pendiente', description="Marca del vehículo")
    modelo: str = Field(default='Pendiente', description="Nombre o modelo del vehículo")
    tipo: Optional[str] = None
    capacidad_tanque_galones: Optional[float] = Field(None, gt=0)
    capacidad_carga: float = Field(default=0, ge=0, description="Capacidad de carga en toneladas/kg")
    soat_vencimiento: Optional[date] = None
    rt_vencimiento: Optional[date] = None
    tarjeta_propiedad_url: Optional[str] = Field(None, max_length=500)
    poliza_vencimiento: Optional[date] = None
    pase_minero_vencimiento: Optional[date] = None


class VehiculoCreate(VehiculoBase):
    kilometraje_actual: float = 0.0

    @field_validator("kilometraje_actual", mode="after")
    @classmethod
    def _validar_kilometraje(cls, v: float) -> float:
        if v < 0:
            raise ValueError("El kilometraje no puede ser negativo.")
        return v


class VehiculoUpdate(BaseModel):
    tipo: Optional[str] = None
    capacidad_tanque_galones: Optional[float] = Field(None, gt=0)
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    capacidad_carga: Optional[float] = None
    kilometraje_actual: Optional[float] = None
    soat_vencimiento: Optional[date] = None
    rt_vencimiento: Optional[date] = None
    tarjeta_propiedad_url: Optional[str] = Field(None, max_length=500)
    poliza_vencimiento: Optional[date] = None
    pase_minero_vencimiento: Optional[date] = None

    @field_validator("kilometraje_actual", mode="after")
    @classmethod
    def _validar_kilometraje(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("El kilometraje no puede ser negativo.")
        return v


class VehiculoResponse(VehiculoBase):
    observaciones_pendientes: Optional[str] = None
    estado_semaforo: str = "verde"
    id: int
    kilometraje_actual: float
    estado: str
    fecha_baja: Optional[datetime] = None
    usuario_baja: Optional[int] = None

    class Config:
        from_attributes = True
