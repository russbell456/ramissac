from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text

from app.database.base import Base


class AuditoriaSistema(Base):
    __tablename__ = "auditoria_sistema"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entidad = Column(String(50), nullable=False, index=True)
    registro_id = Column(Integer, nullable=False, index=True)
    accion = Column(String(50), nullable=False)
    valores_anteriores = Column(JSON, nullable=True)
    valores_nuevos = Column(JSON, nullable=True)
    motivo = Column(Text, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
