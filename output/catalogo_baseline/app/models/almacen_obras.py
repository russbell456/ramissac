from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base


class AlmacenObra(Base):
    __tablename__ = "almacen_obras"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    cliente = Column(String, nullable=True)
    ubicacion = Column(String, nullable=True)
    estado = Column(String, default="activo")
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    prestamos = relationship("AlmacenPrestamo", back_populates="obra")
