from app.models.user import User
from app.models.vehiculo import Vehiculo
import pytest
from pydantic import ValidationError

from app.schemas.jornada_transporte_schema import (
    ChecklistCreate,
    JornadaAsignacionCreate,
    JornadaResponse,
    RegistroAccionCreate,
)
from app.services.jornada_transporte_service import JornadaTransporteService


def _crear_base(db_session):
    conductor = User(
        nombre="Conductor",
        apellidos="Prueba",
        dni="99887766",
        cargo="Conductor",
        email="conductor-jornada@test.com",
        password="hash",
        role="conductor",
    )
    vehiculo = Vehiculo(
        placa="JRN001",
        marca="Volvo",
        modelo="FH",
        capacidad_carga=10,
        kilometraje_actual=100,
        estado="disponible",
    )
    db_session.add_all([conductor, vehiculo])
    db_session.commit()
    return conductor, vehiculo


def test_checklist_inicial_conforme_inicia_jornada(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)

    jornada = service.asignar(
        JornadaAsignacionCreate(vehiculo_id=vehiculo.id, conductor_id=conductor.id)
    )
    actualizada = service.registrar_checklist_inicial(
        jornada.id,
        ChecklistCreate(
            kilometraje=120,
            nivel_combustible="3/4",
            estado_general="Bueno",
            conforme=True,
        ),
        conductor.id,
    )

    assert actualizada.estado == "en_curso"
    assert actualizada.vehiculo.estado == "en_ruta"
    assert actualizada.vehiculo.kilometraje_actual == 120


def test_checklist_inicial_no_conforme_cancela_y_genera_averia(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)
    jornada = service.asignar(
        JornadaAsignacionCreate(vehiculo_id=vehiculo.id, conductor_id=conductor.id)
    )

    actualizada = service.registrar_checklist_inicial(
        jornada.id,
        ChecklistCreate(
            kilometraje=105,
            nivel_combustible="1/2",
            estado_general="Falla en frenos",
            conforme=False,
            observaciones="Revisar sistema de frenos",
        ),
        conductor.id,
    )

    assert actualizada.estado == "cancelada_por_averia"
    assert actualizada.vehiculo.estado == "en_mantenimiento"
    assert len(vehiculo.averias) == 1


def test_conducir_requiere_vehiculo():
    with pytest.raises(ValidationError, match="Seleccione un vehículo"):
        RegistroAccionCreate(accion_tipo="Empezar a Conducir")


def test_registro_conduccion_conserva_vehiculo_hasta_checklist_final(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)

    jornada = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            accion_tipo="Empezar a Conducir",
            vehiculo_id=vehiculo.id,
        ),
    )
    respuesta = JornadaResponse.model_validate(jornada).model_dump(mode="json")
    assert respuesta["vehiculo_id"] == vehiculo.id
    assert service.obtener(jornada.id).vehiculo_id == vehiculo.id

    finalizada = service.registrar_checklist_final(
        jornada.id,
        ChecklistCreate(
            tipo="final",
            kilometraje=120,
            nivel_combustible="3/4",
            estado_general="Bueno",
            conforme=True,
        ),
        conductor.id,
    )
    assert finalizada.estado == "finalizada"
    assert finalizada.vehiculo_id == vehiculo.id
