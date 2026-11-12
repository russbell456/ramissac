from __future__ import annotations

import json
from pathlib import Path
import base64
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.almacen_articulos import AlmacenArticulo
from app.models.almacen_obras import AlmacenObra
from app.models.rq_campo import (EstadoRqCampo,
    RqCampo, RqCampoCorrelativo, RqCampoObraRegistro, RqCampoItem,
    RqCampoItemSeguimiento, RqCampoGestionAdjunto, RqCampoAdjunto, TipoItemRqCampo)
from app.models.user import User
from app.schemas.rq_campo import RqCampoCreate
from app.services.rq_campo_pdf_service import decodificar_imagen_base64, generar_pdf
from app.services.rq_email_service import RqEmailService


class EnvioRqError(RuntimeError):
    pass


PERU_TZ = ZoneInfo("America/Lima")


def _ahora_peru() -> datetime:
    return datetime.now(PERU_TZ).replace(tzinfo=None)


class RqCampoService:
    @staticmethod
    def _nombre_obra(codigo: str, descripcion: str | None) -> str:
        detalle = (descripcion or "").strip()
        return f"{codigo} - {detalle}" if detalle else codigo

    @staticmethod
    def _resolver_obra(db: Session, datos: RqCampoCreate) -> AlmacenObra:
        if datos.obra_id and not datos.obra_codigo:
            obra = db.query(AlmacenObra).filter(AlmacenObra.id == datos.obra_id).first()
            if not obra or str(obra.estado).lower() != "activo":
                raise ValueError("La obra no existe o no está activa")
            return obra

        codigo = (datos.obra_codigo or "").strip().upper()
        if not re.fullmatch(r"\d{3}-\d{4}", codigo):
            raise ValueError("El código de obra debe tener formato NNN-YYYY")
        # Serializa altas y correlativos de la misma obra en PostgreSQL.
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:codigo))"), {"codigo": codigo})
        registro = db.query(RqCampoObraRegistro).filter_by(codigo=codigo).with_for_update().first()
        descripcion = (datos.obra_descripcion or "").strip()
        obra = registro.obra if registro else db.query(AlmacenObra).filter(
            (AlmacenObra.nombre == codigo) | AlmacenObra.nombre.startswith(f"{codigo} - ")
        ).order_by(AlmacenObra.id.asc()).first()
        if datos.obra_id and (not obra or obra.id != datos.obra_id):
            raise ValueError("El código no corresponde a la obra seleccionada")
        if obra:
            if str(obra.estado).lower() != "activo":
                raise ValueError("La obra no existe o no está activa")
            if descripcion:
                obra.nombre = RqCampoService._nombre_obra(codigo, descripcion)
                obra.descripcion = descripcion
        else:
            if not descripcion:
                raise ValueError("Ingrese una descripción breve para la nueva obra")
            obra = AlmacenObra(nombre=RqCampoService._nombre_obra(codigo, descripcion),
                               descripcion=descripcion, estado="activo")
            db.add(obra)
            db.flush()
        if not registro:
            db.add(RqCampoObraRegistro(codigo=codigo, obra_id=obra.id, ultimo_numero=0))
        db.flush()
        return obra

    @staticmethod
    def _puede_ver(rq: RqCampo, usuario: User) -> bool:
        return rq.creador_id == usuario.id or usuario.role.lower() in {"admin", "logistica", "logística", "almacenero", "compras", "comprador"}

    @staticmethod
    def _obtener(db: Session, rq_id: int, usuario: User) -> RqCampo:
        rq = db.query(RqCampo).filter(RqCampo.id == rq_id).first()
        if not rq:
            raise LookupError("Requerimiento no encontrado")
        if not RqCampoService._puede_ver(rq, usuario):
            raise PermissionError("No tiene permiso para acceder a este requerimiento")
        return rq

    @staticmethod
    def _siguiente_numero(db: Session, anio: int, obra: AlmacenObra) -> str:
        registro = db.query(RqCampoObraRegistro).filter_by(obra_id=obra.id).with_for_update().first()
        if registro:
            registro.ultimo_numero += 1
            return f"RQ-{registro.ultimo_numero:03d}-{registro.codigo}"
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:anio)"), {"anio": anio})
        correlativo = db.query(RqCampoCorrelativo).filter_by(anio=anio).with_for_update().first()
        if not correlativo:
            correlativo = RqCampoCorrelativo(anio=anio, ultimo_numero=0)
            db.add(correlativo)
            db.flush()
        correlativo.ultimo_numero += 1
        return f"RQ-{correlativo.ultimo_numero:03d}-{anio}"

    @staticmethod
    def _crear_items(db: Session, rq: RqCampo, datos) -> None:
        for posicion, entrada in enumerate(datos, 1):
            articulo = None
            if entrada.tipo == TipoItemRqCampo.CATALOGADO:
                articulo = db.query(AlmacenArticulo).filter(AlmacenArticulo.id == entrada.articulo_id, AlmacenArticulo.activo.is_(True)).first()
                if not articulo:
                    raise ValueError(f"El artículo {entrada.articulo_id} no existe o está inactivo")
            adjuntos = [RqCampoAdjunto(**adjunto.model_dump()) for adjunto in entrada.adjuntos]
            if articulo and articulo.ficha and articulo.ficha.documento_base64 and len(adjuntos) < 5 and not any(a.tipo_mime == "application/pdf" for a in adjuntos):
                adjuntos.append(RqCampoAdjunto(nombre=articulo.ficha.nombre_documento, tipo_mime="application/pdf",
                                               contenido_base64=articulo.ficha.documento_base64))
            foto = entrada.foto_base64
            if articulo and not foto and not any(a.tipo_mime.startswith("image/") for a in adjuntos):
                directorio = Path("uploads/articulos").resolve()
                for imagen in articulo.imagenes[:max(0, 5-len(adjuntos))]:
                    ruta = Path(imagen.ruta.lstrip("/")).resolve()
                    if directorio in ruta.parents and ruta.is_file() and ruta.stat().st_size <= 5 * 1024 * 1024:
                        contenido = base64.b64encode(ruta.read_bytes()).decode()
                        # WebP se convierte a JPEG para el anexo PDF.
                        if imagen.tipo_mime == "image/webp":
                            import io
                            from PIL import Image
                            salida = io.BytesIO()
                            with Image.open(ruta) as original:
                                original.convert("RGB").save(salida, format="JPEG", quality=85)
                            contenido = base64.b64encode(salida.getvalue()).decode()
                        adjuntos.append(RqCampoAdjunto(nombre=imagen.nombre_archivo,
                            tipo_mime="image/jpeg" if imagen.tipo_mime == "image/webp" else imagen.tipo_mime,
                            contenido_base64=contenido))
            rq.items.append(RqCampoItem(
                numero_item=posicion,
                tipo=entrada.tipo,
                articulo_id=articulo.id if articulo else None,
                codigo_producto=articulo.codigo_excel if articulo else None,
                nombre_producto=articulo.nombre if articulo else entrada.nombre_producto.strip(),
                unidad_medida=articulo.unidad_medida if articulo else entrada.unidad_medida.strip(),
                cantidad=entrada.cantidad,
                descripcion=entrada.descripcion or ("\n".join(filter(None, [articulo.descripcion, articulo.especificaciones])) if articulo else None),
                medidas=entrada.medidas if entrada.descripcion is not None else (articulo.medidas if articulo else None),
                observacion=entrada.observacion if entrada.descripcion is not None else (articulo.observacion if articulo else None),
                foto_base64=foto,
                fecha_requerida=entrada.fecha_requerida,
                adjuntos=adjuntos,
            ))
        peso = sum(len(base64.b64decode(a.contenido_base64)) for item in rq.items for a in item.adjuntos)
        peso += sum(len(decodificar_imagen_base64(item.foto_base64)) for item in rq.items if item.foto_base64)
        if peso > 20 * 1024 * 1024:
            raise ValueError("Los adjuntos del requerimiento, incluidas las fichas del catálogo, superan 20 MB")

    @staticmethod
    def crear(db: Session, datos: RqCampoCreate, usuario: User) -> RqCampo:
        obra = RqCampoService._resolver_obra(db, datos)
        fecha = datos.fecha_requerimiento or _ahora_peru()
        nombre_proyecto = obra.nombre
        rq = RqCampo(
            numero=RqCampoService._siguiente_numero(db, fecha.year, obra), obra_id=obra.id,
            creador_id=usuario.id, nombre_proyecto=nombre_proyecto,
            numero_contrato_servicio=datos.numero_contrato_servicio,
            numero_cotizacion=datos.numero_cotizacion,
            solicitante_nombre=f"{usuario.nombre} {usuario.apellidos}".strip(),
            solicitante_cargo=usuario.cargo, fecha_requerimiento=fecha,
            descripcion_general=datos.descripcion_general,
        )
        db.add(rq)
        RqCampoService._crear_items(db, rq, datos.items)
        db.commit()
        db.refresh(rq)
        return rq

    @staticmethod
    def listar(db: Session, usuario: User) -> list[RqCampo]:
        consulta = db.query(RqCampo)
        if usuario.role.lower() not in {"admin", "logistica", "logística", "almacenero", "compras", "comprador"}:
            consulta = consulta.filter(RqCampo.creador_id == usuario.id)
        return consulta.order_by(RqCampo.creado_en.desc()).all()

    @staticmethod
    def actualizar(db: Session, rq_id: int, datos: RqCampoCreate, usuario: User) -> RqCampo:
        rq = RqCampoService._obtener(db, rq_id, usuario)
        if rq.creador_id != usuario.id and usuario.role != "admin":
            raise PermissionError("Solo el creador puede editar el requerimiento")
        if rq.estado != EstadoRqCampo.BORRADOR:
            raise ValueError("Solo se puede editar un requerimiento en borrador")
        obra = RqCampoService._resolver_obra(db, datos)
        if rq.obra_id != obra.id:
            rq.numero = RqCampoService._siguiente_numero(db, rq.fecha_requerimiento.year, obra)
        rq.obra_id = obra.id
        rq.nombre_proyecto = obra.nombre
        rq.numero_contrato_servicio = datos.numero_contrato_servicio
        rq.numero_cotizacion = datos.numero_cotizacion
        rq.fecha_requerimiento = datos.fecha_requerimiento or rq.fecha_requerimiento
        rq.descripcion_general = datos.descripcion_general
        rq.items.clear()
        db.flush()
        RqCampoService._crear_items(db, rq, datos.items)
        db.commit()
        db.refresh(rq)
        return rq

    @staticmethod
    def eliminar(db: Session, rq_id: int, usuario: User) -> None:
        rq = RqCampoService._obtener(db, rq_id, usuario)
        if rq.creador_id != usuario.id and usuario.role != "admin":
            raise PermissionError("Solo el creador puede eliminar el requerimiento")
        if rq.estado != EstadoRqCampo.BORRADOR:
            raise ValueError("Solo se puede eliminar un requerimiento en borrador")
        db.delete(rq)
        db.commit()

    @staticmethod
    def firmar_y_enviar(db: Session, rq_id: int, firma: str, destinatarios: list[str] | None, usuario: User) -> RqCampo:
        rq = RqCampoService._obtener(db, rq_id, usuario)
        if rq.creador_id != usuario.id and usuario.role != "admin":
            raise PermissionError("Solo el creador puede firmar este requerimiento")
        if rq.estado == EstadoRqCampo.ENVIADO:
            raise ValueError("El requerimiento ya fue enviado; utilice el endpoint de reenvío")
        if not rq.obra or str(rq.obra.estado).lower() != "activo":
            raise ValueError("La obra ya no está activa; seleccione una obra activa antes de enviar")
        decodificar_imagen_base64(firma)
        correos = destinatarios or RqEmailService.destinatarios_por_defecto()
        if not correos:
            raise ValueError("Indique entre uno y tres destinatarios o configure RQ_EMAIL_DESTINATARIOS")
        ahora = _ahora_peru()
        rq.firma_base64 = firma
        rq.firmado_por_id = usuario.id
        rq.fecha_firma = ahora
        rq.estado = EstadoRqCampo.FIRMADO
        rq.destinatarios_email = json.dumps(correos)
        rq.error_envio = None
        db.commit()
        try:
            RqEmailService.enviar(rq, correos, generar_pdf(rq))
        except Exception as exc:
            rq.error_envio = str(exc)[:1000]
            db.commit()
            raise EnvioRqError(f"El requerimiento quedó firmado, pero el correo no pudo enviarse: {exc}") from exc
        rq.estado = EstadoRqCampo.ENVIADO
        rq.fecha_envio = _ahora_peru()
        rq.error_envio = None
        db.commit()
        db.refresh(rq)
        return rq

    @staticmethod
    def reenviar(db: Session, rq_id: int, destinatarios: list[str] | None, usuario: User) -> RqCampo:
        rq = RqCampoService._obtener(db, rq_id, usuario)
        if rq.creador_id != usuario.id and usuario.role.lower() != "admin":
            raise PermissionError("Solo el creador puede reenviar el requerimiento")
        if not rq.firma_base64:
            raise ValueError("El requerimiento todavía no está firmado")
        correos = destinatarios or (json.loads(rq.destinatarios_email) if rq.destinatarios_email else RqEmailService.destinatarios_por_defecto())
        if not correos:
            raise ValueError("No hay destinatarios configurados")
        try:
            RqEmailService.enviar(rq, correos, generar_pdf(rq))
        except Exception as exc:
            rq.error_envio = str(exc)[:1000]
            db.commit()
            raise EnvioRqError(f"No se pudo reenviar el correo: {exc}") from exc
        rq.estado = EstadoRqCampo.ENVIADO
        rq.destinatarios_email = json.dumps(correos)
        rq.fecha_envio = _ahora_peru()
        rq.error_envio = None
        db.commit()
        db.refresh(rq)
        return rq

    @staticmethod
    def gestionar_item(db: Session, rq_id: int, item_id: int, datos, usuario: User) -> RqCampo:
        rq = RqCampoService._obtener(db, rq_id, usuario)
        if rq.estado != EstadoRqCampo.ENVIADO:
            raise ValueError("El requerimiento debe estar enviado para gestionar sus ítems")
        rol = usuario.role.lower()
        logistica = rol in {"admin", "logistica", "logística", "almacenero"}
        compras = rol in {"admin", "compras", "comprador"}
        estado = datos.estado.value
        if not logistica and not compras:
            raise PermissionError("Solo logística o compras puede gestionar ítems")
        item = next((i for i in rq.items if i.id == item_id), None)
        if not item:
            raise LookupError("Ítem no encontrado en este requerimiento")
        if rol != "admin":
            if estado in {"PENDIENTE", "POR_COMPRAR", "ATENDIDO_STOCK"} and not logistica:
                raise PermissionError("Esta acción corresponde a logística")
            if estado in {"EN_PROCESO", "COMPRADO"} and not compras:
                raise PermissionError("Esta acción corresponde a compras")
            if compras and not logistica and item.estado_gestion not in {"POR_COMPRAR", "EN_PROCESO"} and estado != item.estado_gestion:
                raise ValueError("Logística debe derivar el ítem a compras primero")
        if estado == "CERRADO_SIN_COMPRA" and not (datos.nota or "").strip():
            raise ValueError("Indique el motivo del cierre sin compra")
        if not item.seguimiento:
            item.seguimiento = RqCampoItemSeguimiento()
        item.seguimiento.estado = estado
        item.seguimiento.nota = (datos.nota or "").strip() or None
        if datos.detalle is not None:
            item.seguimiento.detalle = datos.detalle.strip() or None
        if datos.adjuntos is not None:
            item.seguimiento.adjuntos = [RqCampoGestionAdjunto(**a.model_dump()) for a in datos.adjuntos]
        item.seguimiento.actualizado_por_id = usuario.id
        item.seguimiento.actualizado_en = _ahora_peru()
        rq.actualizado_en = _ahora_peru()
        db.commit()
        db.refresh(rq)
        return rq
