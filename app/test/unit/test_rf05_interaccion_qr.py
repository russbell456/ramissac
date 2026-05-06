import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.main import app
from app.dependencies.auth_dependencies import get_current_user


def test_rf05_registrar_prestamo_qr_exitoso(client, mocker, mock_current_user_almacenero):

    def override_get_current_user():
        return mock_current_user_almacenero

    app.dependency_overrides[get_current_user] = override_get_current_user

    # ================= MOCK SERVICE =================
    mock_service_instance = MagicMock()

    mock_prestamo = MagicMock()
    mock_prestamo.id = 999
    mock_prestamo.codigo_unico = "56"
    mock_prestamo.estado = "abierto"   # 🔥 FIX REAL AQUÍ

    mock_service_instance.registrar_prestamo_desde_qr.return_value = mock_prestamo

    mocker.patch(
        "app.routers.almacen_prestamo.AlmacenPrestamoService",
        return_value=mock_service_instance
    )

    # ================= DATA =================
    data = {
        "trabajador_id": 100,
        "codigo_unico": "56",
        "dni": "12345678",
        "nombres_completos": "Juan Pérez",
        "cargo": "Operario",
        "fecha_prestamo": datetime.now(timezone.utc).isoformat(),
        "fecha_devolucion_prevista": datetime.now(timezone.utc).isoformat(),
        "items": [
            {"articulo_id": 1, "cantidad": 2}
        ],
        "firma_base64": "data:image/png;base64,test"
    }

    response = client.post("/almacen/registrar-prestamo-qr", json=data)

    print("DEBUG:", response.status_code, response.json())

    assert response.status_code == 200

    body = response.json()
    assert body["codigo_unico"] == "56"
    assert body["estado"] == "abierto"

    app.dependency_overrides.pop(get_current_user, None)