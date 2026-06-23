import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.services.almacen_prestamo_service import AlmacenPrestamoService
from app.schemas.almacen_prestamo import PrestamoQRData, ItemPrestamo
from app.main import app
from app.dependencies.auth_dependencies import get_current_user


# ======================================================
# RF06 + RF07: Generación de PDF + Firma (AISLADO TOTAL)
# ======================================================
def test_rf06_rf07_generacion_pdf_y_firma(mock_db, mocker):
    """RF06 + RF07: Generación de PDF y captura de firma (100% aislado)"""

    # ✅ Mock correcto (evita ReportLab real)
    mock_generar_pdf = mocker.patch(
        'app.services.almacen_prestamo_service.generar_pdf_prestamo',
        return_value="/static/prestamos/prestamo_5.pdf"
    )

    # =========================
    # Mocks de datos base
    # =========================
    trabajador_mock = MagicMock(
        id=100,
        nombre="Juan",
        apellidos="Pérez",
        dni="12345678",
        cargo="Operario",
        role="trabajador"
    )

    articulo_mock = MagicMock(
        id=1,
        stock_actual=20,
        nombre="Taladro",
        tipo=MagicMock(value="herramienta"),
        unidad_medida="unidad"
    )

    # Flujo DB: trabajador → artículo
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        trabajador_mock,
        articulo_mock
    ]

    # =========================
    # Mock modelo préstamo
    # =========================
    mock_prestamo_model = MagicMock()
    mock_prestamo_model.id = 999
    mock_prestamo_model.codigo_unico = "P-056"
    mock_prestamo_model.fecha_prestamo = datetime.utcnow()
    mock_prestamo_model.fecha_devolucion_prevista = datetime.utcnow()

    # 🔥 FIX AQUÍ: debe coincidir con el input
    mock_prestamo_model.firma_base64 = "data:image/png;base64,abc123"

    mock_prestamo_model.estado = MagicMock(value="abierto")
    mock_prestamo_model.registrado_por = "almacenero"
    mock_prestamo_model.fecha_registro = datetime.utcnow()

    # Evitar lógica extra
    mock_prestamo_model.detalles = []

    # Mock ORM
    mocker.patch(
        'app.models.almacen_prestamo.AlmacenPrestamo',
        return_value=mock_prestamo_model
    )
    mocker.patch('app.models.almacen_prestamo.AlmacenPrestamoDetalle')

    # =========================
    # Service
    # =========================
    service = AlmacenPrestamoService(mock_db)

    # Mock repo
    mocker.patch.object(service.repo, 'update_stock')
    mocker.patch.object(
        service.repo,
        'crear_prestamo',
        return_value=mock_prestamo_model
    )

    # =========================
    # Data entrada
    # =========================
    data = PrestamoQRData(
        trabajador_id=100,
        codigo_unico="P-056",
        dni="12345678",
        nombres_completos="Juan Pérez",
        cargo="Operario",
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_prevista=datetime.utcnow(),
        items=[ItemPrestamo(articulo_id=1, cantidad=2)],
        firma_base64="data:image/png;base64,abc123"
    )

    # =========================
    # Ejecución
    # =========================
    prestamo = service.registrar_prestamo_desde_qr(
        data,
        almacenero_id=999
    )

    # =========================
    # Validaciones
    # =========================
    mock_generar_pdf.assert_called_once()
    assert prestamo.firma_base64 == data.firma_base64


# ======================================================
# RF08: Descargar PDF existente
# ======================================================
def test_rf08_descargar_pdf_existente(client, mocker):
    """RF08: Descarga de PDF"""

    mocker.patch('os.path.exists', return_value=True)

    mock_file_response = MagicMock()
    mock_file_response.status_code = 200
    mock_file_response.headers = {
        "content-disposition": "attachment; filename=prestamo_1.pdf"
    }

    mocker.patch(
        'app.routers.almacen_prestamo.FileResponse',
        return_value=mock_file_response
    )

    response = client.get("/almacen/prestamo/5/pdf")

    assert response.status_code == 200


# ======================================================
# RF08: Obtener préstamos de trabajador
# ======================================================
def test_rf08_obtener_prestamos_trabajador(
    client, mocker, mock_current_user_almacenero
):
    """RF08: Obtener préstamos de un trabajador"""

    app.dependency_overrides[get_current_user] = (
        lambda: mock_current_user_almacenero
    )

    mock_prestamos = [
        {
            "id": 1,
            "trabajador_id": 100,
            "codigo_unico": "P-056",
            "nombres_completos": "Juan Pérez",
            "dni": "12345678",
            "cargo": "Operario",
            "fecha_prestamo": datetime.utcnow().isoformat(),
            "fecha_devolucion_prevista": datetime.utcnow().isoformat(),
            "firma_base64": "data:image/png;base64,abc123",
            "estado": "abierto",
            "registrado_por": "almacenero",
            "fecha_registro": datetime.utcnow().isoformat(),
            "detalles": []
        }
    ]

    mocker.patch.object(
        AlmacenPrestamoService,
        'obtener_prestamos_trabajador',
        return_value=mock_prestamos
    )

    response = client.get("/almacen/trabajador/100/prestamos")

    assert response.status_code == 200