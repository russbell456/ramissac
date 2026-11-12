from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import base64
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

from app.config.company_config import COMPANY

def guardar_firma_base64(firma_base64: str, file_id: str, folder: str = "static/firmas") -> str:
    """Return a stored signature path, upgrading legacy Base64 values on demand."""
    if firma_base64 and not firma_base64.startswith("data:"):
        existing_path = os.path.abspath(firma_base64)
        if os.path.isfile(existing_path):
            return existing_path

    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    
    # Remover prefijo si existe
    if "," in firma_base64:
        firma_base64 = firma_base64.split(",")[1]
        
    firma_bytes = base64.b64decode(firma_base64)
    firma_path = os.path.join(folder, f"firma_{file_id}.png")
    with open(firma_path, "wb") as f:
        f.write(firma_bytes)
    return firma_path

def generar_pdf_prestamo(prestamo) -> str:
    os.makedirs("static/prestamos", exist_ok=True)
    file_path = f"static/prestamos/prestamo_{prestamo.id}.pdf"
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    elements = []
    style_title = ParagraphStyle(
        "LoanTitle",
        parent=styles["Title"],
        alignment=1,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=5,
    )
    style_header = ParagraphStyle(
        "CompanyHeader",
        parent=styles["Normal"],
        alignment=1,
        fontSize=8,
        leading=10,
    )
    style_label = ParagraphStyle(
        "LoanLabel",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#4B5563"),
    )
    style_cell = ParagraphStyle(
        "LoanCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )
    style_section = ParagraphStyle(
        "LoanSection",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=8,
        spaceAfter=6,
    )
    style_footer = ParagraphStyle(
        "LoanFooter",
        parent=styles["Normal"],
        alignment=1,
        fontSize=8,
        textColor=colors.grey,
    )

    def p(value, style=style_cell):
        return Paragraph(escape(str(value if value not in (None, "") else "-")), style)

    def fecha_local(value):
        if not value:
            return "-"
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return value.astimezone(ZoneInfo("America/Lima")).strftime(
            "%d/%m/%Y %H:%M"
        )

    def tabla_persona(persona, titulo):
        nombre = " ".join(
            parte
            for parte in (
                getattr(persona, "nombre", None),
                getattr(persona, "apellidos", None),
            )
            if parte
        ) or "No registrado"
        filas = [[Paragraph(f"<b>{escape(titulo)}</b>", style_cell), ""]]
        for etiqueta, valor in (
            ("Nombre", nombre),
            ("DNI", getattr(persona, "dni", None)),
            ("Cargo", getattr(persona, "cargo", None)),
            ("Área", getattr(persona, "area", None)),
            ("Teléfono", getattr(persona, "telefono", None)),
            ("Correo", getattr(persona, "email", None)),
        ):
            filas.append([p(etiqueta, style_label), p(valor)])
        tabla = Table(filas, colWidths=[60, 190])
        tabla.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tabla
    
    logo_path = "static/logo.jpg"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=80, height=80)
    else:
        logo = Paragraph("", styles['Normal'])

    empresa_info = [
        Paragraph(f"<b>{escape(COMPANY['nombre'])}</b>", style_header),
        Paragraph(f"RUC: {escape(COMPANY['ruc'])}", style_header),
        Paragraph(escape(COMPANY['direccion']), style_header),
        Paragraph(
            f"Cel: {escape(COMPANY['telefono'])} | Email: {escape(COMPANY['email'])}",
            style_header,
        ),
        Paragraph(escape(COMPANY["web"]), style_header),
    ]
    header_table = Table([
        [
            logo,
            empresa_info,
            Paragraph(
                f"<b>Préstamo</b><br/>#{prestamo.id}",
                style_cell,
            ),
        ]
    ], colWidths=[75, 350, 100])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("ACTA DE ENTREGA Y PRÉSTAMO DE ARTÍCULOS", style_title))
    elements.append(Spacer(1, 8))
    trabajador = getattr(prestamo, "trabajador", None)
    almacenero = getattr(prestamo, "almacenero", None)
    personas = Table(
        [[tabla_persona(trabajador, "TRABAJADOR"), tabla_persona(almacenero, "ENTREGADO POR")]],
        colWidths=[267, 267],
    )
    personas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(personas)
    elements.append(Spacer(1, 10))

    tipo_prestamo = getattr(prestamo.tipo_prestamo, "value", prestamo.tipo_prestamo)
    estado = getattr(prestamo.estado, "value", prestamo.estado)
    resumen = [
        [p("Código", style_label), p(prestamo.codigo_unico), p("Tipo de préstamo", style_label), p(tipo_prestamo)],
        [p("Estado", style_label), p(estado), p("Registrado por", style_label), p(prestamo.registrado_por)],
        [p("Fecha de entrega", style_label), p(fecha_local(prestamo.fecha_prestamo)),
         p("Devolución prevista", style_label), p(fecha_local(prestamo.fecha_devolucion_prevista))],
        [p("PDF generado", style_label), p(fecha_local(datetime.now(ZoneInfo("UTC")))),
         p("ID de préstamo", style_label), p(prestamo.id)],
    ]
    resumen_table = Table(resumen, colWidths=[85, 180, 90, 179])
    resumen_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(resumen_table)

    asociacion = []
    if getattr(prestamo, "obra_id", None):
        obra = getattr(prestamo, "obra", None)
        asociacion.extend([
            ("Obra", getattr(obra, "nombre", str(prestamo.obra_id))),
            ("Cliente", getattr(obra, "cliente", None)),
            ("Ubicación", getattr(obra, "ubicacion", None)),
            ("Descripción", getattr(obra, "descripcion", None)),
        ])
    if getattr(prestamo, "empresa_nombre", None):
        asociacion.extend([
            ("Empresa", prestamo.empresa_nombre),
            ("RUC", getattr(prestamo, "empresa_ruc", "") or ""),
            ("Responsable externo", getattr(prestamo, "persona_nombres", "") or ""),
            ("DNI responsable", getattr(prestamo, "persona_dni", "") or ""),
            ("Teléfono responsable", getattr(prestamo, "persona_telefono", "") or ""),
        ])
    if asociacion:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("ASOCIACIÓN DEL PRÉSTAMO", style_section))
        asociacion_table = Table(
            [[p(etiqueta, style_label), p(valor)] for etiqueta, valor in asociacion],
            colWidths=[100, 434],
        )
        asociacion_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(asociacion_table)

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("ARTÍCULOS ENTREGADOS", style_section))
    table_data = [["N°", "Artículo", "Tipo", "Marca / modelo / serie", "Cantidad", "Control"]]
    fotos_articulos = []
    for indice, det in enumerate(prestamo.detalles, start=1):
        articulo = getattr(det, "articulo", None)
        nombre = getattr(articulo, "nombre", f"Artículo {det.articulo_id}")
        marca = getattr(articulo, "marca", None)
        modelo = getattr(articulo, "modelo", None)
        serie = getattr(articulo, "serie", None)
        tipo_articulo = getattr(getattr(articulo, "tipo", None), "value", "-")
        unidad = getattr(articulo, "unidad_medida", "")
        codigo_articulo = getattr(articulo, "codigo_excel", None)
        categoria = getattr(articulo, "categoria", None)
        estado_fisico = getattr(articulo, "estado_fisico", None)
        descripcion = " / ".join(
            str(v)
            for v in (
                marca,
                modelo,
                f"Serie: {serie}" if serie else None,
                f"Código: {codigo_articulo}" if codigo_articulo else None,
                f"Estado: {estado_fisico}" if estado_fisico else None,
                f"Categoría: {categoria}" if categoria else None,
            )
            if v
        )
        alto_valor = bool(articulo and getattr(articulo, "es_activo_alto_valor", False))
        table_data.append([
            str(indice),
            p(nombre),
            p(tipo_articulo),
            p(descripcion),
            p(f"{det.cantidad_prestada} {unidad}".strip()),
            p("Alto valor" if alto_valor else "Normal"),
        ])
        if alto_valor and det.foto_estado_inicio:
            foto_path = guardar_evidencia_base64(
                det.foto_estado_inicio,
                f"prestamo_{prestamo.id}_articulo_{articulo.id}",
                "static/prestamos/evidencias",
            )
            fotos_articulos.append((nombre, serie, foto_path))

    table = Table(table_data, colWidths=[24, 106, 58, 150, 70, 95], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    if prestamo.firma_base64:
        firma_path = guardar_firma_base64(prestamo.firma_base64, f"prestamo_{prestamo.id}", "static/prestamos")
        firma_table = Table(
            [[
                [Paragraph("<b>CONFORMIDAD DEL TRABAJADOR</b>", style_cell), Spacer(1, 5), Image(firma_path, width=170, height=68, kind="proportional"), Spacer(1, 4), p("Firma del trabajador", style_label)],
                [Paragraph("<b>ENTREGA REGISTRADA POR</b>", style_cell), Spacer(1, 5), p("Almacenero: " + (" ".join(filter(None, [getattr(almacenero, "nombre", None), getattr(almacenero, "apellidos", None)])) or "No registrado")), p("DNI: " + (getattr(almacenero, "dni", None) or "-"), style_label)],
            ]],
            colWidths=[267, 267],
        )
        firma_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(firma_table)

    if fotos_articulos:
        elements.append(PageBreak())
        elements.append(Paragraph("EVIDENCIAS FOTOGRÁFICAS - ARTÍCULOS DE ALTO VALOR", style_section))
        for nombre, serie, foto_path in fotos_articulos:
            leyenda = nombre + (f" - Serie: {serie}" if serie else "")
            elements.append(p(leyenda))
            elements.append(Spacer(1, 5))
            elements.append(Image(foto_path, width=430, height=560, kind="proportional"))
            elements.append(Spacer(1, 10))

    devoluciones = list(getattr(prestamo, "devoluciones", []) or [])
    if devoluciones:
        elements.append(PageBreak())
        elements.append(Paragraph("HISTORIAL DE DEVOLUCIONES", style_section))
        for devolucion in devoluciones:
            receptor = getattr(devolucion, "almacenero", None)
            receptor_nombre = " ".join(filter(None, [
                getattr(receptor, "nombre", None),
                getattr(receptor, "apellidos", None),
            ])) or "No registrado"
            elements.append(Paragraph(
                escape(
                    f"Devolución {devolucion.codigo_unico} | "
                    f"Fecha: {fecha_local(devolucion.fecha_devolucion)} | "
                    f"Recibido por: {receptor_nombre}"
                ), style_cell,
            ))
            filas_devolucion = [["Artículo", "Cantidad devuelta", "Evidencia"]]
            fotos_devolucion = []
            for retorno in getattr(devolucion, "detalles", []) or []:
                prestamo_detalle = getattr(retorno, "prestamo_detalle", None)
                articulo = getattr(prestamo_detalle, "articulo", None)
                nombre_articulo = getattr(articulo, "nombre", "Artículo")
                foto = retorno.foto_estado_devuelto
                filas_devolucion.append([
                    p(nombre_articulo), p(retorno.cantidad_devuelta),
                    p("Adjunta" if foto else "-"),
                ])
                if foto:
                    foto_path = guardar_evidencia_base64(
                        foto,
                        f"devolucion_{devolucion.id}_detalle_{retorno.id}",
                        "static/devoluciones/evidencias",
                    )
                    fotos_devolucion.append((nombre_articulo, foto_path))
            tabla_devolucion = Table(filas_devolucion, colWidths=[250, 120, 120])
            tabla_devolucion.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(Spacer(1, 5))
            elements.append(tabla_devolucion)
            elements.append(Spacer(1, 5))
            for nombre_articulo, foto_path in fotos_devolucion:
                elements.append(p(f"Estado al devolver: {nombre_articulo}"))
                elements.append(Image(foto_path, width=400, height=400, kind="proportional"))
            elements.append(Spacer(1, 12))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Documento generado por el sistema para trazabilidad del préstamo. "
        "La evidencia fotográfica se adjunta únicamente para artículos marcados como alto valor.",
        style_footer,
    ))
    doc.build(elements)

    return file_path


def guardar_evidencia_base64(
    evidencia_base64: str,
    file_id: str,
    folder: str,
) -> str:
    """Return a stored evidence path, upgrading legacy Base64 values on demand."""
    if evidencia_base64 and not evidencia_base64.startswith("data:"):
        existing_path = os.path.abspath(evidencia_base64)
        if os.path.isfile(existing_path):
            return existing_path

    os.makedirs(folder, exist_ok=True)
    encabezado = ""
    contenido = evidencia_base64
    if "," in evidencia_base64:
        encabezado, contenido = evidencia_base64.split(",", 1)
    extension = "jpg" if "image/jpeg" in encabezado.lower() else "png"
    ruta = os.path.join(folder, f"{file_id}.{extension}")
    with open(ruta, "wb") as archivo:
        archivo.write(base64.b64decode(contenido, validate=True))
    return ruta

def generar_pdf_ruta(ruta) -> str:
    os.makedirs("static/rutas", exist_ok=True)
    file_path = f"static/rutas/ruta_{ruta.id}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=20)

    styles = getSampleStyleSheet()
    elements = []
    style_title = ParagraphStyle('TitleCentered', parent=styles['Title'], alignment=1)
    style_header = ParagraphStyle('HeaderCentered', parent=styles['Normal'], alignment=1, spaceAfter=2)
    style_worker = ParagraphStyle('WorkerData', parent=styles['Normal'], spaceAfter=4)
    style_footer = ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    
    logo_path = "static/logo.jpg"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=80, height=80)
    else:
        logo = Paragraph("", styles['Normal'])

    empresa_info = [
        Paragraph(f"<b>{COMPANY['nombre']}</b>", style_title),
        Paragraph(f"RUC: {COMPANY['ruc']}", style_header),
        Paragraph(COMPANY['direccion'], style_header),
        Paragraph(f"Cel: {COMPANY['telefono']}", style_header),
        Paragraph(f"Email: {COMPANY['email']}", style_header),
        Paragraph(f"Web: {COMPANY['web']}", style_header),
    ]
    header_table = Table([
        [logo, empresa_info, Paragraph(f"<b>Código Ruta:</b> #{ruta.id}", styles['Normal'])]
    ], colWidths=[90, 330, 100])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>HOJA DE RUTA Y ASIGNACIÓN DE VEHÍCULO</b>", style_title))
    elements.append(Spacer(1, 15))
    
    trabajador_nombre = f"{ruta.trabajador.nombre} {ruta.trabajador.apellidos}" if getattr(ruta, "trabajador", None) else "N/A"
    placa_vehiculo = ruta.vehiculo.placa if getattr(ruta, "vehiculo", None) else "N/A"
    
    route_data = [
        f"<b>Trabajador / Conductor:</b> {trabajador_nombre}",
        f"<b>Vehículo (Placa):</b> {placa_vehiculo}",
        f"<b>Origen:</b> {ruta.origen}",
        f"<b>Destino:</b> {ruta.destino}",
        f"<b>Fecha de Salida:</b> {ruta.fecha_salida.strftime('%d/%m/%Y %H:%M') if isinstance(ruta.fecha_salida, datetime) else ruta.fecha_salida}",
        f"<b>Fecha de Llegada Estimada:</b> {ruta.fecha_llegada_estimada.strftime('%d/%m/%Y %H:%M') if isinstance(ruta.fecha_llegada_estimada, datetime) else ruta.fecha_llegada_estimada}",
        f"<b>Kilometraje de Salida:</b> {ruta.kilometraje_salida} km",
        f"<b>Combustible de Salida:</b> {ruta.combustible_salida}",
    ]
    for d in route_data:
        elements.append(Paragraph(d, style_worker))

    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("<b>Inspección Obligatoria de Seguridad:</b>", styles['Normal']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"• Frenos: {'Aprobado (OK)' if getattr(ruta, 'check_frenos', False) else 'No verificado'}", styles['Normal']))
    elements.append(Paragraph(f"• Luces: {'Aprobado (OK)' if getattr(ruta, 'check_luces', False) else 'No verificado'}", styles['Normal']))
    elements.append(Paragraph(f"• Llantas: {'Aprobado (OK)' if getattr(ruta, 'check_llantas', False) else 'No verificado'}", styles['Normal']))
    
    elements.append(Spacer(1, 20))
    if getattr(ruta, "firma_trabajador", None):
        firma_path = guardar_firma_base64(ruta.firma_trabajador, f"ruta_{ruta.id}", "static/firmas")
        elements.append(Paragraph("<b>Firma de conformidad del trabajador:</b>", styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Image(firma_path, width=200, height=80))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_footer))
    doc.build(elements)

    return file_path
