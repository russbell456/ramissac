from io import BytesIO
from uuid import uuid4
from PIL import Image
from app.main import app
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.documento_transporte import DocumentoTransporte
from app.test.integration.test_v3_decisiones import base


def imagen():
    output = BytesIO()
    Image.new('RGB', (16, 16), 'white').save(output, format='PNG')
    return output.getvalue()


def test_conductor_envia_revision_y_admin_aprueba_sin_duplicados(base, client, db_session, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    usuarios, _, _ = base
    app.dependency_overrides[get_current_user] = lambda: usuarios[1]
    url = f'/api/transportes/documentos/conductor/{usuarios[1].id}'
    fields = {'tipo': 'licencia', 'fecha_vencimiento': '2027-11-01', 'licencia_categoria': 'A-IIb', 'solicitud_id': str(uuid4())}
    response = client.post(url, data=fields, files={'file': ('licencia.png', imagen(), 'image/png')})
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc['estado'] == 'pendiente'
    repetida = client.post(url, data=fields, files={'file': ('licencia.png', imagen(), 'image/png')})
    assert repetida.status_code == 201 and repetida.json()['id'] == doc['id']
    assert len(list((tmp_path / 'uploads/transportes').iterdir())) == 1
    vigencias = client.get(url + '/vigencias').json()
    licencia = next(d for d in vigencias if d['tipo'] == 'licencia')
    assert licencia['estado_documento'] == 'pendiente' and licencia['licencia_categoria'] == 'A-IIb'
    assert licencia['archivo_url'] == doc['archivo_url']
    assert isinstance(licencia['dias_restantes'], int)
    revisar = f'/api/transportes/documentos/{doc["id"]}/revisar'
    assert client.post(revisar, json={'estado': 'aprobado'}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: usuarios[0]
    assert client.post(revisar, json={'estado': 'aprobado'}).status_code == 200
    db_session.refresh(usuarios[1])
    assert usuarios[1].licencia_categoria == 'A-IIb'


def test_rechazo_motivo_versiones_y_titularidad(base, client, db_session, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    usuarios, _, _ = base
    app.dependency_overrides[get_current_user] = lambda: usuarios[1]
    url = f'/api/transportes/documentos/conductor/{usuarios[1].id}'
    fields = {'tipo': 'emo', 'fecha_vencimiento': '2027-01-01', 'solicitud_id': str(uuid4())}
    assert client.post(f'/api/transportes/documentos/conductor/{usuarios[2].id}', data=fields,
        files={'file': ('emo.png', imagen(), 'image/png')}).status_code == 403
    response = client.post(url, data=fields, files={'file': ('emo.png', imagen(), 'image/png')})
    id = response.json()['id']
    app.dependency_overrides[get_current_user] = lambda: usuarios[0]
    revisar = f'/api/transportes/documentos/{id}/revisar'
    assert client.post(revisar, json={'estado': 'rechazado', 'motivo': 'No'}).status_code == 400
    assert client.post(revisar, json={'estado': 'rechazado', 'motivo': 'El documento es ilegible'}).status_code == 200
    assert next(d for d in client.get(url + '/vigencias').json() if d['tipo'] == 'emo')['motivo_rechazo'] == 'El documento es ilegible'
    app.dependency_overrides[get_current_user] = lambda: usuarios[1]
    fields['solicitud_id'] = str(uuid4())
    nueva = client.post(url, data=fields, files={'file': ('emo.pdf', b'%PDF-1.4\n%%EOF', 'application/pdf')})
    assert nueva.status_code == 201 and nueva.json()['version'] == 2
    assert db_session.query(DocumentoTransporte).filter_by(id=id).one().archivado is True
    fields['solicitud_id'] = str(uuid4())
    assert client.post(url, data=fields, files={'file': ('falso.pdf', b'not-a-pdf', 'application/pdf')}).status_code == 400
    assert client.post(url, data=fields, files={'file': ('grande.pdf', b'x' * (10*1024*1024+1), 'application/pdf')}).status_code == 413


def test_listado_conductores_alta_apellidos_y_aliases_vehiculos(base, client):
    response = client.post('/api/transportes/conductores/alta-rapida', json={'dni': '78901234', 'nombre': 'Ana', 'apellidos': 'Prueba Móvil'})
    assert response.status_code == 201
    conductores = client.get('/api/transportes/conductores').json()
    ana = next(c for c in conductores if c['dni'] == '78901234')
    assert ana['apellidos'] == 'Prueba Móvil' and len(ana['documentos']) >= 3
    response = client.post('/api/transportes/vehiculos', json={'placa': 'DOC-001', 'modelo': 'Camioneta'})
    assert response.status_code == 201
    id = response.json()['id']
    assert client.get('/api/transportes/vehiculos').status_code == 200
    pdf = client.get(f'/api/transportes/vehiculos/{id}/reporte-pdf')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
