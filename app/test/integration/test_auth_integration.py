import uuid


def test_register_user(client):

    unique_email = f"test_{uuid.uuid4()}@test.com"

    response = client.post(
        "/auth/register",
        json={
            "nombre": "Russbell",
            "apellidos": "Cari",
            "dni": "12345678",
            "cargo": "Developer",
            "email": unique_email,
            "password": "12345678",
            "role": "user"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == unique_email
    assert data["nombre"] == "Russbell"


def test_login_user(client):

    unique_email = f"login_{uuid.uuid4()}@test.com"

    register_response = client.post(
        "/auth/register",
        json={
            "nombre": "Login",
            "apellidos": "Test",
            "dni": "87654321",
            "cargo": "QA",
            "email": unique_email,
            "password": "12345678",
            "role": "user"
        }
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": "12345678"
        }
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert data["role"] == "user"


def test_login_invalid_password(client):

    unique_email = f"invalid_{uuid.uuid4()}@test.com"

    client.post(
        "/auth/register",
        json={
            "nombre": "Invalid",
            "apellidos": "Test",
            "dni": "11223344",
            "cargo": "QA",
            "email": unique_email,
            "password": "12345678",
            "role": "user"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401