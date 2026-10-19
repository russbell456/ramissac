from app.models.user import User
from app.models.vehiculo import Vehiculo
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from app.schemas.jornada_transporte_schema import (
    ChecklistCreate,
    JornadaAsignacionCreate,
    JornadaResponse,
    JornadaDetalleResponse,
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



def _abrir(service, conductor, vehiculo):
    return service.registrar_accion(conductor.id, RegistroAccionCreate(
        km_inicial=100, accion_tipo="Empezar a Conducir", vehiculo_id=vehiculo.id,
        nivel_combustible=75, ruta="Juliaca", checklist_flash={"Documentos": True}, observaciones="Sin novedades"))

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
            foto_observacion="/uploads/transportes/abc.jpg",
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
            km_inicial=100,
            accion_tipo="Empezar a Conducir",
            nivel_combustible=50,
            ruta="Traslados en Juliaca",
            checklist_flash={"Documentos": True},
            observaciones="Sin novedad",
        )


def test_apertura_requiere_combustible():
    with pytest.raises(ValidationError, match="nivel_combustible"):
        RegistroAccionCreate(km_inicial=100, accion_tipo="Empezar a Conducir", vehiculo_id=1, observaciones="Sin novedades", ruta="Juliaca", checklist_flash={"Documentos":True})


def test_detalles_de_cada_flujo_son_obligatorios():
    for accion in (
        "Empezar a Conducir",
        "Operar Grúa",
        "Abastecer Combustible",
        "Mantenimiento Preventivo / Correctivo",
        "Check List y/o V°B° de vehículos",
        "Inspección Técnica",
        "Medición de Cocada",
        "Medición de Torque",
        "Trabajos a Externos",
    ):
        with pytest.raises(ValidationError):
            RegistroAccionCreate(
            km_inicial=100,
                accion_tipo=accion,
                vehiculo_id=1,
                nivel_combustible=50,
                observaciones="Sin novedad",
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
            km_inicial=100,
                accion_tipo=accion,
                vehiculo_id=1,
                nivel_combustible=50,
                **detalle,
            )


def test_limites_numericos_y_taller_libre():
    for galones in (0, 0.09, 100.01):
        with pytest.raises(ValidationError):
            RegistroAccionCreate(
            km_inicial=100,
                accion_tipo="Abastecer Combustible",
                vehiculo_id=1,
                nivel_combustible=50,
                observaciones="Sin novedad",
                detalles_combustible={"galones": galones, "nivel_final": 75},
            )
    with pytest.raises(ValidationError):
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Operar Grúa",
            vehiculo_id=1,
            nivel_combustible=50,
            observaciones="Sin novedad",
            detalles_grua={
                "actividad": "Izaje",
                "horometro_inicial": 0,
                "horometro_final": 1,
            },
        )
    accion = RegistroAccionCreate(
            km_inicial=100,
        accion_tipo="Mantenimiento Preventivo / Correctivo",
        vehiculo_id=1,
        nivel_combustible=50,
        observaciones="Sin novedad",
        detalles_mantenimiento={
            "taller": "Taller local",
            "tipo": "Preventivo",
            "trabajos_preventivos": ["Cambio de filtro"],
        },
    )
    assert accion.detalles_mantenimiento.taller == "Taller local"


def test_kilometraje_inicial_debe_ser_positivo(db_session):
    conductor, vehiculo = _crear_base(db_session)
    vehiculo.kilometraje_actual = 0
    db_session.commit()
    with pytest.raises(ValidationError):
        JornadaTransporteService(db_session).registrar_accion(
            conductor.id,
            RegistroAccionCreate(
            km_inicial=0,
                accion_tipo="Reporte de Incidencias u Observaciones",
                vehiculo_id=vehiculo.id,
                nivel_combustible=50,
                observaciones="Sin novedad",
            ),
        )


def test_registro_conduccion_conserva_vehiculo_hasta_checklist_final(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)

    jornada = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Empezar a Conducir",
            vehiculo_id=vehiculo.id,
            nivel_combustible=50,
            ruta="Traslados en Juliaca",
            checklist_flash={"Documentos": True},
            observaciones="Sin novedad",
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
    vehiculo.tipo = "Camión Grúa"
    _abrir(service, conductor, vehiculo)

    jornada = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Operar Grúa",
            vehiculo_id=vehiculo.id,
            nivel_combustible=75,
            observaciones="Sin novedad",
            detalles_grua={
                "actividad": "Izaje",
                "horometro_inicial": 10.5,
                "horometro_final": 11.5,
            },
        ),
    )
    assert jornada.estado == "finalizada"
    assert jornada.fecha_fin is not None
    assert jornada.km_inicial is None
    assert jornada.detalles_grua.actividad == "Izaje"
    assert jornada.detalles_grua.horometro_final == 11.5
    detalle = JornadaDetalleResponse.model_validate(jornada).model_dump(mode="json")
    assert detalle["detalles_grua"]["actividad"] == "Izaje"


def test_combustible_y_mantenimiento_guardan_sus_detalles(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)
    _abrir(service, conductor, vehiculo)

    combustible = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Abastecer Combustible",
            vehiculo_id=vehiculo.id,
            nivel_combustible=25,
            observaciones="Abastecido",
            detalles_combustible={"galones": 18.5, "nivel_final": 100},
        ),
    )
    mantenimiento = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Mantenimiento Preventivo / Correctivo",
            vehiculo_id=vehiculo.id,
            nivel_combustible=100,
            observaciones="Retirado del taller",
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
    detalle = JornadaDetalleResponse.model_validate(mantenimiento).model_dump(mode="json")
    assert detalle["detalles_mantenimiento"]["trabajos_preventivos"] == ["Lavado"]


def test_observaciones_y_checklist_son_obligatorios():
    with pytest.raises(ValidationError, match="observaciones"):
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Reporte de Incidencias u Observaciones",
            vehiculo_id=1,
            nivel_combustible=50,
            observaciones=" ",
        )
    with pytest.raises(ValidationError, match="Check List Flash"):
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Check List y/o V°B° de vehículos",
            vehiculo_id=1,
            nivel_combustible=50,
            observaciones="Revisado",
        )
    with pytest.raises(ValidationError, match="accion_tipo"):
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Acción desconocida",
            vehiculo_id=1,
            nivel_combustible=50,
            observaciones="Revisado",
        )


def test_incidencias_y_checklist_guardan_campos_existentes(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)
    _abrir(service, conductor, vehiculo)
    incidencia = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Reporte de Incidencias u Observaciones",
            vehiculo_id=vehiculo.id,
            nivel_combustible=25,
            observaciones="Ruido en el motor",
            tiene_observaciones=True, severidad="leve", foto_observacion="/uploads/transportes/abc.jpg",
        ),
    )
    checklist = service.registrar_accion(
        conductor.id,
        RegistroAccionCreate(
            km_inicial=100,
            accion_tipo="Check List y/o V°B° de vehículos",
            vehiculo_id=vehiculo.id,
            nivel_combustible=50,
            observaciones="Todo en orden",
            checklist_flash={"Botiquín": True},
        ),
    )
    assert incidencia.observaciones == "Ruido en el motor"
    assert checklist.checklist_flash == {"Botiquín": True}
    assert incidencia.estado == checklist.estado == "finalizada"


def test_cuatro_flujos_restantes_guardan_detalles(db_session):
    conductor, vehiculo = _crear_base(db_session)
    service = JornadaTransporteService(db_session)
    _abrir(service, conductor, vehiculo)
    casos = [
        ("Inspección Técnica", "detalles_inspeccion",
         {"fecha_inspeccion": "2026-10-08", "fecha_vencimiento": "2027-10-08"},
         "fecha_vencimiento", "2027-10-08"),
        ("Medición de Cocada", "detalles_cocada",
         {"medida": 7.5}, "medida", 7.5),
        ("Medición de Torque", "detalles_torque",
         {"medida": 120.25}, "medida", 120.25),
        ("Trabajos a Externos", "detalles_trabajos_externos",
         {"descripcion_trabajos": "Traslado de materiales"},
         "descripcion_trabajos", "Traslado de materiales"),
    ]
    for accion, campo, valores, llave, esperado in casos:
        jornada = service.registrar_accion(
            conductor.id,
            RegistroAccionCreate(
            km_inicial=100,
                accion_tipo=accion,
                vehiculo_id=vehiculo.id,
                nivel_combustible=50,
                observaciones="Sin novedad",
                **{campo: valores},
            ),
        )
        assert jornada.estado == "finalizada"
        detalle = JornadaDetalleResponse.model_validate(jornada).model_dump(mode="json")
        assert detalle[campo][llave] == esperado
