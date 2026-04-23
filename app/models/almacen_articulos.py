from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, Boolean, JSON, Any
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
import enum
class TipoArticulo(enum.Enum):
    EQUIPO = "equipo"
    CONSUMIBLE = "consumible"
class AlmacenArticulo(Base):
    __tablename__ = "almacen_articulos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    unidad_medida = Column(String)
    tipo = Column(Enum(TipoArticulo), nullable=False)
    stock_actual = Column(Integer, default=0)
    codigo_excel = Column(String, unique=True, index=True)
