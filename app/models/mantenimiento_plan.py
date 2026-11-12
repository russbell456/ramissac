from __future__ import annotations

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class PlanMantenimiento(Base):
    """Plan de mantenimiento preventivo programado para un vehículo."""

    __tablename__ = "planes_mantenimiento"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    # Valores: kilometraje, fecha, horas, mixto
    tipo_control = Column(String, default="mixto", nullable=False)
    # Umbrales de control (mixto usa el primero que se cumpla)
    intervalo_kilometraje = Column(Float, nullable=True)
    intervalo_dias = Column(Integer, nullable=True)
    intervalo_horas = Column(Float, nullable=True)
    # Valores: NORMAL, PROXIMO, VENCIDO
    estado_control = Column(String, default="NORMAL", nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    vehiculo = relationship("Vehiculo", back_populates="planes_mantenimiento")
    detalles = relationship(
        "PlanDetalleMantenimiento",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class PlanDetalleMantenimiento(Base):
    """Detalle de un ítem de un plan de mantenimiento preventivo."""

    __tablename__ = "plan_detalles_mantenimiento"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("planes_mantenimiento.id"),
        nullable=False,
    )
    descripcion = Column(Text, nullable=False)
    orden = Column(Integer, default=0, nullable=False)

    plan = relationship("PlanMantenimiento", back_populates="detalles")

