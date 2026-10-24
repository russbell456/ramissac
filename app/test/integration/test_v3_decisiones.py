from datetime import date, datetime, timedelta
from uuid import uuid4
from io import BytesIO
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.main import app
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.models.jornada_transporte import JornadaTransporte
from app.models.documento_transporte import DocumentoTransporte
from app.models.notificacion_transporte import NotificacionTransporte
from app.models.mantenimiento import Mantenimiento
from app.schemas.jornada_transporte_schema import RegistroAccionCreate, ChecklistCreate, SubaccionCerrar, SubaccionCancelar
from app.services.jornada_transporte_service import JornadaTransporteService
from app.services.transportes_scheduler import ejecutar_ciclo

FOTO = '/uploads/transportes/abc.jpg'


@pytest.fixture
def base(db_session):
    users = []
    for i, role in enumerate(['admin', 'conductor', 'conductor']):
        user = User(nombre='Prueba', apellidos='V3', dni=f'8888888{i}', email=f'v3{i}@test.com', password='hash', role=role)
        db_session.add(user)
        users.append(user)
    vehiculo = Vehiculo(placa='V3-TST', marca='RAMIS', modelo='Camión Grúa', tipo='Camión Grúa', capacidad_carga=1, kilometraje_actual=100)
    db_session.add(vehiculo)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: users[0]
    yield users, vehiculo, JornadaTransporteService(db_session)
    app.dependency_overrides.pop(get_current_user, None)


def apertura(v, **kwargs):
    return RegistroAccionCreate(accion_tipo='Empezar a Conducir', vehiculo_id=v.id,
        km_inicial=100, ruta='San Rafael', nivel_combustible=50,
        observaciones='Sin novedades', checklist_flash={'Botiquín': False}, **kwargs)


def test_relevo_bloquea_otro_vehiculo_y_cierre_historico_conserva_actual(base, db_session):
    usuarios, v, service = base
    j1 = service.registrar_accion(usuarios[1].id, apertura(v))
    j2 = service.registrar_accion(usuarios[2].id, apertura(v))
    with pytest.raises(HTTPException) as error:
        service.registrar_accion(usuarios[1].id, apertura(v))
    assert error.value.status_code == 409
    v.kilometraje_actual = 300
    db_session.commit()
    service.registrar_checklist_final(j1.id, ChecklistCreate(tipo='final', kilometraje=150,
        nivel_combustible='50', estado_general='Conforme', conforme=True), usuarios[1].id)
    assert v.kilometraje_actual == 300
    assert v.estado == 'en_ruta'
    assert j2.estado == 'en_curso'


def test_grua_concurrencia_instantaneo_cancelacion_y_repeticion(base):
    usuarios, v, service = base
    service.registrar_accion(usuarios[1].id, apertura(v))
    data = RegistroAccionCreate(accion_tipo='Operar Grúa', vehiculo_id=v.id,
        observaciones='Izaje', detalles_grua={'actividad': 'Izaje', 'horometro_inicial': 10})
    sub = service.registrar_accion(usuarios[1].id, data)
    with pytest.raises(HTTPException):
        service.registrar_accion(usuarios[1].id, data)
    combustible = RegistroAccionCreate(accion_tipo='Abastecer Combustible', vehiculo_id=v.id,
        observaciones='Recarga', km_inicial=100, nivel_combustible=75,
        detalles_combustible={'galones': 10, 'nivel_final': 100})
    assert service.registrar_accion(usuarios[1].id, combustible).estado == 'finalizada'
    service.cancelar_subaccion(sub.id, 'Se suspendió por coordinación del trabajo', usuarios[1])
    assert sub.estado == 'cancelada'
    siguiente = service.registrar_accion(usuarios[1].id, data)
    service.cerrar_subaccion(siguiente.id, SubaccionCerrar(horometro_final=12), usuarios[1])
    assert siguiente.estado == 'finalizada'


def test_consolidado_descuenta_una_hora_por_conductor_dia(base, db_session):
    usuarios, v, service = base
    for inicio, fin in [(datetime(2026, 10, 22, 12), datetime(2026, 10, 22, 18)),
                        (datetime(2026, 10, 22, 18), datetime(2026, 10, 22, 23))]:
        db_session.add(JornadaTransporte(vehiculo_id=v.id, conductor_id=usuarios[1].id,
            estado='finalizada', fecha_inicio=inicio, fecha_fin=fin, km_inicial=100, km_final=150))
    db_session.commit()
    resumen = service.consolidar_horas(usuarios[1].id, date(2026, 10, 22))
    assert resumen['horas_brutas'] == 11
    assert resumen['refrigerio'] == 1
    assert resumen['horas_efectivas'] == 10


def test_avisos_nocturnos_idempotentes_y_cierre_2359_lima(base, db_session, monkeypatch):
    monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS', raising=False)
    usuarios, v, service = base
    j = service.registrar_accion(usuarios[1].id, apertura(v))
    j.fecha_inicio = datetime(2026, 10, 22, 12)
    db_session.commit()
    for _ in range(2):
        ejecutar_ciclo(db_session, datetime(2026, 10, 23, 0))  # 19:00 Lima
    assert db_session.query(NotificacionTransporte).filter(NotificacionTransporte.clave.like('%nocturna%')).count() == 2
    ejecutar_ciclo(db_session, datetime(2026, 10, 23, 4, 59))
    assert j.estado == 'cerrada_por_sistema'
    assert j.fecha_fin == datetime(2026, 10, 23, 4, 59)


def test_documentos_renovacion_preserva_versiones_y_roles(base, client, db_session):
    usuarios, v, _ = base
    url = f'/api/transportes/documentos/vehiculo/{v.id}'
    payload = {'tipo': 'soat', 'archivo_url': '/uploads/transportes/abc.pdf', 'fecha_vencimiento': '2027-01-01'}
    assert client.post(url, json=payload).status_code == 201
    payload['fecha_vencimiento'] = '2028-01-01'
    assert client.post(url, json=payload).status_code == 201
    docs = db_session.query(DocumentoTransporte).order_by(DocumentoTransporte.id).all()
    assert docs[0].archivado and not docs[1].archivado
    assert docs[1].version == 2
    app.dependency_overrides[get_current_user] = lambda: usuarios[1]
    assert client.post(url, json=payload).status_code == 403
    assert client.get(url + '/vigencias').status_code == 200


def test_mantenimiento_exige_admin_firma_y_evidencia(base, client, db_session):
    usuarios, v, _ = base
    m = Mantenimiento(vehiculo_id=v.id, fecha_ingreso=datetime.utcnow(), descripcion_falla='Reparación de frenos', costo=0, alcance='mayor')
    db_session.add(m)
    usuarios[0].firma_url = FOTO
    db_session.commit()
    url = f'/api/mantenimientos/{m.id}/cerrar'
    data = {'km_cierre': 100, 'descripcion': 'Reparación completa y verificada'}
    assert client.post(url, json=data).status_code == 400
    data['informe_url'] = '/uploads/transportes/abc.pdf'
    app.dependency_overrides[get_current_user] = lambda: usuarios[1]
    assert client.post(url, json=data).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: usuarios[0]
    assert client.post(url, json=data).status_code == 200
    db_session.refresh(m)
    assert m.aprobado_por_id == usuarios[0].id
    assert m.firma_admin_url == FOTO
    acta = client.get(f'/api/mantenimientos/{m.id}/acta-pdf')
    assert acta.status_code == 200 and acta.content.startswith(b'%PDF')
    assert client.put(f'/api/mantenimientos/{m.id}', json={'estado': 'completado'}).status_code == 409


def test_idempotencia_reintento_y_limite_fotos(base):
    usuarios, v, service = base
    data = apertura(v, solicitud_id=str(uuid4()))
    assert service.registrar_accion(usuarios[1].id, data).id == service.registrar_accion(usuarios[1].id, data).id
    with pytest.raises(ValidationError):
        apertura(v, fotos_observacion=[FOTO] * 6)
    with pytest.raises(ValidationError):
        SubaccionCancelar(motivo='          ')


def test_pdf_filtros_validos_y_descarga(base, client):
    _, v, _ = base
    url = f'/api/vehiculos/{v.id}/reporte-pdf'
    respuesta = client.get(url + '?estado=todas')
    assert respuesta.status_code == 200
    assert respuesta.content.startswith(b'%PDF')
    assert client.get(url + '?desde=2026-10-22&hasta=2026-01-01').status_code == 400


def test_observacion_offline_despues_del_cierre_se_recupera_sin_duplicar(base, client, db_session):
    usuarios, v, service = base
    jornada = service.registrar_accion(usuarios[1].id, apertura(v))
    fecha = datetime.utcnow()
    service.registrar_checklist_final(jornada.id, ChecklistCreate(tipo='final', kilometraje=150,
        conforme=True, estado_general='Conforme', nivel_combustible='50'), usuarios[1].id)
    app.dependency_overrides[get_current_user] = lambda: usuarios[1]
    url = f'/api/jornadas/{jornada.id}/incidencias'
    data = {'solicitud_id': str(uuid4()), 'tipo': 'falla', 'severidad': 'moderada',
        'descripcion': 'Observación reportada sin señal', 'fotos': [FOTO], 'fecha': fecha.isoformat()}
    primero = client.post(url, json=data)
    segundo = client.post(url, json=data)
    assert primero.status_code == segundo.status_code == 201
    assert primero.json()['id'] == segundo.json()['id']
    app.dependency_overrides[get_current_user] = lambda: usuarios[0]
    resuelta = client.post(f'/api/transportes/observaciones/incidencia/{primero.json()["id"]}/resolver',
        json={'descripcion': 'Reparación revisada por administración', 'foto_url': FOTO})
    assert resuelta.status_code == 200
    assert resuelta.json()['estado_semaforo'] == 'verde'


def test_alta_rapida_y_activacion_no_rompen_listado_conductores(base, client):
    response = client.post('/api/transportes/conductores/alta-rapida', json={'nombre': 'Conductor nuevo', 'dni': '71234567'})
    assert response.status_code == 201
    assert client.get('/auth/trabajadores').status_code == 200
    id = response.json()['id']
    activation = client.put(f'/api/transportes/conductores/{id}/acceso',
        json={'email': 'conductor-nuevo@test.com', 'password': 'AccesoNuevo123'})
    assert activation.status_code == 200
    assert client.post('/auth/login', json={'email': 'conductor-nuevo@test.com', 'password': 'AccesoNuevo123'}).status_code == 200
