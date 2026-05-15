from __future__ import annotations
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base

class Requerimiento(Base):
    __tablename__ = "requerimientos"

    id = Column(Integer, primary_key=True, index=True)
    nro_rq = Column(String, unique=True, index=True)
    proyecto = Column(String, nullable=False)
    solicitante = Column(String, nullable=False)
    fecha_emision = Column(Date, default=datetime.utcnow)
    estado = Column(String, default="pendiente")  
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    estado_compra = Column(String, default="no_iniciado")
    progreso_compra = Column(Float, default=0.0)

    items = relationship("RQItem", back_populates="requerimiento", cascade="all, delete-orphan")
