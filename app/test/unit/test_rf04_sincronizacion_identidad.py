import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import base64

from app.services.almacen_prestamo_service import AlmacenPrestamoService
from app.schemas.almacen_prestamo import PrestamoQRData, ItemPrestamo


# 🔴 CORREGIDO: mock en el lugar correcto
@patch('app.services.almacen_prestamo_service.generar_pdf_prestamo')
def test_rf04_recupera_datos_trabajador_desde_db(mock_generar_pdf, mock_db, mocker):
    """RF04: Sincronización de identidad del trabajador desde QR"""

    # ==================== MOCKS ====================

    trabajador_mock = MagicMock()
    trabajador_mock.id = 100
    trabajador_mock.nombre = "Juan"
    trabajador_mock.apellidos = "Pérez"
    trabajador_mock.dni = "12345678"
    trabajador_mock.cargo = "Operario"
    trabajador_mock.role = "trabajador"

    articulo_mock = MagicMock()
    articulo_mock.stock_actual = 50
    articulo_mock.nombre = "Taladro"

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        trabajador_mock,   # trabajador
        articulo_mock      # artículo
    ]

    service = AlmacenPrestamoService(mock_db)

    # Firma válida
    firma_valida = base64.b64encode(b"firma_test").decode('utf-8')
    firma_base64_completa = f"data:image/png;base64,{firma_valida}"

    data = PrestamoQRData(
        trabajador_id=100,
        codigo_unico="56",
        dni="12345678",
        nombres_completos="Juan Pérez",
        cargo="Operario",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        items=[ItemPrestamo(articulo_id=1, cantidad=5)],
        firma_base64=firma_base64_completa
    )

    # Mock del préstamo
    mock_prestamo = MagicMock()
    mock_prestamo.id = 999
    mock_prestamo.codigo_unico = "56"
    mock_prestamo.trabajador_id = 100
    mock_prestamo.fecha_prestamo = data.fecha_prestamo
    mock_prestamo.fecha_devolucion_prevista = data.fecha_devolucion_prevista
    mock_prestamo.firma_base64 = data.firma_base64
    mock_prestamo.estado = MagicMock(value="abierto")
    mock_prestamo.registrado_por = "almacenero"
    mock_prestamo.fecha_registro = datetime.utcnow()
    mock_prestamo.detalles = []

    mocker.patch('app.models.almacen_prestamo.AlmacenPrestamo', return_value=mock_prestamo)
    mocker.patch('app.models.almacen_prestamo.AlmacenPrestamoDetalle')
    mocker.patch.object(service.repo, 'update_stock')
    mocker.patch.object(service.repo, 'crear_prestamo', return_value=mock_prestamo)

    mock_generar_pdf.return_value = "/tmp/test_prestamo.pdf"

    # ==================== EJECUCIÓN ====================
    prestamo = service.registrar_prestamo_desde_qr(data, almacenero_id=999)

    # ==================== ASSERTS ====================
    assert prestamo is not None
    assert prestamo.trabajador_id == 100
    assert prestamo.codigo_unico == "56"
    mock_generar_pdf.assert_called_once()