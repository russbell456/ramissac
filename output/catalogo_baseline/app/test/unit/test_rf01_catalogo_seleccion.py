import pytest
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
from app.services.almacen_articulo_service import AlmacenArticuloService
from app.models.almacen_articulos import TipoArticulo   # ← IMPORTANTE

def test_rf01_obtener_catalogo_disponibles(db_session):
    repo = AlmacenArticuloRepository(db_session)
    
    repo.upsert_articulo({
        "nombre": "Taladro", 
        "unidad_medida": "unid", 
        "tipo": TipoArticulo.EQUIPO,      # ← CORREGIDO
        "stock_actual": 10, 
        "codigo_excel": "T001"
    })
    
    repo.upsert_articulo({
        "nombre": "Tornillo", 
        "unidad_medida": "kg", 
        "tipo": TipoArticulo.CONSUMIBLE,  # ← CORREGIDO
        "stock_actual": 0, 
        "codigo_excel": "C001"
    })

    articulos = repo.get_all_disponibles()
    assert len(articulos) == 1
    assert articulos[0].nombre == "Taladro"


def test_rf01_buscar_articulos_por_nombre_o_codigo(db_session):
    repo = AlmacenArticuloRepository(db_session)
    
    repo.upsert_articulo({
        "nombre": "Rotomartillo Bosch", 
        "unidad_medida": "unid", 
        "tipo": TipoArticulo.EQUIPO,      # ← CORREGIDO
        "stock_actual": 5, 
        "codigo_excel": "RM001"
    })

    service = AlmacenArticuloService(db_session)
    resultados = service.buscar_articulos("rotomartillo")
    
    assert len(resultados) >= 1
    assert "Rotomartillo Bosch" in resultados[0].nombre