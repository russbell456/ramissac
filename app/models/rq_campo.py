from __future__ import annotations

import enum
import json
import re
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import Base


class EstadoRqCampo(str, enum.Enum):
    BORRADOR = "BORRADOR"
    FIRMADO = "FIRMADO"
    ENVIADO = "ENVIADO"


class TipoItemRqCampo(str, enum.Enum):
    CATALOGADO = "CATALOGADO"
    NO_CATALOGADO = "NO_CATALOGADO"


class RqCampoCorrelativo(Base):
    __tablename__ = "rq_campo_correlativos"

    anio = Column(Integer, primary_key=True)
    ultimo_numero = Column(Integer, nullable=False, default=0)


class RqCampoObraRegistro(Base):
    __tablename__ = "rq_campo_obras"

    codigo = Column(String(8), primary_key=True)
    obra_id = Column(Integer, ForeignKey("almacen_obras.id"), nullable=False, unique=True)
    ultimo_numero = Column(Integer, nullable=False, default=0)
    obra = relationship("AlmacenObra", back_populates="registro_rq")


class EstadoItemRq(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    POR_COMPRAR = "POR_COMPRAR"
    EN_PROCESO = "EN_PROCESO"
    COMPRADO = "COMPRADO"
    ATENDIDO_STOCK = "ATENDIDO_STOCK"
    CERRADO_SIN_COMPRA = "CERRADO_SIN_COMPRA"


ESTADOS_ITEM_FINALES = {"COMPRADO", "ATENDIDO_STOCK", "CERRADO_SIN_COMPRA"}


class RqCampo(Base):
    __tablename__ = "rq_campo"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(30), nullable=False, unique=True, index=True)
    obra_id = Column(Integer, ForeignKey("almacen_obras.id"), nullable=False, index=True)
    creador_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    nombre_proyecto = Column(String(200), nullable=False)
    numero_contrato_servicio = Column(String(100), nullable=True)
    numero_cotizacion = Column(String(100), nullable=True)
    solicitante_nombre = Column(String(200), nullable=False)
    solicitante_cargo = Column(String(100), nullable=True)
    fecha_requerimiento = Column(DateTime, nullable=False, default=datetime.utcnow)
    descripcion_general = Column(Text, nullable=True)
    estado = Column(Enum(EstadoRqCampo), nullable=False, default=EstadoRqCampo.BORRADOR)
    firma_base64 = Column(Text, nullable=True)
    firmado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_firma = Column(DateTime, nullable=True)
    destinatarios_email = Column(Text, nullable=True)
    fecha_envio = Column(DateTime, nullable=True)
    error_envio = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    obra = relationship("AlmacenObra")
    creador = relationship("User", foreign_keys=[creador_id])
    firmado_por = relationship("User", foreign_keys=[firmado_por_id])
    items = relationship("RqCampoItem", back_populates="rq", cascade="all, delete-orphan", order_by="RqCampoItem.numero_item")

    @property
    def obra_codigo(self) -> str | None:
        if self.obra and self.obra.registro_rq:
            return self.obra.registro_rq.codigo
        match = re.match(r"^(\d{3}-\d{4})(?:$|\s+-\s+)", self.nombre_proyecto)
        return match.group(1) if match else None

    @property
    def obra_descripcion(self) -> str:
        return re.sub(r"^\d{3}-\d{4}\s*-?\s*", "", self.nombre_proyecto)

    @property
    def estado_gestion(self) -> str:
        if self.estado != EstadoRqCampo.ENVIADO:
            return self.estado.value
        if self.items and all(i.estado_gestion in ESTADOS_ITEM_FINALES for i in self.items):
            return "FINALIZADO"
        if any(i.estado_gestion != "PENDIENTE" for i in self.items):
            return "EN_PROCESO"
        return "ENVIADO"

    @property
    def destinatarios(self) -> list[str]:
        if not self.destinatarios_email:
            return []
        try:
            valor = json.loads(self.destinatarios_email)
            return valor if isinstance(valor, list) else []
        except (TypeError, json.JSONDecodeError):
            return []


class RqCampoItem(Base):
    __tablename__ = "rq_campo_items"
    __table_args__ = (UniqueConstraint("rq_id", "numero_item", name="uq_rq_campo_item_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    rq_id = Column(Integer, ForeignKey("rq_campo.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_item = Column(Integer, nullable=False)
    tipo = Column(Enum(TipoItemRqCampo), nullable=False)
    articulo_id = Column(Integer, ForeignKey("almacen_articulos.id"), nullable=True)
    codigo_producto = Column(String(100), nullable=True)
    nombre_producto = Column(String(200), nullable=False)
    unidad_medida = Column(String(50), nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False)
    descripcion = Column(Text, nullable=True)
    medidas = Column(String(150), nullable=True)
    observacion = Column(Text, nullable=True)
    foto_base64 = Column(Text, nullable=True)
    fecha_requerida = Column(DateTime, nullable=True)

    rq = relationship("RqCampo", back_populates="items")
    articulo = relationship("AlmacenArticulo")
    adjuntos = relationship("RqCampoAdjunto", cascade="all, delete-orphan", order_by="RqCampoAdjunto.id")
    seguimiento = relationship("RqCampoItemSeguimiento", uselist=False, cascade="all, delete-orphan")

    @property
    def estado_gestion(self) -> str:
        return self.seguimiento.estado if self.seguimiento else "PENDIENTE"

    @property
    def nota_gestion(self) -> str | None:
        return self.seguimiento.nota if self.seguimiento else None

    @property
    def detalle_gestion(self) -> str | None:
        return self.seguimiento.detalle if self.seguimiento else None

    @property
    def adjuntos_gestion(self) -> list:
        return self.seguimiento.adjuntos if self.seguimiento else []


class RqCampoItemSeguimiento(Base):
    __tablename__ = "rq_campo_item_seguimiento"

    item_id = Column(Integer, ForeignKey("rq_campo_items.id", ondelete="CASCADE"), primary_key=True)
    estado = Column(String(30), nullable=False, default="PENDIENTE")
    nota = Column(Text, nullable=True)
    detalle = Column(Text, nullable=True)
    actualizado_por_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actualizado_en = Column(DateTime, nullable=False)
    adjuntos = relationship("RqCampoGestionAdjunto", cascade="all, delete-orphan")


class RqCampoGestionAdjunto(Base):
    __tablename__ = "rq_campo_gestion_adjuntos"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("rq_campo_item_seguimiento.item_id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo_mime = Column(String(50), nullable=False)
    contenido_base64 = Column(Text, nullable=False)


class RqCampoAdjunto(Base):
    __tablename__ = "rq_campo_adjuntos"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("rq_campo_items.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    tipo_mime = Column(String(50), nullable=False)
    contenido_base64 = Column(Text, nullable=False)
