import pytest
from unittest.mock import MagicMock
from app.services.almacen_prestamo_service import AlmacenPrestamoService
from app.schemas.almacen_prestamo import PrestamoQRData, ItemPrestamo
from datetime import datetime

def test_rf02_stock_insuficiente_levanta_error(mock_db):
    articulo_mock = MagicMock(stock_actual=3)
    mock_db.query.return_value.filter.return_value.first.return_value = articulo_mock

    service = AlmacenPrestamoService(mock_db)
    
    data = PrestamoQRData(
        trabajador_id=100,
        codigo_unico="56",
        dni="12345678",
        nombres_completos="Juan Pérez",
        cargo="Operario",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        items=[ItemPrestamo(articulo_id=1, cantidad=10)],
        firma_base64="data:image/png;base64,abc123"
    )

    with pytest.raises(ValueError, match="stock suficiente|Stock insuficiente"):
        service.registrar_prestamo_desde_qr(data, almacenero_id=999)