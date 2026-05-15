from __future__ import annotations

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.database.base import Base

class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    mensaje = Column(String)
    fecha = Column(DateTime, default=datetime.utcnow)
    leido = Column(Boolean, default=False)
