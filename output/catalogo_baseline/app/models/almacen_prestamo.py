import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class EstadoPrestamo(enum.Enum):
    PENDIENTE = "pendiente"
    ABIERTO = "abierto"
    CERRADO = "cerrado"


class TipoPrestamo(enum.Enum):
    INTERNO = "interno"
    OBRA = "obra"
    EXTERNO = "externo"


class AlmacenPrestamo(Base):
    __tablename__ = "almacen_prestamos"

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

    obra_id = Column(
        Integer,
        ForeignKey("almacen_obras.id"),
        nullable=True,
    )

    codigo_unico = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    fecha_prestamo = Column(
        DateTime,
        nullable=False,
    )

    fecha_devolucion_prevista = Column(
        DateTime,
        nullable=False,
    )

    # New records store a relative file path here. Existing Base64 rows remain
    # readable until their retention/migration policy is decided.
    firma_base64 = Column(
        Text,
        nullable=True,
    )

    estado = Column(
        Enum(EstadoPrestamo),
        default=EstadoPrestamo.ABIERTO,
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

    tipo_prestamo = Column(
        Enum(TipoPrestamo),
        default=TipoPrestamo.INTERNO,
        nullable=False,
    )

    # Datos de préstamo externo
    empresa_ruc = Column(
        String(20),
        nullable=True,
    )

    empresa_nombre = Column(
        String(150),
        nullable=True,
    )

    persona_dni = Column(
        String(8),
        nullable=True,
    )

    persona_nombres = Column(
        String(150),
        nullable=True,
    )

    persona_telefono = Column(
        String(20),
        nullable=True,
    )

    # Legacy compatibility: new photos are stored on each detail as file paths.
    foto_estado_inicio = Column(
        Text,
        nullable=True,
    )

    detalles = relationship(
        "AlmacenPrestamoDetalle",
        back_populates="prestamo",
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

    devoluciones = relationship(
        "AlmacenDevolucion",
        back_populates="prestamo",
        cascade="all, delete-orphan",
        order_by="AlmacenDevolucion.fecha_devolucion",
    )

    obra = relationship(
        "AlmacenObra",
        back_populates="prestamos",
    )


class AlmacenPrestamoDetalle(Base):
    __tablename__ = "almacen_prestamo_detalles"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    prestamo_id = Column(
        Integer,
        ForeignKey("almacen_prestamos.id"),
        nullable=False,
    )

    articulo_id = Column(
        Integer,
        ForeignKey("almacen_articulos.id"),
        nullable=False,
    )

    cantidad_prestada = Column(
        Integer,
        nullable=False,
    )

    cantidad_devuelta = Column(
        Integer,
        default=0,
        nullable=False,
    )

    esta_devuelto = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relative file path for new article evidence; legacy Base64 remains readable.
    foto_estado_inicio = Column(
        Text,
        nullable=True,
    )

    prestamo = relationship(
        "AlmacenPrestamo",
        back_populates="detalles",
    )

    articulo = relationship(
        "AlmacenArticulo",
    )
