from __future__ import annotations
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime
from app.database.base import Base

class Inventario(Base):
    __tablename__ = "inventario_movil"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    cantidad_recibida = Column(Integer, default=0)
    cantidad_entregada = Column(Integer, default=0)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
