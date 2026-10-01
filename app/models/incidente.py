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


class Incidente(Base):
    """Incidente de operación: accidentes, incidentes y novedades."""

    __tablename__ = "incidentes"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True)
    ruta_id = Column(Integer, ForeignKey("rutas_asignaciones.id"), nullable=True)
    # Valores: accidente, incidente, novedad
    tipo = Column(String, default="incidente", nullable=False)
    # Valores: reportado, en_evaluacion, cerrado
    estado = Column(String, default="reportado", nullable=False)
    fecha_reporte = Column(DateTime, default=datetime.utcnow, nullable=False)
    descripcion = Column(Text, nullable=False)
    afecta_personas = Column(Boolean, default=False, nullable=False)
    # Columna "dano_vehiculo" (sin ñ en BD) para consistencia con la migración.
    dano_vehiculo = Column("dano_vehiculo", Boolean, default=False, nullable=False)
    requiere_acta = Column(Boolean, default=False, nullable=False)
    registrado_por = Column(Integer, ForeignKey("users.id"), nullable=True)
    observaciones = Column(Text, nullable=True)

    vehiculo = relationship("Vehiculo", back_populates="incidentes")
    averias = relationship(
        "Averia",
        back_populates="origen_incidente",
        foreign_keys="Averia.origen_incidente_id",
    )

