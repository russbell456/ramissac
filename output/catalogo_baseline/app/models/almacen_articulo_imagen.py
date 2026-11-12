from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base


class AlmacenArticuloImagen(Base):
    __tablename__ = "almacen_articulo_imagenes"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    articulo_id = Column(
        Integer,
        ForeignKey(
            "almacen_articulos.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    nombre_archivo = Column(
        String(255),
        nullable=False,
    )

    ruta = Column(
        String(500),
        nullable=False,
    )

    tipo_mime = Column(
        String(100),
        nullable=False,
    )

    fecha_creacion = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    articulo = relationship(
        "AlmacenArticulo",
        back_populates="imagenes",
    )