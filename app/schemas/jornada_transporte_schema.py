from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.transportes_enums import (
    EstadoJornada,
    TipoChecklistJornada,
    TipoIncidenciaRuta,
)


class JornadaAsignacionCreate(BaseModel):
    vehiculo_id: int = Field(..., gt=0)
    conductor_id: int = Field(..., gt=0)


class AccionGruaCreate(BaseModel):
    actividad: str = Field(..., min_length=1)
    horometro_inicial: float = Field(..., ge=0)
    horometro_final: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validar_horometros(self) -> AccionGruaCreate:
        if self.horometro_final < self.horometro_inicial:
            raise ValueError("El horómetro final no puede ser menor al inicial.")
        return self

class AccionCombustibleCreate(BaseModel):
    galones: float = Field(..., gt=0)
    nivel_final: int

    @field_validator("nivel_final")
    @classmethod
    def validar_nivel_final(cls, value: int) -> int:
        if value not in {0, 25, 50, 75, 100}:
            raise ValueError("Seleccione un nivel de combustible válido.")
        return value

class AccionMantenimientoCreate(BaseModel):
    taller: Literal["CONAUTO", "PERUMOTOR", "MALVEX"]
    tipo: Literal["Preventivo", "Correctivo"]
    trabajos_preventivos: Optional[list[str]] = None
    descripcion_correctivo: Optional[str] = None

    @model_validator(mode="after")
    def validar_trabajos(self) -> AccionMantenimientoCreate:
        if self.tipo == "Preventivo" and not self.trabajos_preventivos:
            raise ValueError("Seleccione al menos un trabajo preventivo.")
        if self.tipo == "Correctivo" and not (self.descripcion_correctivo or "").strip():
            raise ValueError("Describa el mantenimiento correctivo.")
        return self


class AccionGruaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actividad: Optional[str] = None
    horometro_inicial: Optional[float] = None
    horometro_final: Optional[float] = None


class AccionCombustibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    galones: Optional[float] = None
    nivel_final: Optional[int] = None


class AccionMantenimientoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    taller: Optional[str] = None
    tipo: Optional[str] = None
    trabajos_preventivos: Optional[list[str]] = None
    descripcion_correctivo: Optional[str] = None

class RegistroAccionCreate(BaseModel):
    accion_tipo: str = Field(..., min_length=1)
    vehiculo_id: int = Field(..., gt=0)
    ruta: Optional[str] = None
    nivel_combustible: int
    checklist_flash: Optional[dict] = None
    observaciones: Optional[str] = None
    detalles_grua: Optional[AccionGruaCreate] = None
    detalles_combustible: Optional[AccionCombustibleCreate] = None
    detalles_mantenimiento: Optional[AccionMantenimientoCreate] = None

    @field_validator("nivel_combustible")
    @classmethod
    def validar_nivel_inicial(cls, value: int) -> int:
        if value not in {0, 25, 50, 75, 100}:
            raise ValueError("Seleccione un nivel de combustible válido.")
        return value

    @model_validator(mode="after")
    def validar_flujo(self) -> RegistroAccionCreate:
        if self.accion_tipo == "Empezar a Conducir":
            if not (self.ruta or "").strip():
                raise ValueError("Seleccione una ruta para conducir.")
            if not self.checklist_flash:
                raise ValueError("Complete el Check List Flash.")
        elif self.accion_tipo == "Operar Grúa" and self.detalles_grua is None:
            raise ValueError("Complete los datos de la grúa.")
        elif self.accion_tipo == "Abastecer Combustible" and self.detalles_combustible is None:
            raise ValueError("Complete los datos del abastecimiento.")
        elif (self.accion_tipo == "Mantenimiento Preventivo / Correctivo"
              and self.detalles_mantenimiento is None):
            raise ValueError("Complete los datos del mantenimiento.")
        return self


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
    km_inicial: Optional[float] = None
    km_final: Optional[float] = None
    alerta_horas: bool = False
    alerta_km: bool = False
    horas_efectivas: Optional[float] = None


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
    detalles_grua: Optional[AccionGruaResponse] = None
    detalles_combustible: Optional[AccionCombustibleResponse] = None
    detalles_mantenimiento: Optional[AccionMantenimientoResponse] = None


class MantenimientoAlertaResponse(BaseModel):
    vehiculo_id: int
    kilometraje_actual: float
    proximo_kilometraje_mantenimiento: Optional[float]
    alerta: bool
