# pyrefly: ignore [missing-import]
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle, EstadoPrestamo
from app.models.almacen_devolucion import AlmacenDevolucion, EstadoDevolucion
from app.schemas.almacen_devolucion import DevolucionQRData, ItemDevolucion
from app.services.almacen_devolucion_service import AlmacenDevolucionService


# ==============================================================================
# PRUEBAS DEL SERVICIO (AlmacenDevolucionService)
# ==============================================================================

def test_registrar_devolucion_desde_qr_exitoso_parcial(db_session):
    # 1. Arrange: Crear usuario trabajador, almacenero, artículo y préstamo
    trabajador = User(
        id=10,
        nombre="Trabajador",
        apellidos="Test",
        dni="10101010",
        cargo="Operario",
        email="trabajador@test.com",
        password="password_hash",
        role="trabajador"
    )
    articulo = AlmacenArticulo(
        id=1,
        nombre="Taladro Bosch",
        unidad_medida="unid",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        codigo_excel="T001",
        activo=True
    )
    prestamo = AlmacenPrestamo(
        id=100,
        trabajador_id=10,
        codigo_unico="P-100",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        firma_base64="firma_data",
        estado=EstadoPrestamo.ABIERTO
    )
    detalle = AlmacenPrestamoDetalle(
        id=200,
        prestamo_id=100,
        articulo_id=1,
        cantidad_prestada=3,
        cantidad_devuelta=0,
        esta_devuelto=False
    )
    
    db_session.add_all([trabajador, articulo, prestamo, detalle])
    db_session.commit()

    service = AlmacenDevolucionService(db_session)
    data = DevolucionQRData(
        trabajador_id=10,
        codigo_unico="D-500",
        dni="10101010",
        nombres_completos="Trabajador Test",
        cargo="Operario",
        fecha_devolucion=datetime.utcnow(),
        prestamo_id=100,
        items=[ItemDevolucion(prestamo_detalle_id=200, cantidad=2)],
        firma_base64="firma_dev_data"
    )

    # 2. Act
    devolucion = service.registrar_devolucion_desde_qr(data, almacenero_id=999)

    # 3. Assert
    assert devolucion is not None
    assert devolucion.codigo_unico == "D-500"
    assert devolucion.estado == EstadoDevolucion.CONFIRMADA
    
    # Comprobar actualización de stock
    db_session.refresh(articulo)
    assert articulo.stock_actual == 7  # 5 inicial + 2 devueltos
    
    # Comprobar actualización de detalle préstamo
    db_session.refresh(detalle)
    assert detalle.cantidad_devuelta == 2
    assert detalle.esta_devuelto is False

    # El préstamo general debería seguir ABIERTO
    db_session.refresh(prestamo)
    assert prestamo.estado == EstadoPrestamo.ABIERTO


def test_registrar_devolucion_desde_qr_exitoso_total(db_session):
    trabajador = User(
        id=10,
        nombre="Trabajador",
        apellidos="Test",
        dni="10101010",
        cargo="Operario",
        email="trabajador@test.com",
        password="password_hash",
        role="trabajador"
    )
    articulo = AlmacenArticulo(
        id=1,
        nombre="Taladro Bosch",
        unidad_medida="unid",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        codigo_excel="T001",
        activo=True
    )
    prestamo = AlmacenPrestamo(
        id=100,
        trabajador_id=10,
        codigo_unico="P-100",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        firma_base64="firma_data",
        estado=EstadoPrestamo.ABIERTO
    )
    detalle = AlmacenPrestamoDetalle(
        id=200,
        prestamo_id=100,
        articulo_id=1,
        cantidad_prestada=3,
        cantidad_devuelta=0,
        esta_devuelto=False
    )
    
    db_session.add_all([trabajador, articulo, prestamo, detalle])
    db_session.commit()

    service = AlmacenDevolucionService(db_session)
    data = DevolucionQRData(
        trabajador_id=10,
        codigo_unico="D-500",
        dni="10101010",
        nombres_completos="Trabajador Test",
        cargo="Operario",
        fecha_devolucion=datetime.utcnow(),
        prestamo_id=100,
        items=[ItemDevolucion(prestamo_detalle_id=200, cantidad=3)],
        firma_base64="firma_dev_data"
    )

    # Act
    devolucion = service.registrar_devolucion_desde_qr(data, almacenero_id=999)

    # Assert
    db_session.refresh(detalle)
    assert detalle.cantidad_devuelta == 3
    assert detalle.esta_devuelto is True

    # El préstamo general debería cambiar a CERRADO
    db_session.refresh(prestamo)
    assert prestamo.estado == EstadoPrestamo.CERRADO


def test_registrar_devolucion_trabajador_invalido(db_session):
    service = AlmacenDevolucionService(db_session)
    data = DevolucionQRData(
        trabajador_id=999,  # No existe
        codigo_unico="D-500",
        dni="10101010",
        nombres_completos="Trabajador Test",
        cargo="Operario",
        fecha_devolucion=datetime.utcnow(),
        prestamo_id=100,
        items=[ItemDevolucion(prestamo_detalle_id=200, cantidad=2)],
        firma_base64="firma_dev_data"
    )

    with pytest.raises(ValueError, match="Trabajador no encontrado o rol inválido"):
        service.registrar_devolucion_desde_qr(data, almacenero_id=999)


def test_registrar_devolucion_detalle_inexistente(db_session):
    trabajador = User(
        id=10,
        nombre="Trabajador",
        apellidos="Test",
        dni="10101010",
        cargo="Operario",
        email="trabajador@test.com",
        password="password_hash",
        role="trabajador"
    )
    db_session.add(trabajador)
    db_session.commit()

    service = AlmacenDevolucionService(db_session)
    data = DevolucionQRData(
        trabajador_id=10,
        codigo_unico="D-500",
        dni="10101010",
        nombres_completos="Trabajador Test",
        cargo="Operario",
        fecha_devolucion=datetime.utcnow(),
        prestamo_id=100,
        items=[ItemDevolucion(prestamo_detalle_id=9999, cantidad=2)],  # No existe
        firma_base64="firma_dev_data"
    )

    with pytest.raises(ValueError, match="Detalle no encontrado"):
        service.registrar_devolucion_desde_qr(data, almacenero_id=999)


def test_registrar_devolucion_cantidad_excede_pendiente(db_session):
    trabajador = User(
        id=10,
        nombre="Trabajador",
        apellidos="Test",
        dni="10101010",
        cargo="Operario",
        email="trabajador@test.com",
        password="password_hash",
        role="trabajador"
    )
    articulo = AlmacenArticulo(
        id=1,
        nombre="Taladro",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        activo=True
    )
    prestamo = AlmacenPrestamo(
        id=100,
        trabajador_id=10,
        firma_base64="firma",
        estado=EstadoPrestamo.ABIERTO,
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow()
    )
    detalle = AlmacenPrestamoDetalle(
        id=200,
        prestamo_id=100,
        articulo_id=1,
        cantidad_prestada=3,
        cantidad_devuelta=1,
        esta_devuelto=False
    )
    db_session.add_all([trabajador, articulo, prestamo, detalle])
    db_session.commit()

    service = AlmacenDevolucionService(db_session)
    data = DevolucionQRData(
        trabajador_id=10,
        codigo_unico="D-500",
        dni="10101010",
        nombres_completos="Trabajador Test",
        cargo="Operario",
        fecha_devolucion=datetime.utcnow(),
        prestamo_id=100,
        items=[ItemDevolucion(prestamo_detalle_id=200, cantidad=3)],  # Excede (quedan 2 pendientes)
        firma_base64="firma_dev_data"
    )

    with pytest.raises(ValueError, match="Cantidad excede lo pendiente"):
        service.registrar_devolucion_desde_qr(data, almacenero_id=999)


# ==============================================================================
# PRUEBAS DEL ROUTER (/almacen/registrar-devolucion-qr)
# ==============================================================================

def test_registrar_devolucion_qr_router_exitoso(client, mocker, mock_current_user_almacenero):
    app.dependency_overrides[get_current_user] = lambda: mock_current_user_almacenero

    mock_service = MagicMock()
    mock_devolucion = MagicMock(
        id=55,
        codigo_unico="D-123",
        estado=EstadoDevolucion.CONFIRMADA
    )
    mock_service.registrar_devolucion_desde_qr.return_value = mock_devolucion

    mocker.patch(
        "app.routers.almacen_devolucion.AlmacenDevolucionService",
        return_value=mock_service
    )

    payload = {
        "trabajador_id": 10,
        "codigo_unico": "D-123",
        "dni": "10101010",
        "nombres_completos": "Trabajador Test",
        "cargo": "Operario",
        "fecha_devolucion": datetime.utcnow().isoformat(),
        "prestamo_id": 100,
        "items": [{"prestamo_detalle_id": 200, "cantidad": 2}],
        "firma_base64": "firma_base64_data"
    }

    response = client.post("/almacen/registrar-devolucion-qr", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == 55
    assert data["codigo_unico"] == "D-123"
    assert data["estado"] == "confirmada"
    assert "correctamente" in data["message"]

    app.dependency_overrides.pop(get_current_user, None)


def test_registrar_devolucion_qr_router_sin_permiso(client, mock_current_user_trabajador):
    app.dependency_overrides[get_current_user] = lambda: mock_current_user_trabajador

    payload = {
        "trabajador_id": 10,
        "codigo_unico": "D-123",
        "dni": "10101010",
        "nombres_completos": "Trabajador Test",
        "cargo": "Operario",
        "fecha_devolucion": datetime.utcnow().isoformat(),
        "prestamo_id": 100,
        "items": [{"prestamo_detalle_id": 200, "cantidad": 2}],
        "firma_base64": "firma_base64_data"
    }

    response = client.post("/almacen/registrar-devolucion-qr", json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Solo almacenero o admin" in response.json()["detail"]

    app.dependency_overrides.pop(get_current_user, None)


def test_registrar_devolucion_qr_router_error_bad_request(client, mocker, mock_current_user_almacenero):
    app.dependency_overrides[get_current_user] = lambda: mock_current_user_almacenero

    mock_service = MagicMock()
    mock_service.registrar_devolucion_desde_qr.side_effect = ValueError("Cantidad excede lo pendiente")

    mocker.patch(
        "app.routers.almacen_devolucion.AlmacenDevolucionService",
        return_value=mock_service
    )

    payload = {
        "trabajador_id": 10,
        "codigo_unico": "D-123",
        "dni": "10101010",
        "nombres_completos": "Trabajador Test",
        "cargo": "Operario",
        "fecha_devolucion": datetime.utcnow().isoformat(),
        "prestamo_id": 100,
        "items": [{"prestamo_detalle_id": 200, "cantidad": 2}],
        "firma_base64": "firma_base64_data"
    }

    response = client.post("/almacen/registrar-devolucion-qr", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Cantidad excede lo pendiente"

    app.dependency_overrides.pop(get_current_user, None)
