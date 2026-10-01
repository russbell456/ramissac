from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.transportes_enums import (
    EstadoJornada,
    TipoChecklistJornada,
    TipoIncidenciaRuta,
)


class JornadaAsignacionCreate(BaseModel):
    vehiculo_id: int = Field(..., gt=0)
    conductor_id: int = Field(..., gt=0)


class RegistroAccionCreate(BaseModel):
    accion_tipo: str = Field(..., min_length=1)
    vehiculo_id: Optional[int] = None
    ruta: Optional[str] = None
    nivel_combustible: Optional[int] = None
    checklist_flash: Optional[dict] = None
    observaciones: Optional[str] = None


class JornadaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehiculo_id: Optional[int]
    conductor_id: int
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    estado: str
    accion_tipo: Optional[str]
    ruta: Optional[str]
    nivel_combustible: Optional[int]
    checklist_flash: Optional[dict]
    observaciones: Optional[str]


class ChecklistCreate(BaseModel):
    tipo: str = TipoChecklistJornada.INICIAL.value
    kilometraje: float = Field(..., ge=0)
    nivel_combustible: str = Field(..., min_length=1, max_length=50)
    estado_general: str = Field(..., min_length=1, max_length=100)
    conforme: bool
    observaciones: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, value: str) -> str:
        if value not in {item.value for item in TipoChecklistJornada}:
            raise ValueError("El tipo de checklist debe ser inicial o final.")
        return value


class ChecklistResponse(ChecklistCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jornada_id: int


class IncidenciaRutaCreate(BaseModel):
    tipo: str
    descripcion: str = Field(..., min_length=1)
    fecha: Optional[datetime] = None

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, value: str) -> str:
        if value not in {item.value for item in TipoIncidenciaRuta}:
            raise ValueError("El tipo de incidencia debe ser falla, accidente o combustible.")
        return value


class IncidenciaRutaResponse(IncidenciaRutaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jornada_id: int
    fecha: datetime


class JornadaDetalleResponse(JornadaResponse):
    checklists: list[ChecklistResponse] = []
    incidencias: list[IncidenciaRutaResponse] = []


class MantenimientoAlertaResponse(BaseModel):
    vehiculo_id: int
    kilometraje_actual: float
    proximo_kilometraje_mantenimiento: Optional[float]
    alerta: bool
