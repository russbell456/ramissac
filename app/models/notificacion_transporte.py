from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from app.database.base import Base


class NotificacionTransporte(Base):
    __tablename__ = "notificaciones_transporte"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    clave = Column(String(180), nullable=False, unique=True)
    titulo = Column(String(160), nullable=False)
    mensaje = Column(Text, nullable=False)
    entidad = Column(String(30), nullable=True)
    entidad_id = Column(Integer, nullable=True)
    persistente = Column(Boolean, default=False, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)
    leida = Column(Boolean, default=False, nullable=False)
    push_enviado = Column(Boolean, default=False, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)


class DispositivoPush(Base):
    __tablename__ = "dispositivos_push"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(512), unique=True, nullable=False)
