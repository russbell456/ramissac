import base64

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.models.almacen_obras import AlmacenObra
from app.test.test_rq_engineer_changes import archivo_foto


def usuario(db, rol, numero):
    user = User(nombre=rol, apellidos='Prueba', dni=f'{numero:08d}',
                email=f'{rol}{numero}@example.com', password='x', role=rol)
    db.add(user)
    db.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    return user


def nuevo(codigo='010-2026', descripcion='Canales'):
    return {'obra_codigo': codigo, 'obra_descripcion': descripcion, 'items': [
        {'tipo': 'NO_CATALOGADO', 'nombre_producto': 'Equipo de medición',
         'unidad_medida': 'piezas', 'cantidad': 2.5,
         'descripcion': 'Tipo: Equipo\nPrecisión 0.01 mm'},
        {'tipo': 'NO_CATALOGADO', 'nombre_producto': 'Cemento',
         'unidad_medida': 'bolsas', 'cantidad': 5, 'descripcion': 'Tipo: Material'}]}


def test_obra_libre_reutilizada_y_correlativo_por_obra(client, db_session):
    usuario(db_session, 'supervisor', 1)
    primera = client.post('/rq-campo', json=nuevo())
    assert primera.status_code == 201, primera.text
    a = primera.json()
    b = client.post('/rq-campo', json=nuevo(descripcion='Mantenimiento de canales')).json()
    c = client.post('/rq-campo', json=nuevo('011-2026')).json()
    assert a['obra_id'] == b['obra_id'] != c['obra_id']
    assert a['numero'] == 'RQ-001-010-2026'
    assert b['numero'] == 'RQ-002-010-2026'
    assert c['numero'] == 'RQ-001-011-2026'
    assert b['nombre_proyecto'] == '010-2026 - Mantenimiento de canales'
    assert db_session.query(AlmacenObra).count() == 2
    assert a['items'][0]['unidad_medida'] == 'piezas'
    assert client.get(f"/rq-campo/{a['id']}/pdf").content.startswith(b'%PDF')
    assert client.post('/rq-campo', json=nuevo('10-2026')).status_code == 400
    assert client.post('/rq-campo', json=nuevo('012-2026', '')).status_code == 400


def test_seguimiento_roles_y_cierre_sin_compra(client, db_session, monkeypatch):
    supervisor = usuario(db_session, 'supervisor', 1)
    rq = client.post('/rq-campo', json=nuevo()).json()
    rid = rq['id']
    iid, segundo = [i['id'] for i in rq['items']]
    url = f'/rq-campo/{rid}/items/{iid}/gestion'
    monkeypatch.setattr('app.services.rq_campo_service.RqEmailService.enviar', lambda *a: None)
    firma = base64.b64encode(archivo_foto()).decode()
    assert client.patch(url, json={'estado': 'POR_COMPRAR'}).status_code == 400
    assert client.post(f'/rq-campo/{rid}/firmar-y-enviar', json={
        'firma_base64': firma, 'destinatarios': ['compras@example.com']}).status_code == 200
    assert client.patch(url, json={'estado': 'COMPRADO'}).status_code == 403
    usuario(db_session, 'compras', 2)
    assert client.get(f'/rq-campo/{rid}').status_code == 200
    assert client.patch(url, json={'estado': 'EN_PROCESO'}).status_code == 400
    assert client.patch(url, json={'estado': 'POR_COMPRAR'}).status_code == 403
    usuario(db_session, 'logistica', 3)
    assert client.patch(url, json={'estado': 'POR_COMPRAR'}).json()['estado_gestion'] == 'EN_PROCESO'
    assert client.patch(url, json={'estado': 'COMPRADO'}).status_code == 403
    usuario(db_session, 'compras', 4)
    assert client.patch(url, json={'estado': 'EN_PROCESO'}).status_code == 200
    assert client.patch(url, json={'estado': 'COMPRADO'}).status_code == 200
    foto = {'nombre': 'Equipo real.png', 'tipo_mime': 'image/png', 'contenido_base64': firma}
    evidence = client.patch(url, json={'estado': 'COMPRADO', 'detalle': 'Marca adquirida', 'adjuntos': [foto]})
    assert evidence.status_code == 200, evidence.text
    item = evidence.json()['items'][0]
    assert item['detalle_gestion'] == 'Marca adquirida'
    assert item['adjuntos_gestion'][0]['contenido_base64'] == firma
    assert item['descripcion'] == 'Tipo: Equipo\nPrecisión 0.01 mm'
    usuario(db_session, 'logistica', 5)
    url2 = f'/rq-campo/{rid}/items/{segundo}/gestion'
    assert client.patch(url2, json={'estado': 'CERRADO_SIN_COMPRA'}).status_code == 400
    result = client.patch(url2, json={'estado': 'CERRADO_SIN_COMPRA', 'nota': 'Ya no se requiere'})
    assert result.json()['estado_gestion'] == 'FINALIZADO'
    app.dependency_overrides[get_current_user] = lambda: supervisor
    final = client.get(f'/rq-campo/{rid}').json()
    assert final['estado_gestion'] == 'FINALIZADO'
    assert final['items'][1]['nota_gestion'] == 'Ya no se requiere'
    assert client.put(f'/rq-campo/{rid}', json=nuevo()).status_code == 400
