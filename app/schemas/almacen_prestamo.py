from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class TipoArticuloSchema(str, Enum):
    EQUIPO = "equipo"
    HERRAMIENTA = "herramienta"
    CONSUMIBLE = "consumible"


class TipoPrestamoSchema(str, Enum):
    INTERNO = "interno"
    EXTERNO = "externo"


class ItemPrestamo(BaseModel):
    articulo_id: int = Field(
        ...,
        gt=0,
    )

    cantidad: int = Field(
        ...,
        gt=0,
    )


class PrestamoDetalleSchema(BaseModel):
    id: int
    articulo_id: int
    cantidad_prestada: int
    cantidad_devuelta: int
    cantidad_pendiente: int
    esta_devuelto: bool
    requiere_devolucion: bool

    articulo_nombre: str
    articulo_tipo: str
    articulo_unidad: str

    model_config = ConfigDict(
        from_attributes=True
    )


class PrestamoQRData(BaseModel):
    trabajador_id: int = Field(
        ...,
        gt=0,
    )

    codigo_unico: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    dni: str = Field(
        ...,
        pattern=r"^\d{8}$",
    )

    nombres_completos: str = Field(
        ...,
        min_length=2,
    )

    cargo: str = Field(
        ...,
        min_length=1,
    )

    fecha_prestamo: datetime

    fecha_devolucion_prevista: datetime

    items: list[ItemPrestamo] = Field(
        ...,
        min_length=1,
    )

    firma_base64: str = Field(
        ...,
        min_length=1,
    )

    obra_id: int | None = Field(
        default=None,
        gt=0,
    )

    tipo_prestamo: TipoPrestamoSchema = (
        TipoPrestamoSchema.INTERNO
    )

    empresa_ruc: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    empresa_nombre: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    persona_dni: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
    )

    persona_nombres: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    persona_telefono: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    foto_estado_inicio: str | None = Field(
        default=None,
        min_length=1,
    )

    @model_validator(mode="after")
    def validar_prestamo(self):

        # -----------------------------------------
        # FECHAS
        # -----------------------------------------

        if (
            self.fecha_devolucion_prevista
            <= self.fecha_prestamo
        ):
            raise ValueError(
                "La fecha de devolución prevista "
                "debe ser posterior a la fecha "
                "del préstamo"
            )

        # -----------------------------------------
        # ARTÍCULOS DUPLICADOS
        # -----------------------------------------

        ids = [
            item.articulo_id
            for item in self.items
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "No se puede repetir el mismo "
                "artículo dentro del préstamo"
            )

        # -----------------------------------------
        # PRÉSTAMO INTERNO
        # -----------------------------------------

        if (
            self.tipo_prestamo
            == TipoPrestamoSchema.INTERNO
        ):

            if self.obra_id is None:
                raise ValueError(
                    "Los préstamos internos "
                    "deben indicar una obra"
                )

            if any([
                self.empresa_ruc,
                self.empresa_nombre,
                self.persona_dni,
                self.persona_nombres,
                self.persona_telefono,
            ]):
                raise ValueError(
                    "Un préstamo interno no debe "
                    "contener datos de empresa "
                    "ni responsable externo"
                )

        # -----------------------------------------
        # PRÉSTAMO EXTERNO
        # -----------------------------------------

        if (
            self.tipo_prestamo
            == TipoPrestamoSchema.EXTERNO
        ):

            if self.obra_id is not None:
                raise ValueError(
                    "Un préstamo externo "
                    "no puede estar asociado a una obra"
                )

            if not self.empresa_ruc:
                raise ValueError(
                    "El RUC es obligatorio "
                    "para préstamos externos"
                )

            if not self.empresa_nombre:
                raise ValueError(
                    "El nombre de la empresa es obligatorio"
                )

            if not self.persona_dni:
                raise ValueError(
                    "El DNI del responsable "
                    "es obligatorio"
                )

            if not self.persona_nombres:
                raise ValueError(
                    "El nombre del responsable "
                    "es obligatorio"
                )

            if not self.persona_telefono:
                raise ValueError(
                    "El teléfono del responsable "
                    "es obligatorio"
                )

        return self


class PrestamoResponse(BaseModel):
    id: int
    codigo_unico: str
    estado: str

    message: str = (
        "Préstamo registrado correctamente"
    )


class ArticuloPrestamoSchema(BaseModel):
    trabajador_id: int
    nombres_completos: str
    dni: str
    cargo: str
    fecha_prestamo: datetime
    cantidad_pendiente: int


class PrestamoSchema(BaseModel):
    id: int
    trabajador_id: int

    nombres_completos: str
    dni: str
    cargo: str

    codigo_unico: str

    fecha_prestamo: datetime
    fecha_devolucion_prevista: datetime

    firma_base64: str

    estado: str
    registrado_por: str
    fecha_registro: datetime

    tipo_prestamo: str
    obra_id: int | None

    empresa_ruc: str | None
    empresa_nombre: str | None

    persona_dni: str | None
    persona_nombres: str | None
    persona_telefono: str | None

    detalles: list[PrestamoDetalleSchema]

    model_config = ConfigDict(
        from_attributes=True
    )