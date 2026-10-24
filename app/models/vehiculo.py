from __future__ import annotations
from sqlalchemy import Column, Date, Integer, String, Float, DateTime, ForeignKey
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
    estado_semaforo = Column(String(20), default="verde", nullable=False)
    tipo = Column(String(40), nullable=True)
    capacidad_tanque_galones = Column(Float, nullable=True)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)
    soat_vencimiento = Column(Date, nullable=True)
    rt_vencimiento = Column(Date, nullable=True)
    tarjeta_propiedad_url = Column(String(500), nullable=True)
    poliza_vencimiento = Column(Date, nullable=True)
    pase_minero_vencimiento = Column(Date, nullable=True)

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

    @property
    def observaciones_pendientes(self):
        if self.estado_semaforo == "verde":
            return None
        severidad = "critica" if self.estado_semaforo == "rojo" else "moderada"
        reportes = [j for j in self.jornadas if j.severidad == severidad and j.observaciones and not j.observacion_resuelta]
        if reportes:
            return max(reportes, key=lambda j: j.id).observaciones
        return "Falla crítica pendiente de revisión" if severidad == "critica" else "Observaciones moderadas pendientes de revisión"
