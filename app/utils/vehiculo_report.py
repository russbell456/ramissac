from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def estado_vigencia(vencimiento: date | None, hoy: date | None = None) -> str:
    if vencimiento is None:
        return "pendiente"
    dias = (vencimiento - (hoy or date.today())).days
    if dias <= 0:
        return "vencido"
    if dias <= 15:
        return "rojo"
    if dias <= 30:
        return "amarillo"
    return "verde"


def generar_reporte_vehiculo(vehiculo, jornadas, mantenimientos) -> BytesIO:
    salida = BytesIO()
    estilos = getSampleStyleSheet()
    doc = SimpleDocTemplate(salida, pagesize=A4, title=f"Hoja de Vida {vehiculo.placa}")
    contenido = [
        Paragraph("RAMIS S.A.C. — Hoja de Vida / Reporte Técnico", estilos["Title"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"Placa: <b>{escape(vehiculo.placa)}</b> · Modelo: {escape(vehiculo.modelo)} · "
            f"Kilometraje: {vehiculo.kilometraje_actual:.1f} km · Semáforo: {vehiculo.estado_semaforo.upper()}",
            estilos["BodyText"],
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("Vigencia documental", estilos["Heading2"]),
    ]
    documentos = [
        ("SOAT", vehiculo.soat_vencimiento), ("Revisión técnica", vehiculo.rt_vencimiento),
        ("Seguro / SCTR", vehiculo.poliza_vencimiento), ("Pase minero", vehiculo.pase_minero_vencimiento),
    ]
    tabla = [["Documento", "Vencimiento", "Estado"]] + [
        [nombre, valor.isoformat() if valor else "Pendiente", estado_vigencia(valor).upper()]
        for nombre, valor in documentos
    ]
    tabla.append(['Tarjeta de propiedad', 'Sin vencimiento', 'VERDE' if vehiculo.tarjeta_propiedad_url else 'PENDIENTE'])
    contenido.append(_tabla(tabla, [7 * cm, 5 * cm, 4 * cm]))
    contenido += [Spacer(1, 0.4 * cm), Paragraph("Observaciones", estilos["Heading2"])]
    filas = [["Fecha", "Conductor", "Severidad / Estado", "Descripción", "Evidencia"]]
    for jornada in jornadas:
        evidencia = "—"
        fotos = getattr(jornada, 'fotos_observacion', None) or ([jornada.foto_observacion] if jornada.foto_observacion else [])
        miniaturas = []
        for foto in fotos:
            raiz = (Path.cwd() / "uploads" / "transportes").resolve()
            ruta = (Path.cwd() / foto.lstrip("/\\")).resolve()
            if ruta.is_relative_to(raiz) and ruta.is_file():
                try:
                    miniaturas.append(Image(str(ruta), width=1.4 * cm, height=1.4 * cm))
                except Exception:
                    pass
        evidencia = miniaturas or evidencia
        filas.append([
            jornada.fecha_inicio.strftime("%Y-%m-%d") if jornada.fecha_inicio else "—",
            Paragraph(escape(getattr(jornada, 'conductor_nombre', str(jornada.conductor_id))), estilos['BodyText']),
            Paragraph(f'{jornada.severidad or "—"}<br/>{"Resuelta" if getattr(jornada, "observacion_resuelta", False) else "Pendiente"}', estilos['BodyText']),
            Paragraph(escape(jornada.observaciones or "—"), estilos["BodyText"]), evidencia,
        ])
    contenido.append(_tabla(filas, [2.4 * cm, 2.1 * cm, 2.3 * cm, 7.2 * cm, 2 * cm]))
    contenido += [Spacer(1, 0.4 * cm), Paragraph("Historial de mantenimientos", estilos["Heading2"])]
    contenido.append(_tabla(
        [["Fecha", "Tipo", "Estado", "Trabajo"]] + [[
            item.fecha_ingreso.strftime("%Y-%m-%d"), item.tipo, item.estado,
            Paragraph(escape(item.descripcion_trabajo or item.descripcion_falla), estilos["BodyText"]),
        ] for item in mantenimientos],
        [3 * cm, 3 * cm, 3 * cm, 7 * cm],
    ))
    doc.build(contenido)
    salida.seek(0)
    return salida


def _tabla(datos, anchos):
    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f7")]),
    ]))
    return tabla
