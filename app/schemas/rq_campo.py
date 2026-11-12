from __future__ import annotations

import base64
import io
import re
from datetime import datetime
from decimal import Decimal

from PIL import Image
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.rq_campo import EstadoRqCampo, EstadoItemRq, TipoItemRqCampo


class RqAdjuntoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    tipo_mime: str
    contenido_base64: str = Field(max_length=7_000_000)

    @model_validator(mode="after")
    def validar_archivo(self):
        self.nombre = self.nombre.strip()
        if not self.nombre or any(c in self.nombre for c in ("/", "\\", "\r", "\n")):
            raise ValueError("Nombre de adjunto inválido")
        try:
            datos = base64.b64decode(self.contenido_base64, validate=True)
        except Exception as exc:
            raise ValueError("El adjunto no contiene base64 válido") from exc
        if not datos or len(datos) > 5 * 1024 * 1024:
            raise ValueError("Cada adjunto debe ocupar entre 1 byte y 5 MB")
        if self.tipo_mime == "application/pdf":
            if not datos.startswith(b"%PDF-"):
                raise ValueError("El archivo no es un PDF")
        elif self.tipo_mime in {"image/png", "image/jpeg"}:
            try:
                with Image.open(io.BytesIO(datos)) as imagen:
                    if imagen.format != {"image/png": "PNG", "image/jpeg": "JPEG"}[self.tipo_mime]:
                        raise ValueError("El formato de la foto no coincide")
                    if imagen.width * imagen.height > 25_000_000:
                        raise ValueError("La foto excede 25 megapíxeles")
                    imagen.verify()
            except Exception as exc:
                raise ValueError("La foto no es una imagen válida PNG o JPEG") from exc
        else:
            raise ValueError("Solo se permiten fotos PNG/JPEG y fichas técnicas PDF")
        return self


class RqAdjuntoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    tipo_mime: str
    contenido_base64: str


class RqCampoItemCreate(BaseModel):
    tipo: TipoItemRqCampo
    articulo_id: int | None = Field(default=None, gt=0)
    nombre_producto: str | None = Field(default=None, max_length=200)
    unidad_medida: str | None = Field(default=None, max_length=50)
    cantidad: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    descripcion: str | None = None
    medidas: str | None = Field(default=None, max_length=150)
    observacion: str | None = None
    foto_base64: str | None = None
    fecha_requerida: datetime | None = None
    adjuntos: list[RqAdjuntoCreate] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validar_tipo(self):
        if self.tipo == TipoItemRqCampo.CATALOGADO and not self.articulo_id:
            raise ValueError("Un ítem catalogado requiere articulo_id")
        if self.tipo == TipoItemRqCampo.NO_CATALOGADO:
            if not (self.nombre_producto and self.nombre_producto.strip()):
                raise ValueError("Un ítem no catalogado requiere nombre_producto")
            if not (self.unidad_medida and self.unidad_medida.strip()):
                raise ValueError("Un ítem no catalogado requiere unidad_medida")
        if self.foto_base64:
            contenido = self.foto_base64.split(",", 1)[-1]
            tipo = "image/jpeg" if self.foto_base64.startswith("data:image/jpeg") else "image/png"
            RqAdjuntoCreate(nombre="foto", tipo_mime=tipo, contenido_base64=contenido)
        return self


class RqCampoCreate(BaseModel):
    obra_id: int | None = Field(default=None, gt=0)
    obra_codigo: str | None = Field(default=None, max_length=20)
    obra_descripcion: str | None = Field(default=None, max_length=200)
    nombre_proyecto: str | None = Field(default=None, max_length=200)
    numero_contrato_servicio: str | None = Field(default=None, max_length=100)
    numero_cotizacion: str | None = Field(default=None, max_length=100)
    fecha_requerimiento: datetime | None = None
    descripcion_general: str | None = None
    items: list[RqCampoItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validar_peso_total(self):
        if self.obra_codigo is not None:
            self.obra_codigo = self.obra_codigo.strip().upper()
        if self.obra_descripcion is not None:
            self.obra_descripcion = self.obra_descripcion.strip()
        if self.nombre_proyecto is not None:
            self.nombre_proyecto = self.nombre_proyecto.strip()
        if not self.obra_id and not self.obra_codigo:
            raise ValueError("Indique obra_id o obra_codigo")
        if self.obra_codigo:
            if not re.fullmatch(r"\d{3}-\d{4}", self.obra_codigo):
                raise ValueError("El código de obra debe tener formato NNN-YYYY")
        total = sum(len(a.contenido_base64) for item in self.items for a in item.adjuntos)
        total += sum(len(item.foto_base64 or "") for item in self.items)
        if total > 28_000_000:
            raise ValueError("Los adjuntos del requerimiento superan el límite total de 20 MB")
        return self


class RqCampoUpdate(RqCampoCreate):
    pass


class FirmaEnvioRequest(BaseModel):
    firma_base64: str = Field(min_length=20)
    destinatarios: list[EmailStr] | None = Field(default=None, min_length=1, max_length=3)


class ReenvioRqRequest(BaseModel):
    destinatarios: list[EmailStr] | None = Field(default=None, min_length=1, max_length=3)


class RqItemGestionRequest(BaseModel):
    estado: EstadoItemRq
    nota: str | None = Field(default=None, max_length=2000)
    detalle: str | None = Field(default=None, max_length=10000)
    adjuntos: list[RqAdjuntoCreate] | None = Field(default=None, max_length=5)

    @model_validator(mode="after")
    def validar_peso(self):
        if sum(len(a.contenido_base64) for a in self.adjuntos or []) > 28_000_000:
            raise ValueError("Los adjuntos de seguimiento superan 20 MB")
        return self


class RqCampoItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_item: int
    tipo: TipoItemRqCampo
    articulo_id: int | None
    codigo_producto: str | None
    nombre_producto: str
    unidad_medida: str
    cantidad: Decimal
    descripcion: str | None
    medidas: str | None
    observacion: str | None
    foto_base64: str | None
    fecha_requerida: datetime | None
    estado_gestion: str
    nota_gestion: str | None
    detalle_gestion: str | None
    adjuntos_gestion: list[RqAdjuntoResponse]
    adjuntos: list[RqAdjuntoResponse] = Field(default_factory=list)


class RqCampoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    obra_id: int
    obra_codigo: str | None
    obra_descripcion: str
    creador_id: int
    nombre_proyecto: str
    numero_contrato_servicio: str | None
    numero_cotizacion: str | None
    solicitante_nombre: str
    solicitante_cargo: str | None
    fecha_requerimiento: datetime
    descripcion_general: str | None
    estado: EstadoRqCampo
    estado_gestion: str
    fecha_firma: datetime | None
    destinatarios: list[str]
    fecha_envio: datetime | None
    error_envio: str | None
    creado_en: datetime
    actualizado_en: datetime
    items: list[RqCampoItemResponse]
