import os
import uuid
from datetime import datetime, timedelta
from app.models.user import User
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_prestamo import AlmacenPrestamoDetalle
from app.core.security import hash_password


def test_registrar_devolucion_qr_success(client, db_session):
    # 1. Asegurar carpeta pdf
    os.makedirs("static/prestamos", exist_ok=True)

    # 2. Registrar/Login Admin
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
    login_response = client.post(
        "/auth/login",
        json={
            "email": admin_email,
            "password": "12345678"
        }
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Crear Trabajador
    trabajador = User(
        nombre="Trabajador Dev",
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

    # 4. Crear Artículo
    articulo = AlmacenArticulo(
        nombre="Martillo Dev Test",
        unidad_medida="UND",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=10,
        codigo_excel=f"COD-{uuid.uuid4()}"
    )
    db_session.add(articulo)
    db_session.commit()
    db_session.refresh(articulo)

    # 5. Registrar Préstamo
    prestamo_response = client.post(
        "/almacen/registrar-prestamo-qr",
        headers=headers,
        json={
            "trabajador_id": trabajador.id,
            "codigo_unico": f"PREST-{uuid.uuid4()}",
            "dni": trabajador.dni,
            "nombres_completos": f"{trabajador.nombre} {trabajador.apellidos}",
            "cargo": trabajador.cargo,
            "fecha_prestamo": datetime.now().isoformat(),
            "fecha_devolucion_prevista": (datetime.now() + timedelta(days=3)).isoformat(),
            "items": [
                {
                    "articulo_id": articulo.id,
                    "cantidad": 3
                }
            ],
            "firma_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )
    assert prestamo_response.status_code == 200
    prestamo_id = prestamo_response.json()["id"]

    # 6. Consultar detalle del préstamo en DB para obtener su ID
    detalle = db_session.query(AlmacenPrestamoDetalle).filter_by(prestamo_id=prestamo_id).first()
    assert detalle is not None

    # 7. Registrar Devolución (Éxito)
    response = client.post(
        "/almacen/registrar-devolucion-qr",
        headers=headers,
        json={
            "trabajador_id": trabajador.id,
            "codigo_unico": f"DEV-{uuid.uuid4()}",
            "dni": trabajador.dni,
            "nombres_completos": f"{trabajador.nombre} {trabajador.apellidos}",
            "cargo": trabajador.cargo,
            "fecha_devolucion": datetime.now().isoformat(),
            "prestamo_id": prestamo_id,
            "items": [
                {
                    "prestamo_detalle_id": detalle.id,
                    "cantidad": 3
                }
            ],
            "firma_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "codigo_unico" in data
    assert "estado" in data


def test_registrar_devolucion_qr_forbidden(client):
    # 1. Registrar/Login Usuario normal (trabajador)
    user_email = f"user_{uuid.uuid4()}@test.com"
    client.post(
        "/auth/register",
        json={
            "nombre": "Trabajador",
            "apellidos": "Normal",
            "dni": str(uuid.uuid4().int)[:8],
            "cargo": "Operario",
            "email": user_email,
            "password": "12345678",
            "role": "trabajador"
        }
    )
    login_response = client.post(
        "/auth/login",
        json={
            "email": user_email,
            "password": "12345678"
        }
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Registrar Devolución (Debe fallar con 403 Forbidden)
    response = client.post(
        "/almacen/registrar-devolucion-qr",
        headers=headers,
        json={
            "trabajador_id": 1,
            "codigo_unico": f"DEV-{uuid.uuid4()}",
            "dni": "12345678",
            "nombres_completos": "Trabajador Normal",
            "cargo": "Operario",
            "fecha_devolucion": datetime.now().isoformat(),
            "prestamo_id": 1,
            "items": [
                {
                    "prestamo_detalle_id": 1,
                    "cantidad": 1
                }
            ],
            "firma_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )
    assert response.status_code == 403


def test_registrar_devolucion_qr_bad_request(client):
    # 1. Registrar/Login Admin
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
    login_response = client.post(
        "/auth/login",
        json={
            "email": admin_email,
            "password": "12345678"
        }
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Registrar Devolución con prestamo_id inexistente (Debe fallar con 400 Bad Request)
    response = client.post(
        "/almacen/registrar-devolucion-qr",
        headers=headers,
        json={
            "trabajador_id": 999,
            "codigo_unico": f"DEV-{uuid.uuid4()}",
            "dni": "12345678",
            "nombres_completos": "Inexistente",
            "cargo": "Operario",
            "fecha_devolucion": datetime.now().isoformat(),
            "prestamo_id": 999999,
            "items": [
                {
                    "prestamo_detalle_id": 999999,
                    "cantidad": 1
                }
            ],
            "firma_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="
        }
    )
    assert response.status_code == 400
