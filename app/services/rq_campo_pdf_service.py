from __future__ import annotations

import base64
import io
import re
from xml.sax.saxutils import escape

from PIL import Image as PillowImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.rq_campo import RqCampo


VERDE_CABECERA = colors.HexColor("#D9EAD3")
GRIS_CLARO = colors.HexColor("#F2F2F2")


def decodificar_imagen_base64(valor: str) -> bytes:
    contenido = valor.split(",", 1)[1] if valor.startswith("data:") and "," in valor else valor
    try:
        datos = base64.b64decode(contenido, validate=True)
    except Exception as exc:
        raise ValueError("La firma no contiene una imagen base64 válida") from exc
    if not datos.startswith((b"\x89PNG", b"\xff\xd8\xff")):
        raise ValueError("La firma debe ser una imagen PNG o JPEG")
    return datos


def _texto(valor: object | None, estilo: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(valor)).replace('\n', '<br/>') if valor not in (None, "") else "", estilo)


def _categoria(nombre: str, articulo=None, descripcion: str | None = None) -> str:
    if descripcion:
        match = re.search(r"^Tipo:\s*(material|equipo|herramienta)\b", descripcion, re.IGNORECASE | re.MULTILINE)
        if match:
            return {
                "material": "MATERIALES",
                "equipo": "EQUIPOS",
                "herramienta": "HERRAMIENTAS",
            }[match.group(1).lower()]
    if articulo is not None:
        tipo = getattr(articulo.tipo, "value", articulo.tipo).upper()
        return {"EQUIPO": "EQUIPOS", "HERRAMIENTA": "HERRAMIENTAS"}.get(tipo, "MATERIALES")
    texto = nombre.upper()
    herramientas = ("AMOLADORA", "TALADRO", "LLAVE", "MARTILLO", "ALICATE", "DESTORNILLADOR")
    equipos = ("COMPRESOR", "EQUIPO", "CASCO", "ARNÉS", "ARNES", "EXTINTOR", "GENERADOR")
    if any(palabra in texto for palabra in herramientas):
        return "HERRAMIENTAS"
    if any(palabra in texto for palabra in equipos):
        return "EQUIPOS"
    return "MATERIALES"


def _fecha_hora(valor) -> str:
    return valor.strftime("%d/%m/%Y %H:%M")


def generar_pdf(rq: RqCampo) -> bytes:
    salida = io.BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=landscape(A4), leftMargin=.55*cm, rightMargin=.55*cm,
                            topMargin=.55*cm, bottomMargin=.55*cm)
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("rq_titulo", parent=estilos["Title"], fontSize=12.5, leading=15, alignment=TA_CENTER)
    control_label = ParagraphStyle("rq_control_label", parent=estilos["BodyText"], fontSize=7.5, leading=9)
    control_valor = ParagraphStyle("rq_control_valor", parent=estilos["BodyText"], fontSize=7.5, leading=9)
    celda = ParagraphStyle("rq_celda", parent=estilos["BodyText"], fontSize=5.8, leading=6.8)
    centrada = ParagraphStyle("rq_centrada", parent=celda, alignment=TA_CENTER)
    mini = ParagraphStyle("rq_mini", parent=celda, fontSize=5.0, leading=5.9)

    control = Table([
        [_texto("CÓDIGO:", control_label), _texto("RAMIS-REQ-FOR-001", control_valor)],
        [_texto("VERSIÓN:", control_label), _texto("02", control_valor)],
        [_texto("FECHA:", control_label), _texto(rq.fecha_requerimiento.strftime("%d/%m/%Y"), control_valor)],
        [_texto("NÚMERO REQUERIMIENTO:", control_label), _texto(rq.numero, control_valor)],
    ], colWidths=[4.25*cm, 3.75*cm], rowHeights=[.62*cm, .62*cm, .62*cm, .62*cm])
    encabezado = Table([[Paragraph("<b>REQUERIMIENTOS DE MATERIALES, INSUMOS, EQUIPOS Y HERRAMIENTAS</b>", titulo), control]],
                       colWidths=[19.5*cm, 8.0*cm])
    encabezado.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .55, colors.black),
                                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                                    ("LEFTPADDING", (0,0), (-1,-1), 6),
                                    ("RIGHTPADDING", (0,0), (-1,-1), 6),
                                    ("TOPPADDING", (0,0), (-1,-1), 4),
                                    ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))

    generales = Table([
        ["NOMBRE DEL SERVICIO:", _texto(rq.nombre_proyecto, celda), "FECHA DE REQUERIMIENTO:", _fecha_hora(rq.fecha_requerimiento)],
        ["N.º COT. DEL SERVICIO:", _texto(rq.numero_cotizacion, celda), "SOLICITANTE:", _texto(rq.solicitante_nombre, celda)],
        ["CONTRATO / SERVICIO:", _texto(rq.numero_contrato_servicio, celda), "ESTADO DEL REQUERIMIENTO:", rq.estado.value],
    ], colWidths=[3.6*cm, 12.4*cm, 4.35*cm, 7.15*cm])
    generales.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), .4, colors.black), ("BACKGROUND", (0,0), (0,-1), GRIS_CLARO),
        ("BACKGROUND", (2,0), (2,-1), GRIS_CLARO), ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 5.7),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    titulos = ["N.º", "Descripción de materiales, herramientas y equipos", "U.M.", "Cant.",
               "Stock JUL", "Stock ANT", "Stock MIN", "Cant. entrega", "Observación o justificación",
               "Foto referencial", "Fecha entrega estimada", "Fecha entrega", "Juliaca", "Antauta", "Mina", "Estado RQ"]
    filas = [[_texto(valor, mini) for valor in titulos]]
    grupos = {categoria: [] for categoria in ("MATERIALES", "EQUIPOS", "HERRAMIENTAS")}
    for item in rq.items:
        grupos[_categoria(item.nombre_producto, item.articulo, item.descripcion)].append(item)
    for categoria, items in grupos.items():
        filas.append([Paragraph(f"<b>{categoria}</b>", celda)] + [""]*15)
        for item in items:
            descripcion = f"{item.codigo_producto} - " if item.codigo_producto else ""
            descripcion += escape(item.nombre_producto)
            if item.medidas:
                descripcion += f" / {escape(item.medidas)}"
            if item.descripcion:
                descripcion += '<br/>' + escape(item.descripcion).replace('\n', '<br/>')
            filas.append([
                str(item.numero_item), Paragraph(descripcion, celda), _texto(item.unidad_medida, centrada), f"{item.cantidad:.2f}",
                "", "", "", "", _texto(item.observacion, celda),
                "VER ANEXO" if item.foto_base64 or item.adjuntos else "",
                item.fecha_requerida.strftime("%d/%m/%Y") if item.fecha_requerida else "", "", "", "", "", rq.estado.value,
            ])

    anchos = [.65, 8.15, .95, .95, 1.05, 1.05, 1.05, 1.15, 2.9, 1.55, 1.75, 1.45, 1.05, 1.05, 1.05, 1.7]
    items_tabla = Table(filas, repeatRows=1, colWidths=[x*cm for x in anchos])
    reglas = [
        ("GRID", (0,0), (-1,-1), .35, colors.black), ("BACKGROUND", (0,0), (-1,0), VERDE_CABECERA),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("FONTSIZE", (0,0), (-1,-1), 5.3),
        ("LEFTPADDING", (0,0), (-1,-1), 2), ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ("ALIGN", (1,1), (1,-1), "LEFT"), ("ALIGN", (8,1), (8,-1), "LEFT"),
    ]
    indice = 1
    for items in grupos.values():
        reglas.extend([("SPAN", (0,indice), (-1,indice)), ("BACKGROUND", (0,indice), (-1,indice), GRIS_CLARO),
                       ("ALIGN", (0,indice), (-1,indice), "LEFT")])
        indice += len(items) + 1
    items_tabla.setStyle(TableStyle(reglas))

    elementos = [encabezado, Spacer(1,4), generales, Spacer(1,5), items_tabla, Spacer(1,8)]
    if rq.descripcion_general:
        elementos.extend([Paragraph(f"<b>DESCRIPCIÓN / JUSTIFICACIÓN GENERAL:</b> {escape(rq.descripcion_general)}", celda), Spacer(1,6)])
    firma = [Paragraph("<b>SOLICITANTE</b>", centrada)]
    if rq.firma_base64:
        firma.append(Image(io.BytesIO(decodificar_imagen_base64(rq.firma_base64)), width=4.2*cm, height=1.8*cm, kind="proportional"))
    firma.extend([Paragraph("<b>FIRMA</b>", centrada), Paragraph(f"NOMBRE: {escape(rq.solicitante_nombre)}", centrada),
                  Paragraph(f"CARGO: {escape(rq.solicitante_cargo or '')}", centrada)])
    elementos.append(KeepTogether(firma))
    if not rq.firma_base64:
        elementos.append(Paragraph("BORRADOR · PENDIENTE DE FIRMA Y ENVÍO", control_label))
    elementos.extend(_anexo_imagenes(rq, estilos))
    doc.build(elementos)
    return salida.getvalue()


def _anexo_imagenes(rq: RqCampo, estilos) -> list:
    fotos, documentos = [], []
    pie = ParagraphStyle("rq_foto_pie", parent=estilos["BodyText"], fontSize=8, leading=10)
    for item in rq.items:
        imagenes = [a for a in item.adjuntos if a.tipo_mime.startswith("image/")]
        for adjunto in item.adjuntos:
            if adjunto.tipo_mime == "application/pdf":
                documentos.append(f"Ítem {item.numero_item} · {item.nombre_producto}: {adjunto.nombre}")
        fuentes = [(a.nombre, base64.b64decode(a.contenido_base64)) for a in imagenes]
        if item.foto_base64 and not imagenes:
            fuentes.append(("Foto referencial", decodificar_imagen_base64(item.foto_base64)))
        for nombre, datos in fuentes:
            with PillowImage.open(io.BytesIO(datos)) as original:
                imagen = ImageOps.exif_transpose(original).convert("RGB")
                imagen.thumbnail((1200, 900))
                salida = io.BytesIO()
                imagen.save(salida, format="JPEG", quality=85)
            fotos.append([
                Image(io.BytesIO(salida.getvalue()), width=8.2*cm, height=5.4*cm, kind="proportional"),
                Spacer(1, 4), _texto(f"Ítem {item.numero_item} · {item.nombre_producto} · {nombre}", pie),
            ])
    elementos = []
    for inicio in range(0, len(fotos), 6):
        elementos.extend([PageBreak(), Paragraph(f"<b>ANEXO FOTOGRÁFICO · {escape(rq.numero)}</b>", estilos["Heading2"]),
                          _texto(rq.nombre_proyecto, pie), Spacer(1, 10)])
        lote = fotos[inicio:inicio+6]
        filas = [lote[pos:pos+3] + [""] * (3-len(lote[pos:pos+3])) for pos in range(0, len(lote), 3)]
        galeria = Table(filas, colWidths=[9.1*cm]*3)
        galeria.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("BOX", (0,0), (-1,-1), .3, colors.lightgrey),
            ("INNERGRID", (0,0), (-1,-1), .3, colors.lightgrey),
            ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        elementos.append(galeria)
    if documentos:
        elementos.extend([Spacer(1, 12), Paragraph("<b>FICHAS TÉCNICAS ADJUNTAS</b>", estilos["Heading3"])])
        elementos.extend(_texto(nombre, pie) for nombre in documentos)
        elementos.append(Paragraph("Los archivos originales se adjuntan al correo y están disponibles en la aplicación.", pie))
    return elementos
