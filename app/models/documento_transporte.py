from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String

from app.database.base import Base


class DocumentoTransporte(Base):
    __tablename__ = "documentos_transporte"

    id = Column(Integer, primary_key=True, index=True)
    entidad = Column(String(20), nullable=False, index=True)
    entidad_id = Column(Integer, nullable=False, index=True)
    tipo = Column(String(50), nullable=False, index=True)
    archivo_url = Column(String(500), nullable=True)
    fecha_vencimiento = Column(Date, nullable=True)
    estado = Column(String(20), default="pendiente", nullable=False)
    aprobado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_aprobacion = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    archivado = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
