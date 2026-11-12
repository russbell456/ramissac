import json
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.pool import StaticPool

import app.models
from app.database.base import Base
from app.models.almacen_articulo_imagen import AlmacenArticuloImagen
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
from app.schemas.almacen_articulo_schema import ArticuloSchema


@pytest.fixture
def catalog():
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            AlmacenArticulo(nombre=f'Taladro {i:03}', codigo_excel=f'EQ-{i:03}',
                tipo=TipoArticulo.HERRAMIENTA, unidad_medida='UND',
                stock_total=5, stock_actual=5, marca='Bosch', modelo='Industrial',
                serie=f'SER-{i:03}') for i in range(450)
        ])
        db.add_all([
            AlmacenArticulo(nombre='Taladro agotado', tipo=TipoArticulo.HERRAMIENTA,
                unidad_medida='UND', stock_actual=0),
            AlmacenArticulo(nombre='Taladro inactivo', tipo=TipoArticulo.HERRAMIENTA,
                unidad_medida='UND', stock_actual=5, activo=False),
            AlmacenArticulo(nombre='Especial 10%_/', tipo=TipoArticulo.CONSUMIBLE,
                unidad_medida='UND', stock_actual=2),
        ])
        db.commit()
        yield db
    engine.dispose()


def test_available_search_preserves_eligibility(catalog):
    repo = AlmacenArticuloRepository(catalog)
    assert len(repo.get_all_disponibles()) == 451
    assert [a.id for a in repo.get_all_disponibles()] == [a.id for a in repo.get_all_disponibles('  ')]
    for query in ['taladro', 'BOSCH', 'Industrial', 'SER-', 'EQ-']:
        result = repo.get_all_disponibles(query)
        assert len(result) == 450
        assert all(a.activo and a.stock_actual > 0 for a in result)
    assert repo.get_all_disponibles('agotado') == []
    assert repo.get_all_disponibles('inactivo') == []
    assert repo.get_all_disponibles('no existe') == []
    assert len(repo.get_all_disponibles('  EQ-449  ')) == 1
    for query in ['%', '_', '/']:
        assert len(repo.get_all_disponibles(query)) == 1
    # The general search continues to include active articles without stock.
    assert len(repo.search('agotado')) == 1
    assert repo.search('inactivo') == []


def test_450_query_count_payload_and_measurement(catalog):
    repo = AlmacenArticuloRepository(catalog)
    count = []
    def track(*args):
        count.append(1)
    event.listen(catalog.bind, 'before_cursor_execute', track)
    all_rows = repo.get_all_disponibles()
    full_payload = [ArticuloSchema.model_validate(a).model_dump(mode='json') for a in all_rows]
    assert len(count) == 2  # articles + all image metadata, not one per row
    count.clear()
    filtered = repo.get_all_disponibles('EQ-449')
    small_payload = [ArticuloSchema.model_validate(a).model_dump(mode='json') for a in filtered]
    assert len(count) == 2
    event.remove(catalog.bind, 'before_cursor_execute', track)
    baseline, current, search = [], [], []
    for _ in range(15):
        catalog.expunge_all()
        start = perf_counter()
        catalog.query(AlmacenArticulo).options(selectinload(AlmacenArticulo.imagenes)).filter(
            AlmacenArticulo.stock_actual > 0, AlmacenArticulo.activo.is_(True)
        ).order_by(AlmacenArticulo.nombre.asc()).all()
        baseline.append((perf_counter() - start) * 1000)
        catalog.expunge_all()
        start = perf_counter()
        repo.get_all_disponibles()
        current.append((perf_counter() - start) * 1000)
        catalog.expunge_all()
        start = perf_counter()
        repo.get_all_disponibles('EQ-449')
        search.append((perf_counter() - start) * 1000)
    print(json.dumps(dict(records=len(all_rows), sql_queries=2,
        full_bytes=len(json.dumps(full_payload, ensure_ascii=False, separators=(',', ':')).encode()),
        search_bytes=len(json.dumps(small_payload, ensure_ascii=False, separators=(',', ':')).encode()),
        baseline_ms=median(baseline), current_ms=median(current), search_ms=median(search))))


def test_http_contracts_and_permissions(catalog):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.database.connection import get_db
    from app.routers.almacen_articulo_router import router
    from app.dependencies.auth_dependencies import get_current_user
    from types import SimpleNamespace

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_db] = lambda: catalog
    with TestClient(application) as client:
        original = client.get('/articulo/disponibles')
        blank = client.get('/articulo/disponibles', params={'q': '   '})
        assert original.status_code == blank.status_code == 200
        assert original.json() == blank.json()
        found = client.get('/articulo/disponibles', params={'q': 'EQ-449'})
        assert found.status_code == 200
        assert len(found.json()) == 1
        assert set(found.json()[0]) == set(original.json()[0])
        assert client.get('/articulo/disponibles', params={'q': 'agotado'}).json() == []
        assert len(client.get('/articulo/buscar', params={'q': 'agotado'}).json()) == 1
        assert len(client.get('/articulo').json()) == 452
        assert client.get(f"/articulo/{found.json()[0]['id']}").status_code == 200
        assert client.get('/articulo/999999').status_code == 404
        application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='trabajador')
        assert client.put('/articulo/1', json={}).status_code == 403
        assert client.patch('/articulo/1/desactivar').status_code == 403
