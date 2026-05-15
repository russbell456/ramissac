from __future__ import annotations

from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base
class RQItem(Base):
    __tablename__ = "rq_items"
    id = Column(Integer, primary_key=True)
    codigo = Column(String)
    descripcion = Column(String)
    cantidad = Column(Integer)
    unidad = Column(String)
    estado = Column(String, default="pendiente")  # pendiente, comprando, comprado
    rq_id = Column(Integer, ForeignKey("requerimientos.id"))
    requerimiento = relationship("Requerimiento", back_populates="items")
    ordenes_compra_items = relationship(
        "OrdenCompraItem", 
        back_populates="rq_item",
        cascade="all, delete-orphan"
    )