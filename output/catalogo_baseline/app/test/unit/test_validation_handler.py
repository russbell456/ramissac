from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr, Field

from app.core.validation_handler import request_validation_exception_handler
from app.schemas.user_schema import UserCreate, UserLogin


class _SampleBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


@pytest.fixture()
def validation_client():
    app = FastAPI()
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )

    @app.post("/test")
    def test_endpoint(body: _SampleBody):
        return {"ok": True}

    return TestClient(app)


def test_validation_handler_returns_400_for_invalid_email(validation_client):
    response = validation_client.post(
        "/test",
        json={"email": "sin-arroba.com", "password": "12345678"},
    )

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


def test_validation_handler_returns_400_for_short_password(validation_client):
    response = validation_client.post(
        "/test",
        json={"email": "a@b.com", "password": "123"},
    )

    assert response.status_code == 400


def test_user_create_rejects_dni_with_letters():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserCreate(
            nombre="Juan",
            apellidos="Pérez",
            dni="1234567A",
            email="juan@test.com",
            password="12345678",
        )


def test_user_create_accepts_valid_dni():
    user = UserCreate(
        nombre="Juan",
        apellidos="Pérez",
        dni="12345678",
        email="juan@test.com",
        password="12345678",
    )

    assert user.dni == "12345678"


def test_user_login_rejects_email_without_at():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserLogin(email="adminexample.com", password="12345678")


def test_user_login_rejects_short_password():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserLogin(email="admin@example.com", password="123")
