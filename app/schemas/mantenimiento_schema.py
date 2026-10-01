from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

from app.models.transportes_enums import (
    EstadoControl,
    EstadoMantenimiento,
    TipoControlMantenimiento,
    TipoMantenimiento,
)


class MantenimientoBase(BaseModel):
    fecha_ingreso: datetime = Field(default_factory=datetime.utcnow, description="Fecha de ingreso al taller")
    descripcion_falla: str = Field(default="Mantenimiento registrado", description="Descripción detallada de la falla")
    costo: float = Field(default=0.0, ge=0, description="Costo del mantenimiento")


class MantenimientoCreate(MantenimientoBase):
    vehiculo_id: int = Field(..., description="ID del vehículo")
    tipo: str = Field(default="CORRECTIVO", description="PREVENTIVO|CORRECTIVO")
    averia_id: Optional[int] = None
    plan_id: Optional[int] = None
    tipo_control: Optional[str] = None
    intervalo_kilometraje: Optional[float] = None
    intervalo_dias: Optional[int] = None
    intervalo_horas: Optional[float] = None
    mecanico_id: Optional[int] = None
    kilometraje_mantenimiento: Optional[float] = Field(default=None, ge=0)
    proximo_kilometraje_mantenimiento: Optional[float] = Field(default=None, ge=0)
    fecha: Optional[datetime] = None
    descripcion_trabajo: Optional[str] = None

    @field_validator("tipo", mode="after")
    @classmethod
    def _validar_tipo(cls, v: str) -> str:
        valores = {t.value for t in TipoMantenimiento}
        if v not in valores:
            raise ValueError(f"Tipo de mantenimiento inválido: {v}.")
        return v


class MantenimientoUpdate(BaseModel):
    fecha_ingreso: Optional[datetime] = None
    descripcion_falla: Optional[str] = None
    costo: Optional[float] = None
    estado: Optional[str] = None
    tipo: Optional[str] = None
    descripcion_trabajo: Optional[str] = None
    fecha_cierre: Optional[datetime] = None
    observaciones_ejecucion: Optional[str] = None
    km_ejecucion: Optional[float] = None
    horas_ejecucion: Optional[float] = None
    trabajador_id: Optional[int] = None
    mecanico_id: Optional[int] = None
    kilometraje_mantenimiento: Optional[float] = Field(default=None, ge=0)
    proximo_kilometraje_mantenimiento: Optional[float] = Field(default=None, ge=0)
    fecha: Optional[datetime] = None

    @field_validator("estado", mode="after")
    @classmethod
    def _validar_estado(cls, v: str) -> str:
        if v is None:
            return v
        valores = {e.value for e in EstadoMantenimiento}
        if v not in valores:
            raise ValueError(f"Estado de mantenimiento inválido: {v}.")
        return v

    @field_validator("tipo", mode="after")
    @classmethod
    def _validar_tipo(cls, v: str) -> str:
        if v is None:
            return v
        valores = {t.value for t in TipoMantenimiento}
        if v not in valores:
            raise ValueError(f"Tipo de mantenimiento inválido: {v}.")
        return v


class MantenimientoResponse(MantenimientoBase):
    id: int
    vehiculo_id: int
    averia_id: Optional[int] = None
    plan_id: Optional[int] = None
    tipo: str
    descripcion_trabajo: Optional[str] = None
    fecha_cierre: Optional[datetime] = None
    estado: str
    fecha_baja: Optional[datetime] = None
    usuario_baja: Optional[int] = None
    tipo_control: Optional[str] = None
    intervalo_kilometraje: Optional[float] = None
    intervalo_dias: Optional[int] = None
    intervalo_horas: Optional[float] = None
    km_ejecucion: Optional[float] = None
    horas_ejecucion: Optional[float] = None
    trabajador_id: Optional[int] = None
    observaciones_ejecucion: Optional[str] = None
    mecanico_id: Optional[int] = None
    kilometraje_mantenimiento: Optional[float] = None
    proximo_kilometraje_mantenimiento: Optional[float] = None
    fecha: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanDetalleMantenimientoSchema(BaseModel):
    descripcion: str
    orden: int = 0


class PlanMantenimientoCreate(BaseModel):
    vehiculo_id: int
    nombre: str
    descripcion: Optional[str] = None
    tipo_control: str = Field(default="mixto", description="kilometraje|fecha|horas|mixto")
    intervalo_kilometraje: Optional[float] = None
    intervalo_dias: Optional[int] = None
    intervalo_horas: Optional[float] = None
    detalles: list[PlanDetalleMantenimientoSchema] = []

    @field_validator("tipo_control", mode="after")
    @classmethod
    def _validar_tipo_control(cls, v: str) -> str:
        valores = {t.value for t in TipoControlMantenimiento}
        if v not in valores:
            raise ValueError(f"Tipo de control inválido: {v}.")
        return v


class PlanMantenimientoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    tipo_control: Optional[str] = None
    intervalo_kilometraje: Optional[float] = None
    intervalo_dias: Optional[int] = None
    intervalo_horas: Optional[float] = None
    estado_control: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("tipo_control", mode="after")
    @classmethod
    def _validar_tipo_control(cls, v: str) -> str:
        if v is None:
            return v
        valores = {t.value for t in TipoControlMantenimiento}
        if v not in valores:
            raise ValueError(f"Tipo de control inválido: {v}.")
        return v

    @field_validator("estado_control", mode="after")
    @classmethod
    def _validar_estado_control(cls, v: str) -> str:
        if v is None:
            return v
        valores = {e.value for e in EstadoControl}
        if v not in valores:
            raise ValueError(f"Estado de control inválido: {v}.")
        return v


class PlanDetalleMantenimientoResponse(BaseModel):
    id: int
    plan_id: int
    descripcion: str
    orden: int

    class Config:
        from_attributes = True


class PlanMantenimientoResponse(BaseModel):
    id: int
    vehiculo_id: int
    nombre: str
    descripcion: Optional[str] = None
    tipo_control: str
    intervalo_kilometraje: Optional[float] = None
    intervalo_dias: Optional[int] = None
    intervalo_horas: Optional[float] = None
    estado_control: str
    activo: bool
    detalles: list[PlanDetalleMantenimientoResponse] = []

    class Config:
        from_attributes = True
