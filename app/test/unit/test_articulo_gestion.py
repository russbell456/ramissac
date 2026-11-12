import pytest
import io
import asyncio
import pandas as pd
from sqlalchemy import event
from unittest.mock import MagicMock
from app.services.almacen_articulo_service import AlmacenArticuloService
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_articulo_imagen import AlmacenArticuloImagen
from app.models.almacen_auditoria import AlmacenAuditoria
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
from app.schemas.almacen_articulo_schema import ArticuloSchema


def test_desactivar_articulo_exitoso(db_session):
    # Arrange: Crear artículo activo
    articulo = AlmacenArticulo(
        id=1,
        nombre="Amoladora Inalámbrica",
        unidad_medida="unid",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        codigo_excel="AM001",
        activo=True
    )
    db_session.add(articulo)
    db_session.commit()

    service = AlmacenArticuloService(db_session)

    # Act
    articulo_ret = service.desactivar_articulo(articulo_id=1, usuario_id=999)

    # Assert
    assert articulo_ret.activo is False
    assert articulo_ret.fecha_baja is not None

    # Verificar que se creó el registro de auditoría
    audit = db_session.query(AlmacenAuditoria).filter(
        AlmacenAuditoria.usuario_id == 999,
        AlmacenAuditoria.accion == "DESACTIVAR",
        AlmacenAuditoria.entidad == "ARTICULO",
        AlmacenAuditoria.entidad_id == 1
    ).first()
    assert audit is not None
    assert "Amoladora Inalámbrica" in audit.descripcion


def test_desactivar_articulo_inexistente(db_session):
    service = AlmacenArticuloService(db_session)
    with pytest.raises(ValueError, match="Artículo no encontrado"):
        service.desactivar_articulo(articulo_id=9999, usuario_id=999)


def test_desactivar_articulo_ya_inactivo(db_session):
    articulo = AlmacenArticulo(
        id=1,
        nombre="Amoladora Inalámbrica",
        unidad_medida="unid",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        codigo_excel="AM001",
        activo=False
    )
    db_session.add(articulo)
    db_session.commit()

    service = AlmacenArticuloService(db_session)
    with pytest.raises(ValueError, match="El artículo ya está inactivo"):
        service.desactivar_articulo(articulo_id=1, usuario_id=999)


def test_activar_articulo_exitoso(db_session):
    # Arrange: Crear artículo inactivo
    articulo = AlmacenArticulo(
        id=1,
        nombre="Martillo de Goma",
        unidad_medida="unid",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        codigo_excel="MT001",
        activo=False
    )
    db_session.add(articulo)
    db_session.commit()

    service = AlmacenArticuloService(db_session)

    # Act
    articulo_ret = service.activar_articulo(articulo_id=1, usuario_id=999)

    # Assert
    assert articulo_ret.activo is True
    assert articulo_ret.fecha_baja is None

    # Verificar que se creó el registro de auditoría
    audit = db_session.query(AlmacenAuditoria).filter(
        AlmacenAuditoria.usuario_id == 999,
        AlmacenAuditoria.accion == "ACTIVAR",
        AlmacenAuditoria.entidad == "ARTICULO",
        AlmacenAuditoria.entidad_id == 1
    ).first()
    assert audit is not None
    assert "Martillo de Goma" in audit.descripcion


def test_activar_articulo_inexistente(db_session):
    service = AlmacenArticuloService(db_session)
    with pytest.raises(ValueError, match="Artículo no encontrado"):
        service.activar_articulo(articulo_id=9999, usuario_id=999)


def test_activar_articulo_ya_activo(db_session):
    articulo = AlmacenArticulo(
        id=1,
        nombre="Martillo de Goma",
        unidad_medida="unid",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=5,
        codigo_excel="MT001",
        activo=True
    )
    db_session.add(articulo)
    db_session.commit()

    service = AlmacenArticuloService(db_session)
    with pytest.raises(ValueError, match="El artículo ya está activo"):
        service.activar_articulo(articulo_id=1, usuario_id=999)


def test_procesar_inventario_excel(db_session):
    # Crear un DataFrame en memoria para simular el Excel
    # El archivo real empieza a leer desde la fila 4 (skiprows=3)
    data = {
        "Producto": ["TALADRO PERCUTOR", "Cinta Aislante", "PRODUCTO_INCOMPLETO"],
        "Unidad Medida": ["unid", "roll", None],
        "Codigo": ["EX001", "EX002", None]
    }
    df = pd.DataFrame(data)
    
    # Crear un buffer en memoria
    excel_buffer = io.BytesIO()
    
    # Crear un Excel ficticio con 3 filas de relleno al inicio (para simular skiprows=3)
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        # Escribir filas vacías iniciales
        dummy_df = pd.DataFrame([[""]*3]*3, columns=["Producto", "Unidad Medida", "Codigo"])
        dummy_df.to_excel(writer, index=False, header=False, startrow=0)
        # Escribir el DataFrame con las columnas correctas a partir de la fila 3 (0-indexed, fila 4 excel)
        df.to_excel(writer, index=False, startrow=3)
        
    excel_buffer.seek(0)
    
    # Simular el objeto UploadFile de FastAPI
    mock_file = MagicMock()
    mock_file.file = excel_buffer
    
    async def mock_read():
        return excel_buffer.getvalue()
    mock_file.read = mock_read

    service = AlmacenArticuloService(db_session)
    
    # Act
    total_leidos = asyncio.run(service.procesar_inventario_excel(mock_file))

    # Assert
    # Total de filas leídas en el dataframe (incluyendo la fila con campos nulos)
    assert total_leidos == 3
    
    # Verificar que se insertaron los dos válidos en la base de datos
    articulo_1 = db_session.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "EX001").first()
    assert articulo_1 is not None
    assert articulo_1.nombre == "TALADRO PERCUTOR"
    assert articulo_1.tipo == TipoArticulo.EQUIPO  # "TALADRO" es keyword para EQUIPO
    assert articulo_1.stock_actual == 5

    articulo_2 = db_session.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "EX002").first()
    assert articulo_2 is not None
    assert articulo_2.nombre == "Cinta Aislante"
    assert articulo_2.tipo == TipoArticulo.CONSUMIBLE  # "Cinta Aislante" no es keyword de EQUIPO
    assert articulo_2.stock_actual == 5

    # El tercero ("PRODUCTO_INCOMPLETO") tiene Codigo = None (NaN), no debe insertarse
    articulo_3 = db_session.query(AlmacenArticulo).filter(AlmacenArticulo.nombre == "PRODUCTO_INCOMPLETO").first()
    assert articulo_3 is None


def test_listar_articulos_carga_imagenes_en_consulta_por_lote(db_session):
    articulos = [
        AlmacenArticulo(
            nombre=f"Artículo con foto {index}",
            unidad_medida="UND",
            tipo=TipoArticulo.EQUIPO,
            stock_actual=1,
        )
        for index in range(3)
    ]
    db_session.add_all(articulos)
    db_session.flush()
    db_session.add_all(
        [
            AlmacenArticuloImagen(
                articulo_id=articulo.id,
                nombre_archivo=f"foto_{index}.jpg",
                ruta=f"/uploads/articulos/foto_{index}.jpg",
                tipo_mime="image/jpeg",
            )
            for index, articulo in enumerate(articulos)
        ]
    )
    db_session.commit()

    statements = []

    def record_statement(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().lower().startswith("select"):
            statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", record_statement)
    try:
        result = AlmacenArticuloRepository(db_session).get_all()
        image_counts = [len(articulo.imagenes) for articulo in result]
    finally:
        event.remove(db_session.bind, "before_cursor_execute", record_statement)

    assert image_counts == [1, 1, 1]
    assert len(statements) == 2


def test_articulo_alto_valor_refleja_fotos_obligatorias_en_respuesta(db_session):
    articulo = AlmacenArticulo(
        nombre="Artículo de alto valor",
        unidad_medida="UND",
        tipo=TipoArticulo.EQUIPO,
        stock_actual=1,
        es_activo_alto_valor=True,
        requiere_foto_prestamo=False,
        requiere_foto_devolucion=False,
    )
    db_session.add(articulo)
    db_session.commit()

    response = ArticuloSchema.model_validate(articulo)

    assert response.requiere_foto_prestamo is True
    assert response.requiere_foto_devolucion is True
