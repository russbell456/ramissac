from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Float, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    averia_id = Column(Integer, ForeignKey("averias.id"), nullable=True)
    plan_id = Column(
        Integer,
        ForeignKey("planes_mantenimiento.id"),
        nullable=True,
    )
    fecha_ingreso = Column(DateTime, nullable=False)
    descripcion_falla = Column(String, nullable=False)
    costo = Column(Float, nullable=False)
    # Nuevos campos para mantenimiento preventivo/correctivo.
    # Se mantienen como String en BD para no romper compatibilidad con el
    # código existente; los enums Python validan los valores en el servicio.
    tipo = Column(String, default="CORRECTIVO", nullable=False)
    mecanico_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    kilometraje_mantenimiento = Column(Float, nullable=True)
    proximo_kilometraje_mantenimiento = Column(Float, nullable=True)
    fecha = Column(DateTime, nullable=True)
    descripcion_trabajo = Column(Text, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    tipo_control = Column(String, nullable=True)  # kilometraje, fecha, horas, mixto
    intervalo_kilometraje = Column(Float, nullable=True)
    intervalo_dias = Column(Integer, nullable=True)
    intervalo_horas = Column(Float, nullable=True)
    km_ejecucion = Column(Float, nullable=True)
    horas_ejecucion = Column(Float, nullable=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    observaciones_ejecucion = Column(Text, nullable=True)
    estado = Column(String, default="en_taller", nullable=False)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo", back_populates="mantenimientos")
    averia = relationship("Averia", back_populates="mantenimientos")
    plan = relationship("PlanMantenimiento")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    mecanico = relationship("User", foreign_keys=[mecanico_id])
