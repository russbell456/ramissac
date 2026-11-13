from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PillowImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.rq_campo import RqCampo


AZUL_PRIMARIO = colors.HexColor("#17365D")
AZUL_SUAVE = colors.HexColor("#EAF0F7")
FONDO_CLARO = colors.HexColor("#F8FAFC")
BORDE = colors.HexColor("#CBD5E1")
BORDE_INTERNO = colors.HexColor("#E2E8F0")
TEXTO_SECUNDARIO = colors.HexColor("#4B5563")


def decodificar_imagen_base64(valor: str) -> bytes:
    contenido = valor.split(",", 1)[1] if valor.startswith(
        "data:") and "," in valor else valor
    try:
        datos = base64.b64decode(contenido, validate=True)
    except Exception as exc:
        raise ValueError(
            "La firma no contiene una imagen base64 válida") from exc
    if not datos.startswith((b"\x89PNG", b"\xff\xd8\xff")):
        raise ValueError("La firma debe ser una imagen PNG o JPEG")
    return datos


def _texto(valor: object | None, estilo: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(valor)).replace('\n', '<br/>')
                     if valor not in (None, "") else "", estilo)


def _categoria(
        nombre: str,
        articulo=None,
        descripcion: str | None = None) -> str:
    if descripcion:
        match = re.search(
            r"^Tipo:\s*(material|equipo|herramienta)\b",
            descripcion,
            re.IGNORECASE | re.MULTILINE)
        if match:
            return {
                "material": "MATERIALES",
                "equipo": "EQUIPOS",
                "herramienta": "HERRAMIENTAS",
            }[match.group(1).lower()]
    if articulo is not None:
        tipo = getattr(articulo.tipo, "value", articulo.tipo).upper()
        return {
            "EQUIPO": "EQUIPOS",
            "HERRAMIENTA": "HERRAMIENTAS"}.get(
            tipo,
            "MATERIALES")
    texto = nombre.upper()
    herramientas = (
        "AMOLADORA",
        "TALADRO",
        "LLAVE",
        "MARTILLO",
        "ALICATE",
        "DESTORNILLADOR")
    equipos = (
        "COMPRESOR",
        "EQUIPO",
        "CASCO",
        "ARNÉS",
        "ARNES",
        "EXTINTOR",
        "GENERADOR")
    if any(palabra in texto for palabra in herramientas):
        return "HERRAMIENTAS"
    if any(palabra in texto for palabra in equipos):
        return "EQUIPOS"
    return "MATERIALES"


def _fecha_hora(valor) -> str:
    return valor.strftime("%d/%m/%Y %H:%M")


def generar_pdf(rq: RqCampo) -> bytes:
    salida = io.BytesIO()
    doc = SimpleDocTemplate(
        salida,
        pagesize=landscape(A4),
        leftMargin=.55 * cm,
        rightMargin=.55 * cm,
        topMargin=.55 * cm,
        bottomMargin=.55 * cm)
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "rq_titulo", parent=estilos["Title"], fontSize=12.5, leading=15,
        alignment=TA_CENTER, textColor=colors.white,
    )
    control_label = ParagraphStyle(
        "rq_control_label",
        parent=estilos["BodyText"],
        fontSize=7.5,
        leading=9,
        textColor=TEXTO_SECUNDARIO,
    )
    control_valor = ParagraphStyle(
        "rq_control_valor",
        parent=estilos["BodyText"],
        fontSize=7.5,
        leading=9,
        textColor=AZUL_PRIMARIO,
    )
    celda = ParagraphStyle(
        "rq_celda", parent=estilos["BodyText"], fontSize=5.8, leading=6.8,
        textColor=AZUL_PRIMARIO,
    )
    centrada = ParagraphStyle("rq_centrada", parent=celda, alignment=TA_CENTER)
    mini = ParagraphStyle("rq_mini", parent=celda, fontSize=5.0, leading=5.9)
    seccion = ParagraphStyle(
        "rq_seccion", parent=estilos["Heading3"], fontSize=8, leading=10,
        textColor=AZUL_PRIMARIO, spaceBefore=4, spaceAfter=4,
    )

    control = Table([
        [
            _texto("CÓDIGO:", control_label),
            _texto("RAMIS-REQ-FOR-001", control_valor),
        ],
        [_texto("VERSIÓN:", control_label), _texto("02", control_valor)],
        [
            _texto("FECHA:", control_label),
            _texto(rq.fecha_requerimiento.strftime("%d/%m/%Y"), control_valor),
        ],
        [
            _texto("NÚMERO REQUERIMIENTO:", control_label),
            _texto(rq.numero, control_valor),
        ],
    ], colWidths=[4.25 * cm, 3.75 * cm], rowHeights=[
        .62 * cm, .62 * cm, .62 * cm, .62 * cm])
    control.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FONDO_CLARO),
        ("BOX", (0, 0), (-1, -1), .5, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), .25, BORDE_INTERNO),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    ruta_logo = Path(__file__).resolve().parents[2] / "static" / "logo.jpg"
    logo = (
        Image(
            str(ruta_logo),
            width=1.7 *
            cm,
            height=1.7 *
            cm,
            kind="proportional") if ruta_logo.is_file() else "")
    titulo_documento = (
        "<b>REQUERIMIENTOS DE MATERIALES, INSUMOS, "
        "EQUIPOS Y HERRAMIENTAS</b>"
    )
    encabezado = Table([[logo, Paragraph(titulo_documento, titulo), control]],
                       colWidths=[2.0 * cm, 17.3 * cm, 8.0 * cm])
    encabezado.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), AZUL_PRIMARIO),
        ("BOX", (0, 0), (-1, -1), .5, BORDE),
        ("LINEBEFORE", (2, 0), (2, 0), .5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    generales = Table([["NOMBRE DEL SERVICIO:",
                        _texto(rq.nombre_proyecto,
                               celda),
                        "FECHA DE REQUERIMIENTO:",
                        _fecha_hora(rq.fecha_requerimiento)],
                       ["N.º COT. DEL SERVICIO:",
                        _texto(rq.numero_cotizacion,
                               celda),
                        "SOLICITANTE:",
                        _texto(rq.solicitante_nombre,
                               celda)],
                       ["CONTRATO / SERVICIO:",
                        _texto(rq.numero_contrato_servicio,
                               celda),
                        "ESTADO DEL REQUERIMIENTO:",
                        rq.estado.value],
                       ],
                      colWidths=[3.6 * cm,
                                 12.4 * cm,
                                 4.35 * cm,
                                 7.15 * cm])
    generales.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FONDO_CLARO),
        ("BOX", (0, 0), (-1, -1), .5, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), .25, BORDE_INTERNO),
        ("BACKGROUND", (0, 0), (0, -1), AZUL_SUAVE),
        ("BACKGROUND", (2, 0), (2, -1), AZUL_SUAVE),
        ("TEXTCOLOR", (0, 0), (0, -1), TEXTO_SECUNDARIO),
        ("TEXTCOLOR", (2, 0), (2, -1), TEXTO_SECUNDARIO),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 5.7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    titulos = [
        "N.º",
        "Descripción de materiales, herramientas y equipos",
        "U.M.",
        "Cant.",
        "Stock JUL",
        "Stock ANT",
        "Stock MIN",
        "Cant. entrega",
        "Observación o justificación",
        "Foto referencial",
        "Fecha entrega estimada",
        "Fecha entrega",
        "Juliaca",
        "Antauta",
        "Mina",
        "Estado RQ"]
    filas = [[_texto(valor, mini) for valor in titulos]]
    grupos = {categoria: []
              for categoria in ("MATERIALES", "EQUIPOS", "HERRAMIENTAS")}
    for item in rq.items:
        grupos[_categoria(item.nombre_producto, item.articulo,
                          item.descripcion)].append(item)
    for categoria, items in grupos.items():
        filas.append([Paragraph(f"<b>{categoria}</b>", celda)] + [""] * 15)
        for item in items:
            descripcion = f"{
                item.codigo_producto} - " if item.codigo_producto else ""
            descripcion += escape(item.nombre_producto)
            if item.medidas:
                descripcion += f" / {escape(item.medidas)}"
            if item.descripcion:
                descripcion += '<br/>' + \
                    escape(item.descripcion).replace('\n', '<br/>')
            filas.append([str(item.numero_item),
                          Paragraph(descripcion,
                                    celda),
                          _texto(item.unidad_medida,
                                 centrada),
                          f"{item.cantidad:.2f}",
                          "",
                          "",
                          "",
                          "",
                          _texto(item.observacion,
                                 celda),
                          "VER ANEXO"
                          if item.foto_base64 or item.adjuntos else "",
                          item.fecha_requerida.strftime("%d/%m/%Y")
                          if item.fecha_requerida else "",
                          "",
                          "",
                          "",
                          "",
                          rq.estado.value,
                          ])

    anchos = [.65, 8.15, .95, .95, 1.05, 1.05, 1.05, 1.15,
              2.9, 1.55, 1.75, 1.45, 1.05, 1.05, 1.05, 1.7]
    items_tabla = Table(
        filas, repeatRows=1, colWidths=[
            x * cm for x in anchos])
    reglas = [
        ("GRID", (0, 0), (-1, -1), .35, BORDE),
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_PRIMARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 5.3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (8, 1), (8, -1), "LEFT"),
    ]
    indice = 1
    for items in grupos.values():
        reglas.extend([
            ("SPAN", (0, indice), (-1, indice)),
            ("BACKGROUND", (0, indice), (-1, indice), AZUL_SUAVE),
            ("TEXTCOLOR", (0, indice), (-1, indice), AZUL_PRIMARIO),
            ("FONTNAME", (0, indice), (-1, indice), "Helvetica-Bold"),
            ("ALIGN", (0, indice), (-1, indice), "LEFT"),
        ])
        for fila_item in range(indice + 1, indice + len(items) + 1):
            if fila_item % 2 == 0:
                reglas.append(
                    (
                        "BACKGROUND",
                        (0, fila_item),
                        (-1, fila_item),
                        FONDO_CLARO,
                    )
                )
        indice += len(items) + 1
    items_tabla.setStyle(TableStyle(reglas))

    elementos = [
        encabezado, Spacer(
            1, 4), generales, Spacer(
            1, 5), items_tabla, Spacer(
                1, 8)]
    if rq.descripcion_general:
        descripcion_general = (
            f"<b>DESCRIPCIÓN / JUSTIFICACIÓN GENERAL:</b> "
            f"{escape(rq.descripcion_general)}"
        )
        elementos.extend([
            Paragraph(descripcion_general, seccion),
            Spacer(1, 6),
        ])
    firma = [Paragraph("<b>SOLICITANTE</b>", centrada)]
    if rq.firma_base64:
        firma.append(
            Image(
                io.BytesIO(
                    decodificar_imagen_base64(
                        rq.firma_base64)),
                width=4.2 * cm,
                height=1.8 * cm,
                kind="proportional"))
    firma.extend(
        [
            Paragraph(
                "<b>FIRMA</b>",
                centrada),
            Paragraph(
                f"NOMBRE: {
                    escape(
                        rq.solicitante_nombre)}",
                centrada),
            Paragraph(
                f"CARGO: {
                    escape(
                        rq.solicitante_cargo or '')}",
                centrada)])
    firma_bloque = Table(
        [[contenido] for contenido in firma],
        colWidths=[8.0 * cm],
    )
    firma_bloque.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), .5, BORDE),
        ("BACKGROUND", (0, 0), (-1, -1), FONDO_CLARO),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(KeepTogether([firma_bloque]))
    if not rq.firma_base64:
        elementos.append(
            Paragraph(
                "BORRADOR · PENDIENTE DE FIRMA Y ENVÍO",
                control_label))
    elementos.extend(_anexo_imagenes(rq, estilos))
    doc.build(elementos)
    return salida.getvalue()


def _anexo_imagenes(rq: RqCampo, estilos) -> list:
    fotos, documentos = [], []
    pie = ParagraphStyle(
        "rq_foto_pie", parent=estilos["BodyText"], fontSize=8, leading=10,
        textColor=TEXTO_SECUNDARIO,
    )
    for item in rq.items:
        imagenes = [
            a for a in item.adjuntos if a.tipo_mime.startswith("image/")]
        for adjunto in item.adjuntos:
            if adjunto.tipo_mime == "application/pdf":
                documentos.append(
                    f"Ítem {
                        item.numero_item} · {
                        item.nombre_producto}: {
                        adjunto.nombre}")
        fuentes = [(a.nombre, base64.b64decode(a.contenido_base64))
                   for a in imagenes]
        if item.foto_base64 and not imagenes:
            fuentes.append(
                ("Foto referencial",
                 decodificar_imagen_base64(
                     item.foto_base64)))
        for nombre, datos in fuentes:
            with PillowImage.open(io.BytesIO(datos)) as original:
                imagen = ImageOps.exif_transpose(original).convert("RGB")
                imagen.thumbnail((1200, 900))
                salida = io.BytesIO()
                imagen.save(salida, format="JPEG", quality=85)
            fotos.append(
                [
                    Image(
                        io.BytesIO(
                            salida.getvalue()),
                        width=8.2 * cm,
                        height=5.4 * cm,
                        kind="proportional"),
                    Spacer(
                        1,
                        4),
                    _texto(
                        f"Ítem {
                            item.numero_item} · {
                            item.nombre_producto} · {nombre}",
                        pie),
                ])
    elementos = []
    for inicio in range(0, len(fotos), 6):
        estilo_titulo_anexo = ParagraphStyle(
            "rq_anexo_titulo", parent=estilos["Heading2"],
            textColor=AZUL_PRIMARIO,
        )
        titulo_anexo = Paragraph(
            f"<b>ANEXO FOTOGRÁFICO · {escape(rq.numero)}</b>",
            estilo_titulo_anexo,
        )
        elementos.extend([
            PageBreak(),
            titulo_anexo,
            _texto(rq.nombre_proyecto, pie),
            Spacer(1, 10),
        ])
        lote = fotos[inicio:inicio + 6]
        filas = [
            lote[pos:pos + 3] + [""] * (3 - len(lote[pos:pos + 3]))
            for pos in range(0, len(lote), 3)
        ]
        galeria = Table(filas, colWidths=[9.1 * cm] * 3)
        galeria.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), .3, BORDE),
            ("INNERGRID", (0, 0), (-1, -1), .3, BORDE_INTERNO),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elementos.append(galeria)
    if documentos:
        estilo_titulo_fichas = ParagraphStyle(
            "rq_fichas_titulo", parent=estilos["Heading3"],
            textColor=AZUL_PRIMARIO,
        )
        elementos.extend([
            Spacer(1, 12),
            Paragraph("<b>FICHAS TÉCNICAS ADJUNTAS</b>", estilo_titulo_fichas),
        ])
        elementos.extend(_texto(nombre, pie) for nombre in documentos)
        elementos.append(
            Paragraph(
                "Los archivos originales se adjuntan al correo y están "
                "disponibles en la aplicación.",
                pie))
    return elementos
