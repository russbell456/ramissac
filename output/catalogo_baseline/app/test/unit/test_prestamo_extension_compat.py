from datetime import datetime

from app.schemas.almacen_prestamo import PrestamoQRData, ItemPrestamo
from app.models.almacen_articulos import AlmacenArticulo
from app.models.almacen_prestamo import AlmacenPrestamo


def test_prestamo_schema_accepts_optional_obra_and_external_fields():
    data = PrestamoQRData(
        trabajador_id=1,
        codigo_unico="P-001",
        dni="12345678",
        nombres_completos="Juan Perez",
        cargo="Operario",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        items=[ItemPrestamo(articulo_id=1, cantidad=2)],
        firma_base64="abc123",
        obra_id=7,
        tipo_prestamo="externo",
        empresa_ruc="20123456789",
        empresa_nombre="Constructora Alpha",
        persona_dni="12345678",
        persona_nombres="Pedro García",
        persona_telefono="987654321",
    )

    assert data.obra_id == 7
    assert data.tipo_prestamo == "externo"
    assert data.empresa_ruc == "20123456789"
    assert data.persona_telefono == "987654321"


def test_articulo_model_supports_photo_rules_and_high_value_flags():
    articulo = AlmacenArticulo(
        nombre="Rotomartillo",
        tipo="equipo",
        stock_actual=1,
        codigo_excel="R-001",
        requiere_foto_prestamo=True,
        requiere_foto_devolucion=True,
        es_activo_alto_valor=True,
    )

    assert articulo.requiere_foto_prestamo is True
    assert articulo.requiere_foto_devolucion is True
    assert articulo.es_activo_alto_valor is True


def test_prestamo_model_supports_optional_obra_and_external_data():
    prestamo = AlmacenPrestamo(
        trabajador_id=1,
        almacenero_id=2,
        codigo_unico="P-002",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        firma_base64="sig",
        obra_id=9,
        tipo_prestamo="externo",
        empresa_ruc="20456789012",
        empresa_nombre="Empresa XYZ",
        persona_dni="87654321",
        persona_nombres="María Salas",
        persona_telefono="912345678",
    )

    assert prestamo.obra_id == 9
    assert prestamo.tipo_prestamo == "externo"
    assert prestamo.empresa_nombre == "Empresa XYZ"
    assert prestamo.persona_telefono == "912345678"
