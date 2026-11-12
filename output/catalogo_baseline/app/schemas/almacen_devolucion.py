from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ItemDevolucion(BaseModel):

    prestamo_detalle_id: int = Field(
        ...,
        gt=0,
    )

    cantidad: int = Field(
        ...,
        gt=0,
    )

    foto_estado_devuelto: str | None = Field(
        default=None,
        min_length=1,
    )


class DevolucionQRData(BaseModel):

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

    # Compatibilidad: la fecha persistida siempre la asigna el servidor.
    fecha_devolucion: datetime | None = Field(
        default=None,
        deprecated=True,
    )

    prestamo_id: int = Field(
        ...,
        gt=0,
    )

    items: list[ItemDevolucion] = Field(
        ...,
        min_length=1,
    )

    firma_base64: str = Field(
        ...,
        min_length=1,
    )

    foto_estado_devuelto: str | None = Field(
        default=None,
        min_length=1,
    )

    observacion_estado: str | None = Field(
        default=None,
        min_length=1,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validar_devolucion(self):

        # ==========================================
        # ITEMS DUPLICADOS
        # ==========================================

        ids = [
            item.prestamo_detalle_id
            for item in self.items
        ]

        if len(ids) != len(set(ids)):

            raise ValueError(
                "No se puede repetir el mismo "
                "detalle del préstamo dentro "
                "de una devolución"
            )

        if self.foto_estado_devuelto and len(self.items) != 1:
            raise ValueError(
                "Envía la foto dentro del detalle correspondiente a cada artículo"
            )

        return self


class DevolucionDetalleResultado(BaseModel):
    prestamo_detalle_id: int
    cantidad_devuelta: int
    minutos_efectivos: int
    dias_tarifa: int
    minutos_residuales: int
    costo_hora_aplicado: Decimal | None
    costo_dia_aplicado: Decimal | None
    importe_informativo: Decimal
    foto_estado_fin_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DevolucionResponse(BaseModel):

    id: int

    codigo_unico: str

    estado: str

    fecha_devolucion: datetime

    detalles: list[DevolucionDetalleResultado]

    importe_informativo_total: Decimal
    almacenero_id: int | None = None
    almacenero_nombre: str | None = None
    firma_url: str | None = None

    message: str = (
        "Devolución registrada correctamente"
    )

    model_config = ConfigDict(
        from_attributes=True
    )
