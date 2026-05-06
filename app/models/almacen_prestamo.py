from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import enum

class EstadoPrestamo(enum.Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"

class AlmacenPrestamo(Base):
    __tablename__ = "almacen_prestamos"

    id = Column(Integer, primary_key=True, index=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ID del trabajador real (del login)
    almacenero_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # ID del almacenero que confirma
    codigo_unico = Column(String, unique=True, index=True)                   # Correlativo 56, 23, etc.
    fecha_prestamo = Column(DateTime, nullable=False)
    fecha_devolucion_prevista = Column(DateTime, nullable=False)
    firma_base64 = Column(Text, nullable=False)                              # Firma del trabajador
    estado = Column(Enum(EstadoPrestamo), default=EstadoPrestamo.ABIERTO)
    registrado_por = Column(String, default="almacenero")
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    detalles = relationship("AlmacenPrestamoDetalle", back_populates="prestamo")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    almacenero = relationship("User", foreign_keys=[almacenero_id])

class AlmacenPrestamoDetalle(Base):
    __tablename__ = "almacen_prestamo_detalles"

    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("almacen_prestamos.id"))
    articulo_id = Column(Integer, ForeignKey("almacen_articulos.id"))
    cantidad_prestada = Column(Integer, nullable=False)
    cantidad_devuelta = Column(Integer, default=0)
    esta_devuelto = Column(Boolean, default=False)

    prestamo = relationship("AlmacenPrestamo", back_populates="detalles")
    articulo = relationship("AlmacenArticulo")