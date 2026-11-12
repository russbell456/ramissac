from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime
)

from datetime import datetime

from app.database.base import Base


class AlmacenAuditoria(Base):

    __tablename__ = "almacen_auditoria"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    usuario_id = Column(
        Integer,
        nullable=False
    )

    accion = Column(
        String(100),
        nullable=False
    )

    entidad = Column(
        String(100),
        nullable=False
    )

    entidad_id = Column(
        Integer,
        nullable=False
    )

    descripcion = Column(
        Text,
        nullable=True
    )

    fecha = Column(
        DateTime,
        default=datetime.utcnow
    )