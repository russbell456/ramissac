import pytest
from unittest.mock import MagicMock
from app.services.almacen_prestamo_service import AlmacenPrestamoService
from app.schemas.almacen_prestamo import PrestamoQRData, ItemPrestamo
from datetime import datetime, timedelta

def test_rf02_stock_insuficiente_levanta_error(mock_db):
    from app.models.user import User
    from app.models.almacen_articulos import AlmacenArticulo
    from app.models.almacen_prestamo import AlmacenPrestamo

    trabajador_mock = MagicMock(dni="12345678", nombre="Juan", apellidos="Pérez", cargo="Operario", role="trabajador", activo=True)
    articulo_mock = MagicMock(stock_actual=3, activo=True, nombre="Taladro", tipo=MagicMock(value="EQUIPO"), es_activo_alto_valor=False, requiere_foto_prestamo=False)

    def mock_query(model):
        q = MagicMock()
        if model == User:
            q.filter.return_value.first.return_value = trabajador_mock
        elif model == AlmacenPrestamo:
            q.filter.return_value.first.return_value = None
        elif model == AlmacenArticulo:
            q.filter.return_value.first.return_value = articulo_mock
            q.filter.return_value.with_for_update.return_value.first.return_value = articulo_mock
        else:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.with_for_update.return_value.first.return_value = None
        return q

    mock_db.query.side_effect = mock_query

    service = AlmacenPrestamoService(mock_db)
    now = datetime.utcnow()
    
    data = PrestamoQRData(
        trabajador_id=100,
        codigo_unico="56",
        dni="12345678",
        nombres_completos="Juan Pérez",
        cargo="Operario",
        fecha_prestamo=now,
        fecha_devolucion_prevista=now + timedelta(days=1),
        items=[ItemPrestamo(articulo_id=1, cantidad=10)],
        firma_base64="data:image/png;base64,abc123"
    )

    with pytest.raises(ValueError, match="stock suficiente|Stock insuficiente"):
        service.registrar_prestamo_desde_qr(data, almacenero_id=999)