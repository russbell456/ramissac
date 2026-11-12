import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class TipoArticulo(enum.Enum):
    EQUIPO = "EQUIPO"
    HERRAMIENTA = "HERRAMIENTA"
    CONSUMIBLE = "CONSUMIBLE"


class AlmacenArticulo(Base):
    __tablename__ = "almacen_articulos"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    nombre = Column(
        String(150),
        nullable=False,
    )

    marca = Column(
        String(100),
        nullable=True,
    )

    modelo = Column(
        String(150),
        nullable=True,
    )

    serie = Column(
        String(150),
        unique=True,
        nullable=True,
        index=True,
    )

    descripcion = Column(
        Text,
        nullable=True,
    )

    categoria = Column(
        String(100),
        nullable=True,
    )

    unidad_medida = Column(
        String(50),
        nullable=False,
    )

    tipo = Column(
        Enum(TipoArticulo),
        nullable=False,
    )

    codigo_excel = Column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    stock_total = Column(
        Integer,
        nullable=False,
        default=0,
    )

    stock_actual = Column(
        Integer,
        nullable=False,
        default=0,
    )

    en_prestamo = Column(
        Integer,
        nullable=False,
        default=0,
    )

    estado_fisico = Column(
        String(100),
        nullable=True,
    )

    costo_hora = Column(
        Numeric(10, 2),
        nullable=True,
    )

    costo_dia = Column(
        Numeric(10, 2),
        nullable=True,
    )

    costo_reposicion = Column(
        Numeric(10, 2),
        nullable=True,
    )

    requiere_foto_prestamo = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    requiere_foto_devolucion = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    es_activo_alto_valor = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    activo = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    fecha_baja = Column(
        DateTime,
        nullable=True,
    )

    imagenes = relationship(
        "AlmacenArticuloImagen",
        back_populates="articulo",
        cascade="all, delete-orphan",
    )