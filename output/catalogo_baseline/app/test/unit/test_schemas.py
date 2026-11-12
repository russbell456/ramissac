import pytest
from app.schemas.almacen_prestamo import PrestamoQRData, ItemPrestamo
from pydantic import ValidationError
from datetime import datetime

def test_schema_prestamo_qr_firma_obligatoria():
    with pytest.raises(ValidationError):
        PrestamoQRData(
            trabajador_id=100,
            codigo_unico="56",
            dni="12345678",
            nombres_completos="Juan",
            cargo="Operario",
            fecha_prestamo=datetime.utcnow(),
            fecha_devolucion_prevista=datetime.utcnow(),
            items=[ItemPrestamo(articulo_id=1, cantidad=1)],
            # falta firma_base64
        )