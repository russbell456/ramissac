"""Ensure all existing routers are exposed once, including nested aggregators."""
from collections import Counter
import importlib
from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest

from app.main import app


def routes_of(router):
    for route in router.routes:
        if isinstance(route, APIRoute):
            yield route
        elif getattr(route, 'original_router', None) is not None:
            # Newer FastAPI releases defer include_router expansion.
            yield from routes_of(route.original_router)


def test_every_created_router_endpoint_is_registered_once():
    actual = Counter((route.path, method, route.endpoint)
        for route in routes_of(app) for method in route.methods)
    expected = set()
    router_directory = Path(__file__).resolve().parents[2] / 'routers'
    for file in sorted(router_directory.glob('*.py')):
        module = importlib.import_module(f'app.routers.{file.stem}')
        router = getattr(module, 'router', None)
        if router is not None:
            expected.update((route.path, method, route.endpoint)
                for route in routes_of(router) for method in route.methods)
    missing = expected - actual.keys()
    assert not missing, sorted((path, method) for path, method, _ in missing)
    duplicates = [(path, method) for (path, method, _), count in actual.items() if count != 1]
    assert not duplicates, duplicates
    # Different handlers must not shadow each other on the same path/method.
    path_counts = Counter((path, method) for path, method, _ in actual.elements())
    assert not [key for key, count in path_counts.items() if count != 1]
    schema = app.openapi()['paths']
    for route in routes_of(app):
        if route.include_in_schema:
            assert all(method.lower() in schema[route.path] for method in route.methods)


@pytest.mark.parametrize('path', [
    '/api/jornadas/', '/api/vehiculos/', '/api/mantenimientos/',
    '/api/planes-mantenimiento/', '/api/inspecciones/', '/api/averias/',
    '/api/incidentes/', '/api/transportes/conductores',
])
def test_transport_routes_remain_protected(path):
    # No lifespan: registration/auth checks do not run startup seeds/migrations.
    response = TestClient(app).get(path)
    assert response.status_code == 401
