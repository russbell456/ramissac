import io
import pandas as pd

from app.dependencies.auth_dependencies import get_current_user


def override_admin_user():
    class User:
        role = "admin"
    return User()


def override_trabajador_user():
    class User:
        role = "trabajador"
    return User()


def test_obtener_articulos_vacio(client):

    response = client.get("/articulo/articulos")

    assert response.status_code == 200
    assert response.json() == []


import uuid

def test_buscar_articulos_vacio(client):

    unique_email = f"test_{uuid.uuid4()}@test.com"

    # REGISTRAR USUARIO
    register_response = client.post(
        "/auth/register",
        json={
            "nombre": "Test",
            "apellidos": "User",
            "dni": "12345678",
            "cargo": "Developer",
            "email": unique_email,
            "password": "12345678",
            "role": "admin"
        }
    )

    assert register_response.status_code == 201

    # LOGIN
    login_response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": "12345678"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # REQUEST
    response = client.get(
        "/articulo/buscar?q=ta",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

def test_importar_excel_success(client):

    from app.main import app

    app.dependency_overrides[get_current_user] = override_admin_user

    data = {
        "Producto": ["Taladro Bosch"],
        "Codigo": ["TB001"],
        "Unidad Medida": ["UND"]
    }

    df = pd.DataFrame(data)

    excel_file = io.BytesIO()

    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, startrow=3)

    excel_file.seek(0)

    response = client.post(
        "/articulo/importar-excel",
        files={
            "file": (
                "inventario.xlsx",
                excel_file,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        }
    )

    assert response.status_code == 201

    body = response.json()

    assert "message" in body


def test_importar_excel_forbidden(client):

    from app.main import app

    app.dependency_overrides[get_current_user] = override_trabajador_user

    data = {
        "Producto": ["Taladro Bosch"],
        "Codigo": ["TB001"],
        "Unidad Medida": ["UND"]
    }

    df = pd.DataFrame(data)

    excel_file = io.BytesIO()

    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, startrow=3)

    excel_file.seek(0)

    response = client.post(
        "/articulo/importar-excel",
        files={
            "file": (
                "inventario.xlsx",
                excel_file,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        }
    )

    assert response.status_code == 403