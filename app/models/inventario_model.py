from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base # Asumo que tienes tu Base definida aquí

class Inventario(Base):
    """
    Representa el stock físico de un producto, agrupado por su código único.
    """
    __tablename__ = 'inventario'

    id = Column(Integer, primary_key=True, index=True)
    
    # Clave principal para el stock: basada en el código del RQItem (ej: PD03758)
    codigo = Column(String, unique=True, index=True, nullable=False)
    descripcion = Column(String, nullable=False)
    
    cantidad_disponible = Column(Integer, default=0, nullable=False)
    
    # Campo para indicar dónde se recibió o almacena el producto (Usaremos ubicacion_envio de la OC)
    ubicacion = Column(String, nullable=True) 

    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_inventario_codigo', 'codigo'),
    )