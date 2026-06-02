import os
import uuid

from datetime import datetime, timedelta

from app.models.user import User
from app.models.almacen_articulos import (
    AlmacenArticulo,
    TipoArticulo
)

from app.core.security import hash_password


def test_registrar_prestamo_success(
    client,
    db_session
):

    # =========================
    # ASEGURAR CARPETA PDF
    # =========================

    os.makedirs("static/prestamos", exist_ok=True)

    # =========================
    # CREAR ADMIN TEMPORAL
    # =========================

    admin_email = f"admin_{uuid.uuid4()}@test.com"

    register_admin = client.post(
        "/auth/register",
        json={
            "nombre": "Admin",
            "apellidos": "Test",
            "dni": str(uuid.uuid4().int)[:8],
            "cargo": "Administrador",
            "email": admin_email,
            "password": "12345678",
            "role": "admin"
        }
    )

    assert register_admin.status_code == 201

    # =========================
    # LOGIN ADMIN
    # =========================

    login_response = client.post(
        "/auth/login",
        json={
            "email": admin_email,
            "password": "12345678"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # =========================
    # CREAR TRABAJADOR
    # =========================

    trabajador = User(
        nombre="Trabajador",
        apellidos="Test",
        dni=str(uuid.uuid4().int)[:8],
        cargo="Operario",
        email=f"trabajador_{uuid.uuid4()}@test.com",
        password=hash_password("12345678")
    )

    trabajador.role = "trabajador"

    db_session.add(trabajador)
    db_session.commit()
    db_session.refresh(trabajador)

    # =========================
    # CREAR ARTICULO
    # =========================

    articulo = AlmacenArticulo(
        nombre="Taladro Test",
        unidad_medida="UND",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=10,
        codigo_excel=f"COD-{uuid.uuid4()}"
    )

    db_session.add(articulo)
    db_session.commit()
    db_session.refresh(articulo)

    # =========================
    # REGISTRAR PRESTAMO
    # =========================

    response = client.post(
        "/almacen/registrar-prestamo-qr",
        headers=headers,
        json={
            "trabajador_id": trabajador.id,
            "codigo_unico": f"PREST-{uuid.uuid4()}",
            "dni": trabajador.dni,
            "nombres_completos": (
                f"{trabajador.nombre} "
                f"{trabajador.apellidos}"
            ),
            "cargo": trabajador.cargo,
            "fecha_prestamo": datetime.now().isoformat(),
            "fecha_devolucion_prevista": (
                datetime.now() + timedelta(days=3)
            ).isoformat(),
            "items": [
                {
                    "articulo_id": articulo.id,
                    "cantidad": 2
                }
            ],
            "firma_base64":
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )

    print(response.status_code)
    print(response.text)

    assert response.status_code == 200

    data = response.json()

    assert data["estado"] == "abierto"
    assert "codigo_unico" in data


def test_registrar_prestamo_sin_token(client):

    response = client.post(
        "/almacen/registrar-prestamo-qr",
        json={}
    )

    assert response.status_code == 401


def test_registrar_prestamo_stock_insuficiente(
    client,
    db_session
):

    # =========================
    # CREAR ADMIN
    # =========================

    admin_email = f"admin_{uuid.uuid4()}@test.com"

    register_admin = client.post(
        "/auth/register",
        json={
            "nombre": "Admin",
            "apellidos": "Test",
            "dni": str(uuid.uuid4().int)[:8],
            "cargo": "Administrador",
            "email": admin_email,
            "password": "12345678",
            "role": "admin"
        }
    )

    assert register_admin.status_code == 201

    # =========================
    # LOGIN
    # =========================

    login_response = client.post(
        "/auth/login",
        json={
            "email": admin_email,
            "password": "12345678"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # =========================
    # CREAR TRABAJADOR
    # =========================

    trabajador = User(
        nombre="Trabajador",
        apellidos="Test",
        dni=str(uuid.uuid4().int)[:8],
        cargo="Operario",
        email=f"trabajador_{uuid.uuid4()}@test.com",
        password=hash_password("12345678")
    )

    trabajador.role = "trabajador"

    db_session.add(trabajador)
    db_session.commit()
    db_session.refresh(trabajador)

    # =========================
    # CREAR ARTICULO
    # =========================

    articulo = AlmacenArticulo(
        nombre="Amoladora Test",
        unidad_medida="UND",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=1,
        codigo_excel=f"COD-{uuid.uuid4()}"
    )

    db_session.add(articulo)
    db_session.commit()
    db_session.refresh(articulo)

    # =========================
    # REQUEST
    # =========================

    response = client.post(
        "/almacen/registrar-prestamo-qr",
        headers=headers,
        json={
            "trabajador_id": trabajador.id,
            "codigo_unico": f"PREST-{uuid.uuid4()}",
            "dni": trabajador.dni,
            "nombres_completos": (
                f"{trabajador.nombre} "
                f"{trabajador.apellidos}"
            ),
            "cargo": trabajador.cargo,
            "fecha_prestamo": datetime.now().isoformat(),
            "fecha_devolucion_prevista": (
                datetime.now() + timedelta(days=2)
            ).isoformat(),
            "items": [
                {
                    "articulo_id": articulo.id,
                    "cantidad": 5
                }
            ],
            "firma_base64":
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )

    assert response.status_code == 400
    assert "stock" in response.text.lower()