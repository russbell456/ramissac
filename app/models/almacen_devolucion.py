from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Text, String
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import enum

class EstadoDevolucion(enum.Enum):
    CONFIRMADA = "confirmada"

class AlmacenDevolucion(Base):
    __tablename__ = "almacen_devoluciones"

    id = Column(Integer, primary_key=True, index=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    almacenero_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    codigo_unico = Column(String, unique=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("almacen_prestamos.id"), nullable=True)  # Referencia al préstamo original
    fecha_devolucion = Column(DateTime, nullable=False)
    firma_base64 = Column(Text, nullable=False)
    estado = Column(Enum(EstadoDevolucion), default=EstadoDevolucion.CONFIRMADA)
    registrado_por = Column(String, default="almacenero")
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    detalles = relationship("AlmacenDevolucionDetalle", back_populates="devolucion")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    almacenero = relationship("User", foreign_keys=[almacenero_id])
    prestamo = relationship("AlmacenPrestamo", foreign_keys=[prestamo_id])

class AlmacenDevolucionDetalle(Base):
    __tablename__ = "almacen_devolucion_detalles"

    id = Column(Integer, primary_key=True, index=True)
    devolucion_id = Column(Integer, ForeignKey("almacen_devoluciones.id"))
    prestamo_detalle_id = Column(Integer, ForeignKey("almacen_prestamo_detalles.id"))
    cantidad_devuelta = Column(Integer, nullable=False)

    devolucion = relationship("AlmacenDevolucion", back_populates="detalles")
    prestamo_detalle = relationship("AlmacenPrestamoDetalle")