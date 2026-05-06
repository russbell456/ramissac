from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
import base64
import os
from datetime import datetime

from app.config.company_config import COMPANY


def generar_pdf_prestamo(prestamo):
    # Ruta del PDF
    file_path = f"static/prestamos/prestamo_{prestamo.id}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=20)

    styles = getSampleStyleSheet()
    elements = []

    # =========================
    # 🔷 ESTILOS PERSONALIZADOS
    # =========================
    style_title = ParagraphStyle('TitleCentered', parent=styles['Title'], alignment=1)
    style_header = ParagraphStyle('HeaderCentered', parent=styles['Normal'], alignment=1, spaceAfter=2)
    style_worker = ParagraphStyle('WorkerData', parent=styles['Normal'], spaceAfter=4)
    style_footer = ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)

    # =========================
    # 🔷 CABECERA (LOGO + EMPRESA + Código)
    # =========================
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

    # Tabla cabecera con logo y datos
    header_table = Table([
        [logo, empresa_info, Paragraph(f"<b>Código:</b> {prestamo.codigo_unico}", styles['Normal'])]
    ], colWidths=[90, 330, 100])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # =========================
    # 🔷 TÍTULO DEL DOCUMENTO
    # =========================
    elements.append(Paragraph("<b>DOCUMENTO DE PRÉSTAMO DE EQUIPOS</b>", style_title))
    elements.append(Spacer(1, 15))

    # =========================
    # 🔷 DATOS DEL TRABAJADOR
    # =========================
    worker_data = [
        f"<b>Trabajador:</b> {prestamo.nombres_completos}",
        f"<b>DNI:</b> {prestamo.dni}",
        f"<b>Cargo:</b> {prestamo.cargo}",
        f"<b>Fecha préstamo:</b> {prestamo.fecha_prestamo}",
        f"<b>Fecha devolución:</b> {prestamo.fecha_devolucion_prevista}",
    ]
    for d in worker_data:
        elements.append(Paragraph(d, style_worker))

    elements.append(Spacer(1, 15))

    # =========================
    # 🔷 TABLA DE ARTÍCULOS
    # =========================
    table_data = [["Artículo", "Cantidad"]]
    for det in prestamo.detalles:
        table_data.append([det.articulo_nombre, str(det.cantidad_prestada)])

    table = Table(table_data, colWidths=[400, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # =========================
    # 🔷 FIRMA DEL TRABAJADOR
    # =========================
    if prestamo.firma_base64:
        firma_bytes = base64.b64decode(prestamo.firma_base64)
        firma_path = f"static/prestamos/firma_{prestamo.id}.png"
        with open(firma_path, "wb") as f:
            f.write(firma_bytes)

        elements.append(Paragraph("<b>Firma del trabajador:</b>", styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Image(firma_path, width=200, height=80))

    elements.append(Spacer(1, 30))

    # =========================
    # 🔷 FOOTER
    # =========================
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_footer))

    # =========================
    # 🔷 GENERAR PDF
    # =========================
    doc.build(elements)

    return file_path