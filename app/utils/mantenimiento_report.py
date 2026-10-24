from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from app.utils.transport_time import local_time


def generar_acta(mantenimiento, administrador):
    salida = BytesIO()
    styles = getSampleStyleSheet()
    historia = [Paragraph('RAMIS S.A.C. — Acta de aprobación de mantenimiento', styles['Title']),
        Spacer(1, .5 * cm),
        Paragraph(f'Mantenimiento #{mantenimiento.id} · Vehículo #{mantenimiento.vehiculo_id}', styles['Heading2']),
        Paragraph(f'Odómetro de cierre: {mantenimiento.km_ejecucion:.1f} km', styles['BodyText']),
        Paragraph(escape(mantenimiento.descripcion_trabajo or ''), styles['BodyText']),
        Spacer(1, .5 * cm),
        Paragraph('Aprobación autenticada', styles['Heading2']),
        Paragraph(escape(f'{administrador.nombre} {administrador.apellidos} · Usuario #{administrador.id}'), styles['BodyText']),
        Paragraph(local_time(mantenimiento.fecha_cierre).strftime('%d/%m/%Y %H:%M:%S · Lima'), styles['BodyText'])]
    raiz = (Path.cwd() / 'uploads' / 'transportes').resolve()
    urls = [mantenimiento.firma_admin_url] + (mantenimiento.fotos_cierre or [])
    for url in urls:
        if not url:
            continue
        ruta = (Path.cwd() / url.lstrip('/')).resolve()
        if ruta.is_relative_to(raiz) and ruta.is_file():
            imagen = Image(str(ruta))
            imagen._restrictSize(10 * cm, 6 * cm)
            historia.extend([Spacer(1, .3 * cm), imagen])
    SimpleDocTemplate(salida, pagesize=A4).build(historia)
    salida.seek(0)
    return salida
