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


def test_registrar_prestamo_forbidden(client):

    user_email = f"user_{uuid.uuid4()}@test.com"

    register_res = client.post(
        "/auth/register",
        json={
            "nombre": "User",
            "apellidos": "Test",
            "dni": str(uuid.uuid4().int)[:8],
            "cargo": "Operario",
            "email": user_email,
            "password": "12345678",
            "role": "trabajador"
        }
    )

    assert register_res.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": user_email,
            "password": "12345678"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = client.post(
        "/almacen/registrar-prestamo-qr",
        headers=headers,
        json={
            "trabajador_id": 1,
            "codigo_unico": f"PREST-{uuid.uuid4()}",
            "dni": "12345678",
            "nombres_completos": "User Test",
            "cargo": "Operario",
            "fecha_prestamo": datetime.now().isoformat(),
            "fecha_devolucion_prevista": (
                datetime.now() + timedelta(days=3)
            ).isoformat(),
            "items": [],
            "firma_base64":
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )

    assert response.status_code == 403


def test_descargar_pdf_success(client):

    prestamo_id = 9999
    pdf_dir = "static/prestamos"

    os.makedirs(pdf_dir, exist_ok=True)

    pdf_path = f"{pdf_dir}/prestamo_{prestamo_id}.pdf"

    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 mock pdf content")

    try:

        response = client.get(
            f"/almacen/prestamo/{prestamo_id}/pdf"
        )

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/pdf"
        )

    finally:

        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_descargar_pdf_not_found(client):

    response = client.get(
        "/almacen/prestamo/888888/pdf"
    )

    assert response.status_code == 404


def test_obtener_prestamos_trabajador(
    client,
    db_session
):

    trabajador_1 = User(
        nombre="Trabajador Uno",
        apellidos="Test",
        dni=str(uuid.uuid4().int)[:8],
        cargo="Operario",
        email=f"t1_{uuid.uuid4()}@test.com",
        password=hash_password("12345678")
    )
    trabajador_1.role = "trabajador"

    trabajador_2 = User(
        nombre="Trabajador Dos",
        apellidos="Test",
        dni=str(uuid.uuid4().int)[:8],
        cargo="Operario",
        email=f"t2_{uuid.uuid4()}@test.com",
        password=hash_password("12345678")
    )
    trabajador_2.role = "trabajador"

    db_session.add_all([
        trabajador_1,
        trabajador_2
    ])
    db_session.commit()

    login_t1 = client.post(
        "/auth/login",
        json={
            "email": trabajador_1.email,
            "password": "12345678"
        }
    )

    token_t1 = login_t1.json()["access_token"]

    headers_t1 = {
        "Authorization": f"Bearer {token_t1}"
    }

    res_self = client.get(
        f"/almacen/trabajador/{trabajador_1.id}/prestamos",
        headers=headers_t1
    )

    assert res_self.status_code == 200

    res_other = client.get(
        f"/almacen/trabajador/{trabajador_2.id}/prestamos",
        headers=headers_t1
    )

    assert res_other.status_code == 403

    admin_email = f"admin_{uuid.uuid4()}@test.com"

    client.post(
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

    login_admin = client.post(
        "/auth/login",
        json={
            "email": admin_email,
            "password": "12345678"
        }
    )

    token_admin = login_admin.json()["access_token"]

    headers_admin = {
        "Authorization": f"Bearer {token_admin}"
    }

    res_admin = client.get(
        f"/almacen/trabajador/{trabajador_2.id}/prestamos",
        headers=headers_admin
    )

    assert res_admin.status_code == 200


def test_obtener_prestamos_articulo(
    client,
    db_session
):

    articulo = AlmacenArticulo(
        nombre="Articulo Prestamo Test",
        unidad_medida="UND",
        tipo=TipoArticulo.CONSUMIBLE,
        stock_actual=10,
        codigo_excel=f"COD-{uuid.uuid4()}"
    )

    db_session.add(articulo)
    db_session.commit()
    db_session.refresh(articulo)

    user_email = f"user_{uuid.uuid4()}@test.com"

    client.post(
        "/auth/register",
        json={
            "nombre": "User",
            "apellidos": "Test",
            "dni": str(uuid.uuid4().int)[:8],
            "cargo": "Operario",
            "email": user_email,
            "password": "12345678",
            "role": "trabajador"
        }
    )

    login_user = client.post(
        "/auth/login",
        json={
            "email": user_email,
            "password": "12345678"
        }
    )

    token_user = login_user.json()["access_token"]

    headers_user = {
        "Authorization": f"Bearer {token_user}"
    }

    res_forbidden = client.get(
        f"/almacen/articulo/{articulo.id}/prestamos",
        headers=headers_user
    )

    assert res_forbidden.status_code == 403

    admin_email = f"admin_{uuid.uuid4()}@test.com"

    client.post(
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

    login_admin = client.post(
        "/auth/login",
        json={
            "email": admin_email,
            "password": "12345678"
        }
    )

    token_admin = login_admin.json()["access_token"]

    headers_admin = {
        "Authorization": f"Bearer {token_admin}"
    }

    res_success = client.get(
        f"/almacen/articulo/{articulo.id}/prestamos",
        headers=headers_admin
    )

    assert res_success.status_code == 200