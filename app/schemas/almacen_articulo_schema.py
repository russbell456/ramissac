from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class TipoArticuloSchema(str, Enum):
    EQUIPO = "EQUIPO"
    HERRAMIENTA = "HERRAMIENTA"
    CONSUMIBLE = "CONSUMIBLE"


class ArticuloCreateSchema(BaseModel):
    nombre: str = Field(
        min_length=2,
        max_length=150,
    )

    marca: str | None = Field(
        default=None,
        max_length=100,
    )

    modelo: str | None = Field(
        default=None,
        max_length=150,
    )

    serie: str | None = Field(
        default=None,
        max_length=150,
    )

    descripcion: str | None = None

    categoria: str | None = Field(
        default=None,
        max_length=100,
    )

    unidad_medida: str = Field(
        min_length=1,
        max_length=50,
    )

    tipo: TipoArticuloSchema

    codigo_excel: str | None = Field(
        default=None,
        max_length=100,
    )

    stock_total: int = Field(
        default=0,
        ge=0,
    )

    stock_actual: int = Field(
        default=0,
        ge=0,
    )

    costo_hora: Decimal | None = Field(
        default=None,
        ge=0,
    )

    costo_dia: Decimal | None = Field(
        default=None,
        ge=0,
    )

    costo_reposicion: Decimal | None = Field(
        default=None,
        ge=0,
    )

    requiere_foto_prestamo: bool = False

    requiere_foto_devolucion: bool = False

    es_activo_alto_valor: bool = False

    estado_fisico: str | None = Field(
        default=None,
        max_length=100,
    )


class ArticuloUpdateSchema(BaseModel):
    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    marca: str | None = Field(
        default=None,
        max_length=100,
    )

    modelo: str | None = Field(
        default=None,
        max_length=150,
    )

    serie: str | None = Field(
        default=None,
        max_length=150,
    )

    descripcion: str | None = None

    categoria: str | None = Field(
        default=None,
        max_length=100,
    )

    unidad_medida: str | None = Field(
        default=None,
        max_length=50,
    )

    tipo: TipoArticuloSchema | None = None

    codigo_excel: str | None = Field(
        default=None,
        max_length=100,
    )

    costo_hora: Decimal | None = Field(
        default=None,
        ge=0,
    )

    costo_dia: Decimal | None = Field(
        default=None,
        ge=0,
    )

    costo_reposicion: Decimal | None = Field(
        default=None,
        ge=0,
    )

    requiere_foto_prestamo: bool | None = None

    requiere_foto_devolucion: bool | None = None

    es_activo_alto_valor: bool | None = None

    estado_fisico: str | None = Field(
        default=None,
        max_length=100,
    )


class ArticuloImagenSchema(BaseModel):
    id: int
    nombre_archivo: str
    ruta: str
    tipo_mime: str
    fecha_creacion: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ArticuloSchema(BaseModel):
    id: int
    nombre: str
    marca: str | None
    modelo: str | None
    serie: str | None
    descripcion: str | None
    categoria: str | None
    unidad_medida: str
    tipo: TipoArticuloSchema
    codigo_excel: str | None
    stock_total: int
    stock_actual: int
    en_prestamo: int
    estado_fisico: str | None
    costo_hora: Decimal | None
    costo_dia: Decimal | None
    costo_reposicion: Decimal | None
    requiere_foto_prestamo: bool
    requiere_foto_devolucion: bool
    es_activo_alto_valor: bool
    activo: bool
    fecha_baja: datetime | None
    imagenes: list[ArticuloImagenSchema] = Field(
    default_factory=list
)

    model_config = ConfigDict(
        from_attributes=True,
    )