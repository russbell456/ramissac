from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base

class Envio(Base):
    __tablename__ = "envios"

    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"))
    cantidad_enviada = Column(Integer, nullable=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)
    empresa_transporte = Column(String, nullable=True)
    estado_envio = Column(String, default="EN_TRANSITO")  
    # PENDIENTE – EN_TRANSITO – ENTREGADO – INCIDENCIA

    compra = relationship("Compra", back_populates="envios")
