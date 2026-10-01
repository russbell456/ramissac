"""Tests de integración del módulo de transportes avanzado.

Cubre: inspecciones (SALIDA/POST_MANTENIMIENTO), regla crítica de salida,
ciclo de vida del vehículo, mantenimiento preventivo/correctivo, averías,
incidentes y kilometraje monotónico.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def override_auth(db_session):
    user = User(
        nombre="Admin",
        apellidos="Principal",
        dni="12345678",
        cargo="Almacenero",
        email="admin@test-avanzado.com",
        password="hashed_password",
        role="almacenero",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


def _unique_dni() -> str:
    return str(uuid.uuid4().int)[:8]


def _crear_vehiculo(client, placa=None, km=0.0):
    placa = placa or f"V{uuid.uuid4().hex[:6].upper()}"
    resp = client.post(
        "/api/vehiculos/",
        json={
            "placa": placa,
            "marca": "Volvo",
            "modelo": "FH16",
            "capacidad_carga": 20.5,
            "kilometraje_actual": km,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _registrar_trabajador(client):
    resp = client.post(
        "/auth/register",
        json={
            "nombre": "Chofer",
            "apellidos": "Prueba",
            "dni": _unique_dni(),
            "cargo": "Conductor",
            "email": f"trab_{uuid.uuid4()}@test.com",
            "password": "12345678",
            "role": "trabajador",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _crear_ruta(client, vehiculo_id, trabajador_id):
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)
    resp = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo_id,
            "trabajador_id": trabajador_id,
            "origen": "Juliaca",
            "destino": "Puno",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _crear_checklist_item(client, codigo=None, criticidad="media"):
    codigo = codigo or f"IT-{uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/inspecciones/checklist-items",
        json={"codigo": codigo, "nombre": "Item de prueba", "criticidad": criticidad},
    )
    assert resp.status_code == 201
    return resp.json()


def _crear_salida(client, vehiculo_id, ruta_id, resultado="APROBADA", criticidad="media"):
    item = _crear_checklist_item(client, criticidad=criticidad)
    resp = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo_id,
            "ruta_id": ruta_id,
            "tipo": "SALIDA",
            "detalles": [
                {"item_id": item["id"], "resultado": "conforme", "comentario": "OK"}
            ],
        },
    )
    assert resp.status_code == 201
    inspeccion_id = resp.json()["id"]
    resuelta = client.patch(
        f"/api/inspecciones/{inspeccion_id}/resolver",
        json={"resultado": resultado, "observaciones": "test"},
    )
    assert resuelta.status_code == 200
    return resuelta.json()


_FIRMA_TEST = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def _iniciar(client, ruta_id, trabajador_id, db_session, km=15000.0):
    trabajador_user = db_session.query(User).filter(User.id == trabajador_id).first()
    app.dependency_overrides[get_current_user] = lambda: trabajador_user
    return client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": _FIRMA_TEST,
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": km,
            "combustible_salida": "3/4",
        },
    )


def _finalizar(client, ruta_id, km=180.0, obs="Llegada ok"):
    return client.patch(
        f"/api/rutas/{ruta_id}/finalizar",
        json={
            "kilometraje_llegada": km,
            "combustible_llegada": "1/2",
            "observaciones_llegada": obs,
        },
    )


def test_trabajador_puede_reportar_operacion(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    item = _crear_checklist_item(client)

    trabajador_user = db_session.query(User).filter(User.id == trabajador["id"]).first()
    app.dependency_overrides[get_current_user] = lambda: trabajador_user

    inspeccion = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "SALIDA",
            "detalles": [{"item_id": item["id"], "resultado": "conforme"}],
        },
    )
    assert inspeccion.status_code == 201

    incidente = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "novedad",
            "descripcion": "Reporte operativo del conductor",
        },
    )
    assert incidente.status_code == 201

    averia = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "descripcion": "Falla reportada en ruta",
            "criticidad": "media",
        },
    )
    assert averia.status_code == 201



# ----------------------------------------------------------------------
# Inspecciones: regla crítica de SALIDA
# ----------------------------------------------------------------------
def test_salida_aprobada_permite_iniciar_ruta(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="APROBADA")

    resp = _iniciar(client, ruta["id"], trabajador["id"], db_session)
    assert resp.status_code == 200
    assert resp.json()["estado_ruta"] == "en_progreso"


def test_salida_aprobada_con_observaciones_permite_iniciar(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="APROBADA_CON_OBSERVACIONES")

    resp = _iniciar(client, ruta["id"], trabajador["id"], db_session)
    assert resp.status_code == 200
    assert resp.json()["estado_ruta"] == "en_progreso"


def test_salida_rechazada_impide_iniciar_ruta(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="RECHAZADA")

    resp = _iniciar(client, ruta["id"], trabajador["id"], db_session)
    assert resp.status_code == 400
    assert "rechazada" in resp.json()["detail"].lower()


def test_no_se_puede_iniciar_sin_inspeccion_salida(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    resp = _iniciar(client, ruta["id"], trabajador["id"], db_session)
    assert resp.status_code == 400
    assert "salida" in resp.json()["detail"].lower()


def test_item_critico_no_conforme_produce_rechazo(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    item = _crear_checklist_item(client, criticidad="critica")
    inspeccion = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "ruta_id": ruta["id"],
            "tipo": "SALIDA",
            "detalles": [
                {"item_id": item["id"], "resultado": "no_conforme", "comentario": "falla"}
            ],
        },
    )
    assert inspeccion.status_code == 201
    inspeccion_id = inspeccion.json()["id"]

    res = client.patch(
        f"/api/inspecciones/{inspeccion_id}/resolver",
        json={"resultado": "APROBADA"},
    )
    assert res.status_code == 400

    res2 = client.patch(
        f"/api/inspecciones/{inspeccion_id}/resolver",
        json={"resultado": "RECHAZADA"},
    )
    assert res2.status_code == 200

    resp = _iniciar(client, ruta["id"], trabajador["id"], db_session)
    assert resp.status_code == 400


def test_trabajador_no_asignado_no_puede_iniciar(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    otro = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="APROBADA")

    otro_user = db_session.query(User).filter(User.id == otro["id"]).first()
    app.dependency_overrides[get_current_user] = lambda: otro_user
    resp = client.patch(
        f"/api/rutas/{ruta['id']}/iniciar",
        json={
            "firma_trabajador": _FIRMA_TEST,
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 100.0,
            "combustible_salida": "lleno",
        },
    )
    assert resp.status_code == 403



def test_finalizacion_ruta_normal(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])
    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="APROBADA")
    _iniciar(client, ruta["id"], trabajador["id"], db_session, km=100.0)

    app.dependency_overrides[get_current_user] = lambda: override_auth
    fin = _finalizar(client, ruta["id"], km=180.0, obs="Llegada ok")
    assert fin.status_code == 200
    assert fin.json()["estado_ruta"] == "completada"

    vehiculo_libre = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_libre.json()["estado"] == "disponible"


def test_finalizacion_ruta_con_falla_envia_a_mantenimiento(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])
    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="APROBADA")
    _iniciar(client, ruta["id"], trabajador["id"], db_session, km=100.0)

    app.dependency_overrides[get_current_user] = lambda: override_auth
    fin = _finalizar(client, ruta["id"], km=180.0, obs="Problema grave con los frenos")
    assert fin.status_code == 200

    vehiculo_manto = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_manto.json()["estado"] == "en_mantenimiento"


# ----------------------------------------------------------------------
# Mantenimiento: ciclo de vida en_mantenimiento -> observado -> disponible
# ----------------------------------------------------------------------
def test_mantenimiento_no_libera_directamente_a_disponible(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)

    manto = client.post(
        "/api/mantenimientos/",
        json={
            "vehiculo_id": vehiculo["id"],
            "fecha_ingreso": datetime.utcnow().isoformat(),
            "descripcion_falla": "Freno trasero",
            "costo": 350.0,
            "tipo": "CORRECTIVO",
        },
    )
    assert manto.status_code == 201
    manto_id = manto.json()["id"]
    assert manto.json()["estado"] == "en_taller"

    completado = client.put(
        f"/api/mantenimientos/{manto_id}",
        json={"estado": "completado"},
    )
    assert completado.status_code == 200

    vehiculo_obs = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_obs.json()["estado"] == "observado"
    assert vehiculo_obs.json()["estado"] != "disponible"


def test_post_mantenimiento_aprobada_libera_vehiculo(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)

    manto = client.post(
        "/api/mantenimientos/",
        json={
            "vehiculo_id": vehiculo["id"],
            "fecha_ingreso": datetime.utcnow().isoformat(),
            "descripcion_falla": "Filtro",
            "costo": 100.0,
            "tipo": "PREVENTIVO",
        },
    )
    manto_id = manto.json()["id"]
    client.put(f"/api/mantenimientos/{manto_id}", json={"estado": "completado"})

    obs = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert obs.json()["estado"] == "observado"

    item = _crear_checklist_item(client, criticidad="media")
    insp = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "POST_MANTENIMIENTO",
            "detalles": [
                {"item_id": item["id"], "resultado": "conforme", "comentario": "OK"}
            ],
        },
    )
    assert insp.status_code == 201
    insp_id = insp.json()["id"]
    res = client.patch(
        f"/api/inspecciones/{insp_id}/resolver",
        json={"resultado": "APROBADA"},
    )
    assert res.status_code == 200

    liberado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert liberado.json()["estado"] == "disponible"


def test_post_mantenimiento_rechazada_mantiene_observado(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)

    manto = client.post(
        "/api/mantenimientos/",
        json={
            "vehiculo_id": vehiculo["id"],
            "fecha_ingreso": datetime.utcnow().isoformat(),
            "descripcion_falla": "Aceite",
            "costo": 50.0,
            "tipo": "PREVENTIVO",
        },
    )
    manto_id = manto.json()["id"]
    client.put(f"/api/mantenimientos/{manto_id}", json={"estado": "completado"})

    item = _crear_checklist_item(client, criticidad="media")
    insp = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "POST_MANTENIMIENTO",
            "detalles": [
                {"item_id": item["id"], "resultado": "no_conforme", "comentario": "falla"}
            ],
        },
    )
    insp_id = insp.json()["id"]
    res = client.patch(
        f"/api/inspecciones/{insp_id}/resolver",
        json={"resultado": "RECHAZADA"},
    )
    assert res.status_code == 200

    sigue_obs = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert sigue_obs.json()["estado"] == "observado"



# ----------------------------------------------------------------------
# Averías
# ----------------------------------------------------------------------
def test_averia_ciclo_completo(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)

    averia = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "descripcion": "Falla en el motor",
            "criticidad": "media",
        },
    )
    assert averia.status_code == 201
    averia_id = averia.json()["id"]
    assert averia.json()["estado"] == "reportada"

    up = client.put(f"/api/averias/{averia_id}", json={"estado": "en_evaluacion"})
    assert up.status_code == 200
    assert up.json()["estado"] == "en_evaluacion"

    res = client.patch(f"/api/averias/{averia_id}/resolver")
    assert res.status_code == 200
    assert res.json()["estado"] == "resuelta"

    cer = client.patch(f"/api/averias/{averia_id}/cerrar")
    assert cer.status_code == 200
    assert cer.json()["estado"] == "cerrada"


def test_averia_critica_bloquea_vehiculo(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "descripcion": "Falla critica",
            "criticidad": "critica",
        },
    )
    v = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert v.json()["estado"] == "bloqueado"


def test_varias_averias_criticas_resolver_una_no_libera(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)

    a1 = client.post(
        "/api/averias/",
        json={"vehiculo_id": vehiculo["id"], "descripcion": "C1", "criticidad": "critica"},
    ).json()
    a2 = client.post(
        "/api/averias/",
        json={"vehiculo_id": vehiculo["id"], "descripcion": "C2", "criticidad": "critica"},
    ).json()

    v = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert v.json()["estado"] == "bloqueado"

    client.patch(f"/api/averias/{a1['id']}/resolver")
    v2 = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert v2.json()["estado"] == "bloqueado"

    client.patch(f"/api/averias/{a2['id']}/resolver")
    v3 = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert v3.json()["estado"] == "observado"


# ----------------------------------------------------------------------
# Incidentes
# ----------------------------------------------------------------------
def test_incidente_creacion_y_asociacion(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    resp = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "incidente",
            "descripcion": "Novedad de operacion",
            "afecta_personas": False,
            "dano_vehiculo": False,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["tipo"] == "incidente"


def test_incidente_con_afectacion_personas_genera_averia_critica(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    resp = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "accidente",
            "descripcion": "Accidente con personas afectadas",
            "afecta_personas": True,
            "dano_vehiculo": True,
        },
    )
    assert resp.status_code == 201
    incidente_id = resp.json()["id"]

    averias = client.get(f"/api/averias/vehiculo/{vehiculo['id']}")
    assert averias.status_code == 200
    assert len(averias.json()) == 1
    averia = averias.json()[0]
    assert averia["criticidad"] == "critica"
    assert averia["origen_incidente_id"] == incidente_id

    v = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert v.json()["estado"] == "bloqueado"


def test_incidente_con_dano_vehiculo_genera_averia(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    resp = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "tipo": "novedad",
            "descripcion": "Dano material leve",
            "afecta_personas": False,
            "dano_vehiculo": True,
        },
    )
    assert resp.status_code == 201
    averias = client.get(f"/api/averias/vehiculo/{vehiculo['id']}")
    assert len(averias.json()) == 1


# ----------------------------------------------------------------------
# Kilometraje monotónico
# ----------------------------------------------------------------------
def test_kilometraje_no_puede_disminuir_al_actualizar(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client, km=5000.0)
    resp = client.put(
        f"/api/vehiculos/{vehiculo['id']}",
        json={"kilometraje_actual": 4000.0},
    )
    assert resp.status_code == 400
    assert "kilometraje" in resp.json()["detail"].lower()


def test_kilometraje_salida_no_menor_que_actual(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client, km=20000.0)
    trabajador = _registrar_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])
    _crear_salida(client, vehiculo["id"], ruta["id"], resultado="APROBADA")

    resp = _iniciar(client, ruta["id"], trabajador["id"], db_session, km=15000.0)
    assert resp.status_code == 400
    assert "kilometraje" in resp.json()["detail"].lower()



# ----------------------------------------------------------------------
# Planes de mantenimiento preventivo
# ----------------------------------------------------------------------
def test_plan_preventivo_control_por_kilometraje(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    resp = client.post(
        "/api/planes-mantenimiento/",
        json={
            "vehiculo_id": vehiculo["id"],
            "nombre": "Cambio de aceite por KM",
            "tipo_control": "kilometraje",
            "intervalo_kilometraje": 10000.0,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["tipo_control"] == "kilometraje"


def test_plan_preventivo_control_por_fecha(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    resp = client.post(
        "/api/planes-mantenimiento/",
        json={
            "vehiculo_id": vehiculo["id"],
            "nombre": "Inspeccion semestral",
            "tipo_control": "fecha",
            "intervalo_dias": 180,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["intervalo_dias"] == 180


def test_plan_preventivo_control_por_horas(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    resp = client.post(
        "/api/planes-mantenimiento/",
        json={
            "vehiculo_id": vehiculo["id"],
            "nombre": "Servicio por horas",
            "tipo_control": "horas",
            "intervalo_horas": 500.0,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["intervalo_horas"] == 500.0


def test_plan_preventivo_control_mixto_requiere_dos_umbrales(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    bad = client.post(
        "/api/planes-mantenimiento/",
        json={
            "vehiculo_id": vehiculo["id"],
            "nombre": "Mixto incompleto",
            "tipo_control": "mixto",
            "intervalo_kilometraje": 10000.0,
        },
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/planes-mantenimiento/",
        json={
            "vehiculo_id": vehiculo["id"],
            "nombre": "Mixto completo",
            "tipo_control": "mixto",
            "intervalo_kilometraje": 10000.0,
            "intervalo_dias": 90,
        },
    )
    assert ok.status_code == 201


def test_evaluar_control_mixto_primera_condicion(client):
    from app.services.mantenimiento_plan_service import PlanMantenimientoService

    service = PlanMantenimientoService.__new__(PlanMantenimientoService)

    class PlanFake:
        intervalo_kilometraje = 10000.0
        intervalo_dias = 90
        intervalo_horas = None

    estado = service.evaluar_control(
        PlanFake(),
        vehiculo_kilometraje=9500.0,
        ultima_ejecucion=datetime.utcnow() - timedelta(days=95),
        horas_operacion=0.0,
    )
    assert estado == "VENCIDO"

    estado2 = service.evaluar_control(
        PlanFake(),
        vehiculo_kilometraje=5000.0,
        ultima_ejecucion=datetime.utcnow() - timedelta(days=10),
        horas_operacion=0.0,
    )
    assert estado2 == "NORMAL"

