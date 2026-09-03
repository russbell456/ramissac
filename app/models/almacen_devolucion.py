from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class EstadoDevolucion(enum.Enum):
    CONFIRMADA = "confirmada"


class AlmacenDevolucion(Base):
    __tablename__ = "almacen_devoluciones"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    trabajador_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    almacenero_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    codigo_unico = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    prestamo_id = Column(
        Integer,
        ForeignKey("almacen_prestamos.id"),
        nullable=False,
    )

    fecha_devolucion = Column(
        DateTime,
        nullable=False,
    )

    firma_base64 = Column(
        Text,
        nullable=False,
    )

    estado = Column(
        Enum(EstadoDevolucion),
        default=EstadoDevolucion.CONFIRMADA,
        nullable=False,
    )

    registrado_por = Column(
        String(50),
        default="almacenero",
        nullable=False,
    )

    fecha_registro = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Evidencia fotográfica del estado
    # en el momento de la devolución.
    foto_estado_devuelto = Column(
        Text,
        nullable=True,
    )

    observacion_estado = Column(
        Text,
        nullable=True,
    )

    detalles = relationship(
        "AlmacenDevolucionDetalle",
        back_populates="devolucion",
        cascade="all, delete-orphan",
    )

    trabajador = relationship(
        "User",
        foreign_keys=[trabajador_id],
    )

    almacenero = relationship(
        "User",
        foreign_keys=[almacenero_id],
    )

    prestamo = relationship(
        "AlmacenPrestamo",
        foreign_keys=[prestamo_id],
    )


class AlmacenDevolucionDetalle(Base):
    __tablename__ = "almacen_devolucion_detalles"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    devolucion_id = Column(
        Integer,
        ForeignKey("almacen_devoluciones.id"),
        nullable=False,
    )

    prestamo_detalle_id = Column(
        Integer,
        ForeignKey("almacen_prestamo_detalles.id"),
        nullable=False,
    )

    cantidad_devuelta = Column(
        Integer,
        nullable=False,
    )

    devolucion = relationship(
        "AlmacenDevolucion",
        back_populates="detalles",
    )

    prestamo_detalle = relationship(
        "AlmacenPrestamoDetalle",
    )