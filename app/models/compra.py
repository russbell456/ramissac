from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base

class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    cantidad_comprada = Column(Integer, nullable=False)
    proveedor = Column(String, nullable=True)
    costo_unitario = Column(Float, nullable=True)
    fecha_compra = Column(DateTime, default=datetime.utcnow)
    origen_compra = Column(String, nullable=True)   # Lima, Local, Externo

    item = relationship("Item", back_populates="compras")
    envios = relationship("Envio", back_populates="compra")
