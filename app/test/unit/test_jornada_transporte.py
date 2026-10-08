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
    with pytest.raises(ValidationError, match="vehiculo_id"):
        RegistroAccionCreate(
            accion_tipo="Empezar a Conducir",
            nivel_combustible=50,
            ruta="Traslados en Juliaca",
            checklist_flash={"Documentos": True},
        )


def test_todas_las_acciones_requieren_combustible():
    with pytest.raises(ValidationError, match="nivel_combustible"):
        RegistroAccionCreate(
            accion_tipo="Reporte de Incidencias u Observaciones",
            vehiculo_id=1,
        )


def test_detalles_de_cada_flujo_son_obligatorios():
    for accion in (
        "Empezar a Conducir",
        "Operar Grúa",
        "Abastecer Combustible",
        "Mantenimiento Preventivo / Correctivo",
    ):
        with pytest.raises(ValidationError):
            RegistroAccionCreate(
                accion_tipo=accion,
                vehiculo_id=1,
                nivel_combustible=50,
            )


def test_validaciones_condicionales_de_grua_combustible_y_mantenimiento():
    casos = [
        ("Operar Grúa", {"detalles_grua": {
            "actividad": "Izaje", "horometro_inicial": 12, "horometro_final": 10,
        }}),
        ("Abastecer Combustible", {"detalles_combustible": {
            "galones": 10, "nivel_final": 30,
        }}),
        ("Mantenimiento Preventivo / Correctivo", {"detalles_mantenimiento": {
            "taller": "CONAUTO", "tipo": "Correctivo",
            "descripcion_correctivo": " ",
        }}),
    ]
    for accion, detalle in casos:
        with pytest.raises(ValidationError):
            RegistroAccionCreate(
                accion_tipo=accion,
                vehiculo_id=1,
                nivel_combustible=50,
                **detalle,
            )


def test_registro_conduccion_conserva_vehiculo_hasta_checklist_final(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)

    jornada = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            accion_tipo="Empezar a Conducir",
            vehiculo_id=vehiculo.id,
            nivel_combustible=50,
            ruta="Traslados en Juliaca",
            checklist_flash={"Documentos": True},
        ),
    )
    respuesta = JornadaResponse.model_validate(jornada).model_dump(mode="json")
    assert respuesta["vehiculo_id"] == vehiculo.id
    assert respuesta["km_inicial"] == 100
    assert respuesta["conductor_id"] == conductor.id
    assert respuesta["fecha_inicio"] is not None
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


def test_accion_de_grua_se_cierra_con_detalle_y_vehiculo(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)

    jornada = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            accion_tipo="Operar Grúa",
            vehiculo_id=vehiculo.id,
            nivel_combustible=75,
            detalles_grua={
                "actividad": "Izaje",
                "horometro_inicial": 10.5,
                "horometro_final": 11.5,
            },
        ),
    )
    assert jornada.estado == "finalizada"
    assert jornada.fecha_fin is not None
    assert jornada.km_inicial == 100
    assert jornada.detalles_grua.actividad == "Izaje"
    assert jornada.detalles_grua.horometro_final == 11.5


def test_combustible_y_mantenimiento_guardan_sus_detalles(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)

    combustible = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            accion_tipo="Abastecer Combustible",
            vehiculo_id=vehiculo.id,
            nivel_combustible=25,
            detalles_combustible={"galones": 18.5, "nivel_final": 100},
        ),
    )
    mantenimiento = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            accion_tipo="Mantenimiento Preventivo / Correctivo",
            vehiculo_id=vehiculo.id,
            nivel_combustible=100,
            detalles_mantenimiento={
                "taller": "MALVEX",
                "tipo": "Preventivo",
                "trabajos_preventivos": ["Lavado"],
            },
        ),
    )
    assert combustible.estado == mantenimiento.estado == "finalizada"
    assert combustible.detalles_combustible.galones == 18.5
    assert combustible.detalles_combustible.nivel_final == 100
    assert mantenimiento.detalles_mantenimiento.taller == "MALVEX"
    assert mantenimiento.detalles_mantenimiento.trabajos_preventivos == ["Lavado"]
