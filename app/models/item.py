from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    rq_id = Column(Integer, ForeignKey("requerimientos.id"))
    nombre = Column(String, nullable=False)

    cantidad_solicitada = Column(Integer, nullable=False)
    cantidad_aprobada = Column(Integer, default=0)
    cantidad_comprada = Column(Integer, default=0)

    estado_item = Column(String, default="PENDIENTE")  
    # Estados:
    # PENDIENTE, APROBADO, COMPRA_PARCIAL, COMPRADO, ENVIADO, RECIBIDO

    requerimiento = relationship("Requerimiento", back_populates="items")
    compras = relationship("Compra", back_populates="item")
