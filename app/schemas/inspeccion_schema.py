from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

from app.models.transportes_enums import (
    CriticidadItem,
    EstadoInspeccion,
    ResultadoChecklist,
    TipoInspeccion,
)


class ChecklistItemCreate(BaseModel):
    codigo: str = Field(..., description="Código único del ítem")
    nombre: str = Field(..., description="Nombre del ítem")
    descripcion: Optional[str] = None
    criticidad: str = Field(default="media", description="baja|media|alta|critica")
    activo: bool = True

    @field_validator("criticidad", mode="after")
    @classmethod
    def _validar_criticidad(cls, v: str) -> str:
        valores = {c.value for c in CriticidadItem}
        if v not in valores:
            raise ValueError(f"Criticidad inválida: {v}.")
        return v


class ChecklistItemResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    criticidad: str
    activo: bool

    class Config:
        from_attributes = True


class InspeccionDetalleCreate(BaseModel):
    item_id: int = Field(..., description="ID del ítem del checklist")
    resultado: str = Field(..., description="conforme|observado|no_conforme|no_aplica")
    comentario: Optional[str] = None

    @field_validator("resultado", mode="after")
    @classmethod
    def _validar_resultado(cls, v: str) -> str:
        valores = {r.value for r in ResultadoChecklist}
        if v not in valores:
            raise ValueError(f"Resultado inválido: {v}.")
        return v


class InspeccionCreate(BaseModel):
    vehiculo_id: int = Field(..., description="ID del vehículo")
    ruta_id: Optional[int] = None
    tipo: str = Field(..., description="SALIDA|LLEGADA|EXTRAORDINARIA|POST_ACCIDENTE|POST_MANTENIMIENTO")
    observaciones: Optional[str] = None
    detalles: list[InspeccionDetalleCreate] = []

    @field_validator("tipo", mode="after")
    @classmethod
    def _validar_tipo(cls, v: str) -> str:
        valores = {t.value for t in TipoInspeccion}
        if v not in valores:
            raise ValueError(f"Tipo de inspección inválido: {v}.")
        return v


class InspeccionResolver(BaseModel):
    """Cuerpo para resolver (aprobar/rechazar) una inspección pendiente."""
    resultado: str = Field(..., description="APROBADA|APROBADA_CON_OBSERVACIONES|RECHAZADA")
    observaciones: Optional[str] = None

    @field_validator("resultado", mode="after")
    @classmethod
    def _validar_resultado(cls, v: str) -> str:
        valores = {r.value for r in EstadoInspeccion}
        if v not in valores:
            raise ValueError(f"Resultado de inspección inválido: {v}.")
        return v


class InspeccionDetalleResponse(BaseModel):
    id: int
    item_id: int
    resultado: str
    comentario: Optional[str] = None
    item: Optional[ChecklistItemResponse] = None

    class Config:
        from_attributes = True


class InspeccionResponse(BaseModel):
    id: int
    vehiculo_id: int
    ruta_id: Optional[int] = None
    tipo: str
    resultado: Optional[str] = None
    realizada_por: Optional[int] = None
    fecha: datetime
    observaciones: Optional[str] = None
    activa: bool
    detalles: list[InspeccionDetalleResponse] = []

    class Config:
        from_attributes = True
