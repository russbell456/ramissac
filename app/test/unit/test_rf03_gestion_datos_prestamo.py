import pytest
from datetime import datetime
from app.repositories.almacen_prestamo_repository import AlmacenPrestamoRepository
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle, EstadoPrestamo

def test_rf03_crear_prestamo_con_detalles(db_session):
    repo = AlmacenPrestamoRepository(db_session)

    prestamo = AlmacenPrestamo(
        trabajador_id=100,
        codigo_unico="P001",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        firma_base64="firma123",
        estado=EstadoPrestamo.ABIERTO
    )
    detalles = [AlmacenPrestamoDetalle(articulo_id=1, cantidad_prestada=5)]

    creado = repo.crear_prestamo(prestamo, detalles)
    assert creado.id is not None
    assert len(creado.detalles) == 1