from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class Averia(Base):
    """Avería de un vehículo con su ciclo de vida y criticidad."""

    __tablename__ = "averias"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    ruta_id = Column(Integer, ForeignKey("rutas_asignaciones.id"), nullable=True)
    descripcion = Column(Text, nullable=False)
    # Valores: baja, media, alta, critica
    criticidad = Column(String, default="media", nullable=False)
    # Valores: reportada, en_evaluacion, programada, en_reparacion, resuelta, cerrada
    estado = Column(String, default="reportada", nullable=False)
    origen_incidente_id = Column(
        Integer,
        ForeignKey("incidentes.id"),
        nullable=True,
    )
    fecha_reporte = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_resolucion = Column(DateTime, nullable=True)
    registrado_por = Column(Integer, ForeignKey("users.id"), nullable=True)
    detalle_resolucion = Column(Text, nullable=True)

    vehiculo = relationship("Vehiculo", back_populates="averias")
    mantenimientos = relationship("Mantenimiento", back_populates="averia")
    origen_incidente = relationship(
        "Incidente",
        back_populates="averias",
        foreign_keys=[origen_incidente_id],
    )

