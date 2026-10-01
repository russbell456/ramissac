from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

from app.models.transportes_enums import EstadoIncidente, TipoIncidente


class IncidenteCreate(BaseModel):
    vehiculo_id: Optional[int] = None
    ruta_id: Optional[int] = None
    tipo: str = Field(default="incidente", description="accidente|incidente|novedad")
    descripcion: str = Field(..., description="Descripcion del incidente")
    afecta_personas: bool = False
    dano_vehiculo: bool = False
    requiere_acta: bool = False
    observaciones: Optional[str] = None

    @field_validator("tipo", mode="after")
    @classmethod
    def _validar_tipo(cls, v: str) -> str:
        valores = {t.value for t in TipoIncidente}
        if v not in valores:
            raise ValueError(f"Tipo de incidente invalido: {v}.")
        return v


class IncidenteUpdate(BaseModel):
    tipo: Optional[str] = None
    estado: Optional[str] = None
    descripcion: Optional[str] = None
    afecta_personas: Optional[bool] = None
    dano_vehiculo: Optional[bool] = None
    requiere_acta: Optional[bool] = None
    observaciones: Optional[str] = None

    @field_validator("tipo", mode="after")
    @classmethod
    def _validar_tipo(cls, v: str) -> str:
        if v is None:
            return v
        valores = {t.value for t in TipoIncidente}
        if v not in valores:
            raise ValueError(f"Tipo de incidente invalido: {v}.")
        return v

    @field_validator("estado", mode="after")
    @classmethod
    def _validar_estado(cls, v: str) -> str:
        if v is None:
            return v
        valores = {e.value for e in EstadoIncidente}
        if v not in valores:
            raise ValueError(f"Estado de incidente invalido: {v}.")
        return v


class IncidenteResponse(BaseModel):
    id: int
    vehiculo_id: Optional[int] = None
    ruta_id: Optional[int] = None
    tipo: str
    estado: str
    fecha_reporte: datetime
    descripcion: str
    afecta_personas: bool
    dano_vehiculo: bool
    requiere_acta: bool
    registrado_por: Optional[int] = None
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True

