from datetime import datetime

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

    fecha_devolucion: datetime

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

        return self


class DevolucionResponse(BaseModel):

    id: int

    codigo_unico: str

    estado: str

    message: str = (
        "Devolución registrada correctamente"
    )

    model_config = ConfigDict(
        from_attributes=True
    )