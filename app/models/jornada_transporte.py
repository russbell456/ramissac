from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.database.base import Base


class JornadaTransporte(Base):
    __tablename__ = "jornadas_transporte"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True, index=True)
    conductor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String, default="en_curso", nullable=False, index=True)
    
    # Nuevos campos del registro de acción
    accion_tipo = Column(String, nullable=True)
    ruta = Column(String, nullable=True)
    nivel_combustible = Column(Integer, nullable=True)
    checklist_flash = Column(JSON, nullable=True)
    observaciones = Column(Text, nullable=True)

    vehiculo = relationship("Vehiculo", back_populates="jornadas")
    checklists = relationship(
        "Checklist",
        back_populates="jornada",
        cascade="all, delete-orphan",
        order_by="Checklist.id",
    )
    incidencias = relationship(
        "IncidenciaRuta",
        back_populates="jornada",
        cascade="all, delete-orphan",
        order_by="IncidenciaRuta.fecha",
    )


class Checklist(Base):
    __tablename__ = "checklists_transporte"

    id = Column(Integer, primary_key=True, index=True)
    jornada_id = Column(Integer, ForeignKey("jornadas_transporte.id"), nullable=False, index=True)
    tipo = Column(String, nullable=False)
    kilometraje = Column(Float, nullable=False)
    nivel_combustible = Column(String, nullable=False)
    estado_general = Column(String, nullable=False)
    conforme = Column(Boolean, nullable=False)
    observaciones = Column(Text, nullable=True)

    jornada = relationship("JornadaTransporte", back_populates="checklists")


class IncidenciaRuta(Base):
    __tablename__ = "incidencias_ruta"

    id = Column(Integer, primary_key=True, index=True)
    jornada_id = Column(Integer, ForeignKey("jornadas_transporte.id"), nullable=False, index=True)
    tipo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    jornada = relationship("JornadaTransporte", back_populates="incidencias")
