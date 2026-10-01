from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String, unique=True, index=True, nullable=False)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    capacidad_carga = Column(Float, nullable=False)
    # Kilometraje actual monotónico (nunca puede disminuir)
    kilometraje_actual = Column(Float, default=0.0, nullable=False)
    # Valores válidos centralizados en transportes_enums.EstadoVehiculo
    estado = Column(String, default="disponible", nullable=False)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    asignaciones = relationship("RutaAsignacion", back_populates="vehiculo", cascade="all, delete-orphan")
    jornadas = relationship("JornadaTransporte", back_populates="vehiculo", cascade="all, delete-orphan")
    mantenimientos = relationship("Mantenimiento", back_populates="vehiculo", cascade="all, delete-orphan")
    inspecciones = relationship("Inspeccion", back_populates="vehiculo", cascade="all, delete-orphan")
    averias = relationship("Averia", back_populates="vehiculo", cascade="all, delete-orphan")
    incidentes = relationship("Incidente", back_populates="vehiculo", cascade="all, delete-orphan")
    planes_mantenimiento = relationship(
        "PlanMantenimiento",
        back_populates="vehiculo",
        cascade="all, delete-orphan",
    )
