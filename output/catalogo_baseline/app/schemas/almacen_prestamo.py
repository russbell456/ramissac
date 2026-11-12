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
    OBRA = "obra"
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

    foto_estado_inicio: str | None = Field(
        default=None,
        min_length=1,
    )


class SolicitudPrestamoData(BaseModel):
    """Datos que solicita el trabajador antes de la entrega."""

    fecha_devolucion_prevista: datetime
    items: list[ItemPrestamo] = Field(..., min_length=1)
    tipo_prestamo: TipoPrestamoSchema = TipoPrestamoSchema.INTERNO
    obra_id: int | None = Field(default=None, gt=0)
    empresa_ruc: str | None = Field(default=None, min_length=1, max_length=20)
    empresa_nombre: str | None = Field(default=None, min_length=1, max_length=150)
    persona_dni: str | None = Field(default=None, pattern=r"^\d{8}$")
    persona_nombres: str | None = Field(default=None, min_length=1, max_length=150)
    persona_telefono: str | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode="after")
    def validar_solicitud(self):
        ids = [item.articulo_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("No se puede repetir un artículo en la solicitud")

        datos_externos = any([
            self.empresa_ruc,
            self.empresa_nombre,
            self.persona_dni,
            self.persona_nombres,
            self.persona_telefono,
        ])

        if self.tipo_prestamo == TipoPrestamoSchema.INTERNO:
            if self.obra_id is not None or datos_externos:
                raise ValueError(
                    "Un préstamo interno no debe asociarse a obra ni incluir datos externos"
                )
        elif self.tipo_prestamo == TipoPrestamoSchema.OBRA:
            if self.obra_id is None:
                raise ValueError("Un préstamo para obra debe indicar una obra")
            if datos_externos:
                raise ValueError("Un préstamo para obra no debe incluir datos externos")
        else:
            if self.obra_id is not None:
                raise ValueError("Un préstamo externo no puede asociarse a una obra")
            if not all([
                self.empresa_ruc,
                self.empresa_nombre,
                self.persona_dni,
                self.persona_nombres,
                self.persona_telefono,
            ]):
                raise ValueError(
                    "El préstamo externo requiere RUC, empresa y datos completos del responsable"
                )
        return self


class FotoArticuloPrestamo(BaseModel):
    articulo_id: int = Field(..., gt=0)
    foto_estado_inicio: str = Field(..., min_length=1)


class ConfirmacionSolicitudPrestamo(BaseModel):
    firma_base64: str = Field(..., min_length=1)
    fotos: list[FotoArticuloPrestamo] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_fotos_sin_duplicados(self):
        ids = [foto.articulo_id for foto in self.fotos]
        if len(ids) != len(set(ids)):
            raise ValueError("No se puede repetir la foto de un artículo")
        return self


class SolicitudPrestamoCreada(BaseModel):
    id: int
    codigo_unico: str
    estado: str
    message: str = "Solicitud creada; el stock no se modifica hasta confirmar la entrega"


class PrestamoDetalleSchema(BaseModel):
    id: int
    articulo_id: int
    cantidad_prestada: int
    cantidad_devuelta: int
    cantidad_pendiente: int
    esta_devuelto: bool
    requiere_devolucion: bool
    requiere_foto_devolucion: bool = False

    articulo_nombre: str
    articulo_tipo: str
    articulo_unidad: str
    foto_estado_inicio_url: str | None = Field(
        default=None,
        validation_alias="foto_estado_inicio",
    )
    foto_estado_fin_url: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class PrestamoDevolucionDetalleSchema(BaseModel):
    prestamo_detalle_id: int
    cantidad_devuelta: int
    foto_estado_fin_url: str | None = None


class PrestamoDevolucionSchema(BaseModel):
    id: int
    codigo_unico: str
    fecha_devolucion: datetime
    almacenero_id: int | None = None
    almacenero_nombre: str | None = None
    firma_url: str | None = None
    detalles: list[PrestamoDevolucionDetalleSchema]


class SolicitudPrestamoResumen(BaseModel):
    id: int
    trabajador_id: int
    nombres_completos: str
    dni: str
    cargo: str
    codigo_unico: str
    fecha_devolucion_prevista: datetime
    estado: str
    tipo_prestamo: str
    obra_id: int | None
    empresa_ruc: str | None
    empresa_nombre: str | None
    persona_dni: str | None
    persona_nombres: str | None
    persona_telefono: str | None
    detalles: list[PrestamoDetalleSchema]


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
        deprecated=True,
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

        datos_externos = any([
            self.empresa_ruc,
            self.empresa_nombre,
            self.persona_dni,
            self.persona_nombres,
            self.persona_telefono,
        ])

        if self.tipo_prestamo == TipoPrestamoSchema.INTERNO:
            if self.obra_id is not None:
                raise ValueError(
                    "Un préstamo interno no debe indicar una obra"
                )
            if datos_externos:
                raise ValueError(
                    "Un préstamo interno no debe contener datos externos"
                )

        if self.tipo_prestamo == TipoPrestamoSchema.OBRA:
            if self.obra_id is None:
                raise ValueError(
                    "Un préstamo para obra debe indicar una obra"
                )
            if datos_externos:
                raise ValueError(
                    "Un préstamo para obra no debe contener datos externos"
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

        if self.foto_estado_inicio and len(self.items) != 1:
            raise ValueError(
                "Envía la foto dentro del artículo correspondiente"
            )

        return self


class PrestamoResponse(BaseModel):
    id: int
    codigo_unico: str
    estado: str
    pdf_url: str | None = None

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

    firma_url: str | None = Field(
        default=None,
        validation_alias="firma_base64",
    )

    estado: str
    registrado_por: str
    almacenero_id: int | None = None
    almacenero_nombre: str | None = None
    fecha_registro: datetime

    tipo_prestamo: str
    obra_id: int | None

    empresa_ruc: str | None
    empresa_nombre: str | None

    persona_dni: str | None
    persona_nombres: str | None
    persona_telefono: str | None

    detalles: list[PrestamoDetalleSchema]
    devoluciones: list[PrestamoDevolucionSchema] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
