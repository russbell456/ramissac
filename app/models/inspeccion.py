from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class ChecklistItem(Base):
    """Ítems reutilizables del checklist de inspección de vehículos."""

    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    # Valores válidos: baja, media, alta, critica (validados en servicio)
    criticidad = Column(String, default="media", nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    detalles = relationship("InspeccionDetalle", back_populates="item")


class Inspeccion(Base):
    """Inspección de un vehículo (SALIDA, LLEGADA, POST_MANTENIMIENTO, etc.)."""

    __tablename__ = "inspecciones"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    ruta_id = Column(Integer, ForeignKey("rutas_asignaciones.id"), nullable=True)
    # Valores válidos: SALIDA, LLEGADA, EXTRAORDINARIA, POST_ACCIDENTE,
    # POST_MANTENIMIENTO (validados en servicio)
    tipo = Column(String, nullable=False)
    # Valores válidos: APROBADA, APROBADA_CON_OBSERVACIONES, RECHAZADA
    resultado = Column(String, nullable=True)
    realizada_por = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    observaciones = Column(Text, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)

    vehiculo = relationship("Vehiculo", back_populates="inspecciones")
    ruta = relationship(
        "RutaAsignacion",
        back_populates="inspecciones",
        foreign_keys=[ruta_id],
    )
    detalles = relationship(
        "InspeccionDetalle",
        back_populates="inspeccion",
        cascade="all, delete-orphan",
    )
    realizador = relationship("User", foreign_keys=[realizada_por])


class InspeccionDetalle(Base):
    """Resultado de un ítem del checklist dentro de una inspección."""

    __tablename__ = "inspeccion_detalles"

    id = Column(Integer, primary_key=True, index=True)
    inspeccion_id = Column(
        Integer,
        ForeignKey("inspecciones.id"),
        nullable=False,
    )
    item_id = Column(
        Integer,
        ForeignKey("checklist_items.id"),
        nullable=False,
    )
    # Valores válidos: conforme, observado, no_conforme, no_aplica
    resultado = Column(String, nullable=False)
    comentario = Column(Text, nullable=True)

    inspeccion = relationship("Inspeccion", back_populates="detalles")
    item = relationship("ChecklistItem", back_populates="detalles")

