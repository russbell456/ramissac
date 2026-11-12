from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database.base import Base


class AlmacenTercero(Base):
    __tablename__ = "almacen_terceros"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False, default="empresa")
    ruc = Column(String, nullable=True)
    dni = Column(String, nullable=True)
    nombres = Column(String, nullable=True)
    empresa_nombre = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
