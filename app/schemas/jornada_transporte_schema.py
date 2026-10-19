from __future__ import annotations

from datetime import date, datetime
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
    horometro_inicial: float = Field(..., gt=0)
    horometro_final: float = Field(..., gt=0)

    @model_validator(mode="after")
    def validar_horometros(self) -> AccionGruaCreate:
        if self.horometro_final < self.horometro_inicial:
            raise ValueError("El horómetro final no puede ser menor al inicial.")
        return self

class AccionCombustibleCreate(BaseModel):
    galones: float = Field(..., ge=0.1, le=100)
    nivel_final: int
    costo: Optional[float] = Field(None, ge=0)
    comprobante: Optional[str] = Field(None, max_length=100)
    odometro: Optional[float] = Field(None, ge=0)

    @field_validator("nivel_final")
    @classmethod
    def validar_nivel_final(cls, value: int) -> int:
        if value not in {0, 25, 50, 75, 100}:
            raise ValueError("Seleccione un nivel de combustible válido.")
        return value

class AccionMantenimientoCreate(BaseModel):
    taller: str = Field(..., min_length=1)
    tipo: Literal["Preventivo", "Correctivo"]
    trabajos_preventivos: Optional[list[str]] = None
    descripcion_correctivo: Optional[str] = None

    @model_validator(mode="after")
    def validar_trabajos(self) -> AccionMantenimientoCreate:
        if not self.taller.strip():
            raise ValueError("Indique el taller o concesionaria.")
        if self.tipo == "Preventivo" and not self.trabajos_preventivos:
            raise ValueError("Seleccione al menos un trabajo preventivo.")
        if self.tipo == "Correctivo" and not (self.descripcion_correctivo or "").strip():
            raise ValueError("Describa el mantenimiento correctivo.")
        return self


class AccionInspeccionCreate(BaseModel):
    fecha_inspeccion: date
    fecha_vencimiento: date


class AccionCocadaCreate(BaseModel):
    medida: float


class AccionTorqueCreate(BaseModel):
    medida: float


class AccionTrabajosExternosCreate(BaseModel):
    descripcion_trabajos: str = Field(..., min_length=1)

    @field_validator("descripcion_trabajos")
    @classmethod
    def validar_descripcion(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Describa los trabajos realizados.")
        return value.strip()


class AccionGruaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actividad: Optional[str] = None
    horometro_inicial: Optional[float] = None
    horometro_final: Optional[float] = None


class AccionCombustibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    galones: Optional[float] = None
    nivel_final: Optional[int] = None
    costo: Optional[float] = None
    comprobante: Optional[str] = None
    odometro: Optional[float] = None


class AccionMantenimientoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    taller: Optional[str] = None
    tipo: Optional[str] = None
    trabajos_preventivos: Optional[list[str]] = None
    descripcion_correctivo: Optional[str] = None


class AccionInspeccionResponse(AccionInspeccionCreate):
    model_config = ConfigDict(from_attributes=True)


class AccionCocadaResponse(AccionCocadaCreate):
    model_config = ConfigDict(from_attributes=True)


class AccionTorqueResponse(AccionTorqueCreate):
    model_config = ConfigDict(from_attributes=True)


class AccionTrabajosExternosResponse(AccionTrabajosExternosCreate):
    model_config = ConfigDict(from_attributes=True)

class EvidenciaObservacion(BaseModel):
    tiene_observaciones: bool = False
    severidad: Optional[Literal["leve", "grave"]] = None
    foto_observacion: Optional[str] = Field(None, max_length=500, pattern=r"^/uploads/transportes/[a-f0-9]+\.(jpg|png|webp)$")

    @model_validator(mode="after")
    def validar_evidencia(self):
        if self.tiene_observaciones or self.severidad:
            self.tiene_observaciones = True
            if not self.severidad or not self.foto_observacion or not (getattr(self, "observaciones", None) or "").strip():
                raise ValueError("Las observaciones requieren severidad, descripción y fotografía.")
        return self


class RegistroAccionCreate(EvidenciaObservacion):
    jornada_padre_id: Optional[int] = Field(None, gt=0)
    accion_tipo: Literal[
        "Empezar a Conducir",
        "Operar Grúa",
        "Abastecer Combustible",
        "Mantenimiento Preventivo / Correctivo",
        "Reporte de Incidencias u Observaciones",
        "Check List y/o V°B° de vehículos",
        "Inspección Técnica",
        "Medición de Cocada",
        "Medición de Torque",
        "Trabajos a Externos",
    ]
    vehiculo_id: int = Field(..., gt=0)
    km_inicial: Optional[float] = Field(None, gt=0)
    ruta: Optional[str] = None
    nivel_combustible: Optional[int] = None
    checklist_flash: Optional[dict[str, bool]] = None
    observaciones: str = Field(..., min_length=1)
    detalles_grua: Optional[AccionGruaCreate] = None
    detalles_combustible: Optional[AccionCombustibleCreate] = None
    detalles_mantenimiento: Optional[AccionMantenimientoCreate] = None
    detalles_inspeccion: Optional[AccionInspeccionCreate] = None
    detalles_cocada: Optional[AccionCocadaCreate] = None
    detalles_torque: Optional[AccionTorqueCreate] = None
    detalles_trabajos_externos: Optional[AccionTrabajosExternosCreate] = None

    @field_validator("observaciones")
    @classmethod
    def validar_observaciones(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Ingrese observaciones.")
        return value.strip()

    @field_validator("nivel_combustible")
    @classmethod
    def validar_nivel_inicial(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in {0, 25, 50, 75, 100}:
            raise ValueError("Seleccione un nivel de combustible válido.")
        return value

    @model_validator(mode="after")
    def validar_flujo(self) -> RegistroAccionCreate:
        if self.accion_tipo not in {"Operar Grúa", "Reporte de Incidencias u Observaciones"}:
            if self.km_inicial is None:
                raise ValueError("Ingrese km_inicial para esta acción.")
            if self.nivel_combustible is None:
                raise ValueError("Ingrese nivel_combustible para esta acción.")
        if self.accion_tipo == "Reporte de Incidencias u Observaciones" and not self.tiene_observaciones:
            raise ValueError("El reporte requiere observaciones con severidad, descripción y fotografía.")
        if self.accion_tipo == "Empezar a Conducir":
            if not (self.ruta or "").strip():
                raise ValueError("Seleccione una ruta para conducir.")
            if not self.checklist_flash:
                raise ValueError("Complete el Check List Flash.")
        elif self.accion_tipo == "Check List y/o V°B° de vehículos":
            if not self.checklist_flash:
                raise ValueError("Complete el Check List Flash.")
        elif self.accion_tipo == "Operar Grúa" and self.detalles_grua is None:
            raise ValueError("Complete los datos de la grúa.")
        elif self.accion_tipo == "Abastecer Combustible" and self.detalles_combustible is None:
            raise ValueError("Complete los datos del abastecimiento.")
        elif (self.accion_tipo == "Mantenimiento Preventivo / Correctivo"
              and self.detalles_mantenimiento is None):
            raise ValueError("Complete los datos del mantenimiento.")
        elif self.accion_tipo == "Inspección Técnica" and self.detalles_inspeccion is None:
            raise ValueError("Complete las fechas de inspección técnica.")
        elif self.accion_tipo == "Medición de Cocada" and self.detalles_cocada is None:
            raise ValueError("Ingrese la medición de cocada.")
        elif self.accion_tipo == "Medición de Torque" and self.detalles_torque is None:
            raise ValueError("Ingrese la medición de torque.")
        elif self.accion_tipo == "Trabajos a Externos" and self.detalles_trabajos_externos is None:
            raise ValueError("Describa los trabajos externos.")
        return self


class JornadaResponse(BaseModel):
    estado_semaforo: str = "verde"
    tiene_observaciones: bool = False
    severidad: Optional[str] = None
    foto_observacion: Optional[str] = None
    jornada_padre_id: Optional[int] = None
    nivel_combustible_final: Optional[float] = None
    galones_abastecidos: Optional[float] = None
    galones_consumidos: Optional[float] = None
    rendimiento_km_galon: Optional[float] = None
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


class ChecklistCreate(EvidenciaObservacion):
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
    foto_incidencia: Optional[str] = Field(None, max_length=500, pattern=r"^/uploads/transportes/[a-f0-9]+\.(jpg|png|webp)$")
    severidad: Optional[Literal["leve", "grave"]] = None
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
    sub_acciones: list[JornadaDetalleResponse] = Field(default_factory=list)
    checklists: list[ChecklistResponse] = []
    incidencias: list[IncidenciaRutaResponse] = []
    detalles_grua: Optional[AccionGruaResponse] = None
    detalles_combustible: Optional[AccionCombustibleResponse] = None
    detalles_mantenimiento: Optional[AccionMantenimientoResponse] = None
    detalles_inspeccion: Optional[AccionInspeccionResponse] = None
    detalles_cocada: Optional[AccionCocadaResponse] = None
    detalles_torque: Optional[AccionTorqueResponse] = None
    detalles_trabajos_externos: Optional[AccionTrabajosExternosResponse] = None


class MantenimientoAlertaResponse(BaseModel):
    vehiculo_id: int
    kilometraje_actual: float
    proximo_kilometraje_mantenimiento: Optional[float]
    alerta: bool
