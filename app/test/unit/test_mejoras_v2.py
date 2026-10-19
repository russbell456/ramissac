import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.test.unit.test_jornada_transporte import _crear_base, _abrir
from app.schemas.jornada_transporte_schema import RegistroAccionCreate, ChecklistCreate, IncidenciaRutaCreate, JornadaDetalleResponse
from app.services.jornada_transporte_service import JornadaTransporteService
from app.models.jornada_transporte import JornadaTransporte

FOTO = '/uploads/transportes/abc.jpg'

def accion(vehiculo, **kwargs):
    values = dict(accion_tipo='Abastecer Combustible', vehiculo_id=vehiculo.id, km_inicial=100,
                  nivel_combustible=75, observaciones='Sin novedades', detalles_combustible={'galones': 10, 'nivel_final': 100})
    values.update(kwargs)
    return RegistroAccionCreate(**values)

def test_subaccion_requiere_jornada_y_no_modifica_odometro_al_rechazar(db_session):
    c, v = _crear_base(db_session)
    with pytest.raises(HTTPException) as err:
        JornadaTransporteService(db_session).registrar_accion(c.id, accion(v, km_inicial=150))
    assert err.value.status_code == 409
    assert v.kilometraje_actual == 100

def test_parent_and_consumo_con_varios_abastecimientos(db_session):
    c, v = _crear_base(db_session)
    v.capacidad_tanque_galones = 40
    service = JornadaTransporteService(db_session)
    padre = _abrir(service, c, v)
    for _ in range(2):
        sub = service.registrar_accion(c.id, accion(v))
        assert sub.jornada_padre_id == padre.id
    assert db_session.query(JornadaTransporte).filter_by(estado='en_curso').count() == 1
    cierre = service.registrar_checklist_final(padre.id, ChecklistCreate(tipo='final', kilometraje=200, nivel_combustible='50', estado_general='Bueno', conforme=True), c.id)
    assert cierre.galones_abastecidos == 20
    assert cierre.galones_consumidos == 30  # 75%-50% de 40 gal + 20 gal
    assert cierre.rendimiento_km_galon == pytest.approx(3.3333)
    assert len(JornadaDetalleResponse.model_validate(cierre).sub_acciones) == 2

def test_consumo_sin_capacidad_no_inventa_galones(db_session):
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    j = _abrir(s, c, v)
    j = s.registrar_checklist_final(j.id, ChecklistCreate(tipo='final', kilometraje=150, nivel_combustible='1/2', estado_general='Bueno', conforme=True), c.id)
    assert j.galones_consumidos is None
    assert j.rendimiento_km_galon is None

@pytest.mark.parametrize('severidad,color,estado', [('leve','amarillo','en_curso'), ('grave','rojo','en_curso')])
def test_semaforo_subaccion_se_propaga_y_persiste(db_session, severidad, color, estado):
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    padre = _abrir(s, c, v)
    s.registrar_accion(c.id, accion(v, tiene_observaciones=True, severidad=severidad, foto_observacion=FOTO, observaciones='Falla detectada'))
    db_session.refresh(padre)
    assert padre.estado_semaforo == v.estado_semaforo == color
    assert padre.estado == estado
    if color == 'rojo':
        assert v.estado == 'en_mantenimiento'
        assert v.averias[0].criticidad == 'critica'

def test_doble_jornada_y_parent_ajeno_rechazados(db_session):
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    _abrir(s, c, v)
    with pytest.raises(HTTPException):
        _abrir(s, c, v)
    with pytest.raises(HTTPException):
        s.registrar_accion(c.id, accion(v, jornada_padre_id=999))

def test_grua_restringida_por_tipo_en_servidor(db_session):
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    _abrir(s, c, v)
    datos = accion(v, accion_tipo='Operar Grúa', detalles_combustible=None, detalles_grua={'actividad':'Izaje','horometro_inicial':1,'horometro_final':2})
    with pytest.raises(HTTPException):
        s.registrar_accion(c.id, datos)
    v.tipo = 'Camión Grúa'
    assert s.registrar_accion(c.id, datos).detalles_grua is not None

def test_checklist_no_conforme_exige_evidencia_y_bloquea(db_session):
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    datos = accion(v, accion_tipo='Empezar a Conducir', detalles_combustible=None, ruta='Juliaca', checklist_flash={'Frenos':False})
    with pytest.raises(HTTPException):
        s.registrar_accion(c.id, datos)
    datos = datos.model_copy(update={'tiene_observaciones':True,'severidad':'grave','foto_observacion':FOTO,'observaciones':'Frenos dañados'})
    assert s.registrar_accion(c.id, datos).estado == 'cancelada_por_averia'
    assert v.estado == 'en_mantenimiento'

def test_evidencia_no_acepta_url_externa_o_descripcion_vacia():
    with pytest.raises(ValidationError):
        RegistroAccionCreate(accion_tipo='Reporte de Incidencias u Observaciones', vehiculo_id=1, km_inicial=100, nivel_combustible=50, tiene_observaciones=True, severidad='grave', observaciones='Falla', foto_observacion='https://example.com/a.jpg')

def test_incidencia_critica_cancela_jornada(db_session):
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    j = _abrir(s, c, v)
    s.registrar_incidencia(j.id, IncidenciaRutaCreate(tipo='falla', descripcion='Fuga de combustible', severidad='grave', foto_incidencia=FOTO), c.id)
    assert j.estado_semaforo == 'rojo'
    assert j.foto_observacion == FOTO
    assert v.estado == 'en_mantenimiento'


def test_upload_imagen_valida_y_rechaza_contenido_falso(client, monkeypatch, tmp_path):
    from io import BytesIO
    from PIL import Image
    from app.main import app
    from app.models.user import User
    from app.dependencies.auth_dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: User(id=1, role='conductor')
    monkeypatch.chdir(tmp_path)
    imagen = BytesIO()
    Image.new('RGB', (2, 2)).save(imagen, format='PNG')
    response = client.post('/api/jornadas/fotos', files={'file': ('../foto.png', imagen.getvalue(), 'image/png')})
    assert response.status_code == 201
    ruta = response.json()['url']
    assert ruta.startswith('/uploads/transportes/')
    assert (tmp_path / ruta.lstrip('/')).exists()
    assert client.post('/api/jornadas/fotos', files={'file': ('falso.jpg', b'not-an-image', 'image/jpeg')}).status_code == 400
    assert client.post('/api/jornadas/fotos', files={'file': ('grande.jpg', b'x' * (5 * 1024 * 1024 + 1), 'image/jpeg')}).status_code == 413


def test_post_mantenimiento_restaurar_semaforo(db_session):
    from app.services.lifecycle_service import LifecycleService
    c, v = _crear_base(db_session)
    v.estado = 'observado'
    v.estado_semaforo = 'rojo'
    LifecycleService(db_session).liberar_post_mantenimiento(v)
    assert v.estado == 'disponible'
    assert v.estado_semaforo == 'verde'


@pytest.mark.parametrize('flujo', ['apertura', 'asignacion', 'checklist_asignado'])
def test_rojo_rechaza_apertura_y_asignacion_con_400(db_session, flujo):
    from app.schemas.jornada_transporte_schema import JornadaAsignacionCreate
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    if flujo == 'checklist_asignado':
        j = s.asignar(JornadaAsignacionCreate(vehiculo_id=v.id, conductor_id=c.id))
    v.estado_semaforo = 'rojo'
    db_session.commit()
    with pytest.raises(HTTPException) as err:
        if flujo == 'apertura': _abrir(s, c, v)
        elif flujo == 'asignacion': s.asignar(JornadaAsignacionCreate(vehiculo_id=v.id, conductor_id=c.id))
        else: s.registrar_checklist_inicial(j.id, ChecklistCreate(kilometraje=100, nivel_combustible='75', estado_general='Bueno', conforme=True), c.id)
    assert err.value.status_code == 400


def test_amarillo_es_persistente_al_abrir_jornada(db_session):
    c, v = _crear_base(db_session)
    v.estado_semaforo = 'amarillo'
    j = _abrir(JornadaTransporteService(db_session), c, v)
    assert j.estado == 'en_curso'
    assert j.estado_semaforo == v.estado_semaforo == 'amarillo'


def test_grua_solo_horometros_no_actualiza_odometro_ni_cierra_padre(db_session):
    c, v = _crear_base(db_session)
    v.tipo = 'Camión Grúa'
    s = JornadaTransporteService(db_session)
    padre = _abrir(s, c, v)
    for _ in range(2):
        sub = s.registrar_accion(c.id, RegistroAccionCreate(accion_tipo='Operar Grúa', vehiculo_id=v.id, jornada_padre_id=padre.id, observaciones='Sin novedades', detalles_grua={'actividad':'Izaje','horometro_inicial':10,'horometro_final':12}))
        assert sub.jornada_padre_id == padre.id
        assert sub.km_inicial is None
    assert v.kilometraje_actual == padre.km_inicial == 100
    assert padre.estado == 'en_curso'
    assert padre.fecha_fin is None
    assert padre.km_final is None
    detalle = JornadaDetalleResponse.model_validate(s.obtener(padre.id))
    assert detalle.sub_acciones[0].detalles_grua.horometro_final == 12


@pytest.mark.parametrize('canal', ['incidencia', 'subaccion'])
def test_reporte_grave_mantiene_jornada_abierta_hasta_cierre_explicito(db_session, canal):
    c, v = _crear_base(db_session)
    v.capacidad_tanque_galones = 40
    s = JornadaTransporteService(db_session)
    padre = _abrir(s, c, v)
    if canal == 'incidencia':
        s.registrar_incidencia(padre.id, IncidenciaRutaCreate(tipo='falla', severidad='grave', foto_incidencia=FOTO, descripcion='Falla de frenos'), c.id)
    else:
        sub = s.registrar_accion(c.id, RegistroAccionCreate(accion_tipo='Reporte de Incidencias u Observaciones', vehiculo_id=v.id, jornada_padre_id=padre.id, tiene_observaciones=True, severidad='grave', foto_observacion=FOTO, observaciones='Falla de frenos'))
        assert sub.jornada_padre_id == padre.id
    assert padre.estado == 'en_curso'
    assert padre.fecha_fin is None
    assert padre.km_final is None
    assert v.estado_semaforo == 'rojo'
    assert v.estado == 'en_mantenimiento'
    cierre = s.registrar_checklist_final(padre.id, ChecklistCreate(tipo='final', kilometraje=200, nivel_combustible='50', conforme=True, estado_general='Unidad detenida por falla reportada'), c.id)
    assert cierre.estado == 'finalizada'
    assert cierre.km_final == 200
    assert cierre.galones_consumidos == 10
    assert cierre.rendimiento_km_galon == 10
    assert v.estado == 'en_mantenimiento'
    assert v.estado_semaforo == 'rojo'



def test_observacion_leve_posterior_no_oculta_falla_critica_pendiente(db_session):
    from app.schemas.vehiculo_schema import VehiculoResponse
    c, v = _crear_base(db_session)
    s = JornadaTransporteService(db_session)
    padre = _abrir(s, c, v)
    s.registrar_incidencia(padre.id, IncidenciaRutaCreate(tipo='falla', severidad='grave', foto_incidencia=FOTO, descripcion='Frenos averiados'), c.id)
    s.registrar_incidencia(padre.id, IncidenciaRutaCreate(tipo='falla', severidad='leve', foto_incidencia=FOTO, descripcion='Rayadura de carrocería'), c.id)
    assert v.estado_semaforo == padre.estado_semaforo == 'rojo'
    assert padre.estado == 'en_curso'
    assert padre.observaciones == 'Frenos averiados'
    assert VehiculoResponse.model_validate(v).observaciones_pendientes == 'Frenos averiados'
