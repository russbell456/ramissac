from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.auditoria_sistema import AuditoriaSistema
from app.models.jornada_transporte import JornadaTransporte
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.schemas.jornada_transporte_schema import RegistroAccionCreate
from app.services.jornada_transporte_service import JornadaTransporteService
from app.services.vehiculo_service import VehiculoService
from app.utils.vehiculo_report import estado_vigencia, generar_reporte_vehiculo


def _user(db, dni, email):
    item = User(nombre="Conductor", apellidos="V3", dni=dni, email=email, password="x", role="conductor")
    db.add(item)
    db.flush()
    return item


def _vehicle(db):
    item = Vehiculo(placa="V3-001", marca="RAMIS", modelo="Camioneta", tipo="Camioneta", capacidad_carga=1, kilometraje_actual=100)
    db.add(item)
    db.commit()
    return item


def _drive(vehicle_id):
    return RegistroAccionCreate(
        accion_tipo="Empezar a Conducir", vehiculo_id=vehicle_id, km_inicial=100,
        ruta="San Rafael", nivel_combustible=50, checklist_flash={"botiquin": False},
        observaciones="Botiquín pendiente de reposición",
    )


def test_relevo_libre_deja_primera_jornada_pendiente(db_session):
    primero = _user(db_session, "70000001", "v31@test.pe")
    segundo = _user(db_session, "70000002", "v32@test.pe")
    vehiculo = _vehicle(db_session)
    service = JornadaTransporteService(db_session)
    anterior = service.registrar_accion(primero.id, _drive(vehiculo.id))
    nueva = service.registrar_accion(segundo.id, _drive(vehiculo.id))
    db_session.refresh(anterior)
    assert anterior.estado == "pendiente_de_cierre"
    assert nueva.estado == "en_curso"
    assert vehiculo.estado == "en_ruta"


def test_checklist_no_conforme_no_bloquea_sin_severidad(db_session):
    conductor = _user(db_session, "70000003", "v33@test.pe")
    vehiculo = _vehicle(db_session)
    jornada = JornadaTransporteService(db_session).registrar_accion(conductor.id, _drive(vehiculo.id))
    assert jornada.estado == "en_curso"
    assert vehiculo.estado_semaforo == "verde"


def test_salto_mayor_600_exige_evidencia(db_session):
    conductor = _user(db_session, "70000004", "v34@test.pe")
    vehiculo = _vehicle(db_session)
    data = _drive(vehiculo.id).model_copy(update={"km_inicial": 701})
    with pytest.raises(HTTPException) as error:
        JornadaTransporteService(db_session).registrar_accion(conductor.id, data)
    assert error.value.status_code == 400


def test_baja_logica_genera_auditoria(db_session):
    usuario = _user(db_session, '70000006', 'v36@test.pe')
    vehiculo = _vehicle(db_session)
    VehiculoService(db_session).delete_vehiculo(vehiculo.id, usuario.id)
    assert vehiculo.estado == "inactivo"
    audit = db_session.query(AuditoriaSistema).one()
    assert audit.accion == "baja_logica"
    assert audit.valores_anteriores == {"estado": "disponible"}


def test_cierre_nocturno_marca_odometro_pendiente(db_session):
    conductor = _user(db_session, "70000005", "v35@test.pe")
    vehiculo = _vehicle(db_session)
    jornada = JornadaTransporteService(db_session).registrar_accion(conductor.id, _drive(vehiculo.id))
    jornada.fecha_inicio = datetime.utcnow() - timedelta(days=1)
    db_session.commit()
    assert JornadaTransporteService(db_session).cerrar_jornadas_vencidas() == 1
    assert jornada.estado == "cerrada_por_sistema"
    assert jornada.cerrado_por_sistema is True


def test_reporte_pdf_y_semaforo_documental(db_session):
    vehiculo = _vehicle(db_session)
    assert estado_vigencia(datetime.utcnow().date() + timedelta(days=20)) == "amarillo"
    pdf = generar_reporte_vehiculo(vehiculo, [], [])
    assert pdf.read(4) == b"%PDF"
