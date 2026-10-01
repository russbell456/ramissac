from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

from app.models.transportes_enums import CriticidadAveria, EstadoAveria


class AveriaCreate(BaseModel):
    vehiculo_id: int = Field(..., description="ID del vehículo")
    ruta_id: Optional[int] = None
    descripcion: str = Field(..., description="Descripción de la avería")
    criticidad: str = Field(default="media", description="baja|media|alta|critica")
    origen_incidente_id: Optional[int] = None

    @field_validator("criticidad", mode="after")
    @classmethod
    def _validar_criticidad(cls, v: str) -> str:
        valores = {c.value for c in CriticidadAveria}
        if v not in valores:
            raise ValueError(f"Criticidad inválida: {v}.")
        return v


class AveriaUpdate(BaseModel):
    descripcion: Optional[str] = None
    criticidad: Optional[str] = None
    estado: Optional[str] = None
    detalle_resolucion: Optional[str] = None

    @field_validator("criticidad", mode="after")
    @classmethod
    def _validar_criticidad(cls, v: str) -> str:
        if v is None:
            return v
        valores = {c.value for c in CriticidadAveria}
        if v not in valores:
            raise ValueError(f"Criticidad inválida: {v}.")
        return v

    @field_validator("estado", mode="after")
    @classmethod
    def _validar_estado(cls, v: str) -> str:
        if v is None:
            return v
        valores = {e.value for e in EstadoAveria}
        if v not in valores:
            raise ValueError(f"Estado inválido: {v}.")
        return v


class AveriaResponse(BaseModel):
    id: int
    vehiculo_id: int
    ruta_id: Optional[int] = None
    descripcion: str
    criticidad: str
    estado: str
    origen_incidente_id: Optional[int] = None
    fecha_reporte: datetime
    fecha_resolucion: Optional[datetime] = None
    registrado_por: Optional[int] = None
    detalle_resolucion: Optional[str] = None

    class Config:
        from_attributes = True
