from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class VehiculoBase(BaseModel):
    placa: str = Field(..., description="Placa única del vehículo")
    marca: str = Field(..., description="Marca del vehículo")
    modelo: str = Field(..., description="Modelo del vehículo")
    capacidad_carga: float = Field(..., description="Capacidad de carga en toneladas/kg")


class VehiculoCreate(VehiculoBase):
    kilometraje_actual: float = 0.0

    @field_validator("kilometraje_actual", mode="after")
    @classmethod
    def _validar_kilometraje(cls, v: float) -> float:
        if v < 0:
            raise ValueError("El kilometraje no puede ser negativo.")
        return v


class VehiculoUpdate(BaseModel):
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    capacidad_carga: Optional[float] = None
    kilometraje_actual: Optional[float] = None

    @field_validator("kilometraje_actual", mode="after")
    @classmethod
    def _validar_kilometraje(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("El kilometraje no puede ser negativo.")
        return v


class VehiculoResponse(VehiculoBase):
    id: int
    kilometraje_actual: float
    estado: str
    fecha_baja: Optional[datetime] = None
    usuario_baja: Optional[int] = None

    class Config:
        from_attributes = True
