import base64
import io

import pytest
from PIL import Image
from pydantic import ValidationError
from reportlab.pdfgen import canvas

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_obras import AlmacenObra
from app.models.user import User
from app.schemas.rq_campo import RqAdjuntoCreate, RqCampoCreate


def archivo_pdf():
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(40, 750, 'Ficha de prueba')
    pdf.save()
    return output.getvalue()


def archivo_foto():
    output = io.BytesIO()
    Image.new('RGB', (600, 400), '#193D8F').save(output, format='PNG')
    return output.getvalue()


@pytest.fixture()
def scenario(db_session):
    user = User(nombre='Ana', apellidos='Quispe', dni='87654321', cargo='Ingeniera', email='ana@example.com', password='x', role='logistica')
    active = AlmacenObra(nombre='Obra registrada', estado='activo')
    closed = AlmacenObra(nombre='Obra cerrada', estado='cerrado')
    article = AlmacenArticulo(nombre='Llave', unidad_medida='UND', tipo=TipoArticulo.HERRAMIENTA, stock_actual=0)
    db_session.add_all([user, active, closed, article])
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    return user, active, closed, article


def payload(obra, article):
    return {'obra_id': obra.id, 'nombre_proyecto': 'Nombre libre que debe ignorarse', 'items': [
        {'tipo': 'CATALOGADO', 'articulo_id': article.id, 'cantidad': 2.5}
    ]}


def test_obra_canonica_stock_cero_y_rechazo_de_cerradas(client, scenario):
    _, active, closed, article = scenario
    assert article.id in [a['id'] for a in client.get('/articulo/buscar', params={'q': ''}).json()]
    response = client.post('/rq-campo', json=payload(active, article))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data['nombre_proyecto'] == active.nombre
    assert data['items'][0]['cantidad'] == '2.50'
    assert client.get(f"/rq-campo/{data['id']}/pdf").status_code == 200
    stock = client.get(f"/rq-campo/{data['id']}/stock").json()[0]
    assert stock['stock_actual'] == 0 and float(stock['faltante']) == 2.5
    assert stock['numero_item'] == 1
    assert client.post('/rq-campo', json=payload(closed, article)).status_code == 400
    invalid = payload(active, article)
    invalid['obra_id'] = 99999
    assert client.post('/rq-campo', json=invalid).status_code == 400
    assert len(client.get('/rq-campo').json()) == 1


def test_adjuntos_se_conservan_en_api_pdf_y_correo(client, scenario, monkeypatch):
    _, active, _, article = scenario
    request = payload(active, article)
    request['items'][0]['adjuntos'] = [
        {'nombre': 'Foto.png', 'tipo_mime': 'image/png', 'contenido_base64': base64.b64encode(archivo_foto()).decode()},
        {'nombre': 'Ficha.pdf', 'tipo_mime': 'application/pdf', 'contenido_base64': base64.b64encode(archivo_pdf()).decode()},
    ]
    response = client.post('/rq-campo', json=request)
    assert response.status_code == 201, response.text
    rq_id = response.json()['id']
    data = client.get(f'/rq-campo/{rq_id}').json()
    assert [a['nombre'] for a in data['items'][0]['adjuntos']] == ['Foto.png', 'Ficha.pdf']
    assert data['items'][0]['adjuntos'][1]['contenido_base64'] == request['items'][0]['adjuntos'][1]['contenido_base64']
    pdf = client.get(f'/rq-campo/{rq_id}/pdf').content
    assert pdf.startswith(b'%PDF') and b'/Subtype /Image' in pdf
    assert pdf.count(b'/Type /Page\n') >= 2
    assert client.put(f'/rq-campo/{rq_id}', json=request).status_code == 200
    assert len(client.get(f'/rq-campo/{rq_id}').json()['items'][0]['adjuntos']) == 2
    sent = []
    monkeypatch.setattr('app.services.rq_campo_service.RqEmailService.enviar', lambda *args: sent.append(args))
    firma = base64.b64encode(archivo_foto()).decode()
    assert client.post(f'/rq-campo/{rq_id}/firmar-y-enviar', json={'firma_base64': firma, 'destinatarios': ['compras@example.com']}).status_code == 200
    assert len(sent) == 1
    assert client.put(f'/rq-campo/{rq_id}', json=request).status_code == 400


@pytest.mark.parametrize('mime,contenido', [('application/pdf', b'No es PDF'), ('image/png', b'\x89PNGbad'), ('application/x-msdownload', b'bad')])
def test_rechaza_archivos_invalidos(mime, contenido):
    with pytest.raises(ValidationError):
        RqAdjuntoCreate(nombre='archivo', tipo_mime=mime, contenido_base64=base64.b64encode(contenido).decode())


def test_limites_de_adjuntos():
    file = {'nombre': 'Ficha.pdf', 'tipo_mime': 'application/pdf', 'contenido_base64': base64.b64encode(archivo_pdf()).decode()}
    with pytest.raises(ValidationError):
        RqCampoCreate.model_validate({'obra_id': 1, 'items': [{'tipo': 'NO_CATALOGADO', 'nombre_producto': 'Producto', 'unidad_medida': 'UND', 'cantidad': 1, 'adjuntos': [file]*6}]})
    with pytest.raises(ValidationError):
        RqAdjuntoCreate(nombre='Ficha.pdf', tipo_mime='application/pdf', contenido_base64=base64.b64encode(b'%PDF-' + b'x'*(5*1024*1024)).decode())


def test_ficha_catalogo_y_snapshot_en_requerimiento(client, scenario):
    _, active, _, article = scenario
    response = client.put(f'/articulo/{article.id}', json={'nombre': 'Llave actualizada', 'descripcion': 'Acero', 'medidas': '24 mm', 'especificaciones': 'Boca abierta', 'observacion': 'Uso en montaje'})
    assert response.status_code == 200, response.text
    assert response.json()['medidas'] == '24 mm'
    doc = archivo_pdf()
    assert client.post(f'/articulo/{article.id}/ficha-tecnica', files={'file': ('Ficha.pdf', doc, 'application/pdf')}).status_code == 200
    assert client.get(f'/articulo/{article.id}/ficha-tecnica').content == doc
    assert client.get('/articulo').json()[0]['ficha_tecnica_nombre'] == 'Ficha.pdf'
    rq = client.post('/rq-campo', json=payload(active, article)).json()
    item = rq['items'][0]
    assert item['medidas'] == '24 mm'
    assert 'Boca abierta' in item['descripcion']
    assert item['adjuntos'][0]['nombre'] == 'Ficha.pdf'
    client.put(f'/articulo/{article.id}', json={'medidas': '30 mm'})
    assert client.get(f"/rq-campo/{rq['id']}").json()['items'][0]['medidas'] == '24 mm'
    assert client.post(f'/articulo/{article.id}/ficha-tecnica', files={'file': ('Falso.pdf', b'invalid', 'application/pdf')}).status_code == 400


def test_cerrar_obra_despues_de_crear_impide_firma(client, scenario, db_session, monkeypatch):
    _, active, _, article = scenario
    rq = client.post('/rq-campo', json=payload(active, article)).json()
    active.estado = 'cerrado'
    db_session.commit()
    sent = []
    monkeypatch.setattr('app.services.rq_campo_service.RqEmailService.enviar', lambda *args: sent.append(args))
    response = client.post(f"/rq-campo/{rq['id']}/firmar-y-enviar", json={'firma_base64': base64.b64encode(archivo_foto()).decode(), 'destinatarios': ['a@example.com']})
    assert response.status_code == 400
    assert not sent


def test_correo_entrega_pdf_principal_y_fichas_originales(monkeypatch):
    from datetime import datetime
    from types import SimpleNamespace
    from app.services.rq_email_service import RqEmailService
    sent = []
    class Smtp:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def starttls(self): pass
        def send_message(self, message): sent.append(message)
    monkeypatch.setenv('RQ_SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('RQ_SMTP_FROM_EMAIL', 'origen@example.com')
    monkeypatch.delenv('RQ_SMTP_USERNAME', raising=False)
    monkeypatch.delenv('RQ_SMTP_PASSWORD', raising=False)
    monkeypatch.setattr('app.services.rq_email_service.smtplib.SMTP', Smtp)
    doc = archivo_pdf()
    rq = SimpleNamespace(numero='RQ-001-2026', nombre_proyecto='Obra', solicitante_nombre='Ana', solicitante_cargo='Ingeniera', fecha_requerimiento=datetime(2026, 10, 1), items=[
        SimpleNamespace(numero_item=1, adjuntos=[SimpleNamespace(nombre='Ficha.pdf', tipo_mime='application/pdf', contenido_base64=base64.b64encode(doc).decode())])
    ])
    RqEmailService.enviar(rq, ['compras@example.com'], b'%PDF-principal')
    attachments = list(sent[0].iter_attachments())
    assert len(attachments) == 2
    assert attachments[0].get_filename() == 'RQ-001-2026.pdf'
    assert attachments[1].get_payload(decode=True) == doc
    assert attachments[1].get_filename() == 'Item-1-Ficha.pdf'
