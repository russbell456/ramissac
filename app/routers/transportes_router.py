"""
Router agregador del módulo de Transportes.

Agrupa todos los sub-routers del módulo bajo un punto de entrada único
en main.py, sin renombrar los prefijos de los endpoints existentes.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.routers.vehiculo_router import router as vehiculo_router
from app.routers.ruta_router import router as ruta_router
from app.routers.mantenimiento_router import router as mantenimiento_router
from app.routers.plan_mantenimiento_router import router as plan_mantenimiento_router
from app.routers.inspeccion_router import router as inspeccion_router
from app.routers.averia_router import router as averia_router
from app.routers.incidente_router import router as incidente_router
from app.routers.jornada_transporte_router import router as jornada_transporte_router

# Router contenedor: no añade prefijo propio para no alterar
# las URLs existentes (ej. /api/vehiculos, /api/jornadas, etc.)
router = APIRouter(tags=["Módulo de Transportes"])

router.include_router(vehiculo_router)
router.include_router(ruta_router)
router.include_router(mantenimiento_router)
router.include_router(plan_mantenimiento_router)
router.include_router(inspeccion_router)
router.include_router(averia_router)
router.include_router(incidente_router)
router.include_router(jornada_transporte_router)
