from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.validation_handler import (
    request_validation_exception_handler,
)

from app.database.base import Base
from app.database.connection import (
    engine,
    get_db,
)

from app.models.almacen_articulo_imagen import (
    AlmacenArticuloImagen,
)

from app.models.almacen_obras import (
    AlmacenObra,
)

from app.models.almacen_terceros import (
    AlmacenTercero,
)

from app.models.user import User

import app.models  # noqa: F401


# ============================================================
# ROUTERS
# ============================================================

from app.routers.almacen_articulo_router import (
    router as almacen_articulo_router,
)

from app.routers.almacen_devolucion import (
    router as almacen_devolucion_router,
)

from app.routers.almacen_obras import (
    router as almacen_obras_router,
)

from app.routers.almacen_prestamo import (
    router as almacen_prestamo_router,
)

from app.routers.almacen_terceros import (
    router as almacen_terceros_router,
)

from app.routers.auth_router import (
    router as auth_router,
)

from app.routers.vehiculo_router import (
    router as vehiculo_router,
)

from app.routers.ruta_router import (
    router as ruta_router,
)

from app.routers.mantenimiento_router import (
    router as mantenimiento_router,
)


from app.security.hashing import Hash


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(
    _: FastAPI,
):
    """
    Inicialización principal del backend.

    1. Crea las tablas que todavía no existan.
    2. Verifica/crea el administrador inicial.
    """

    Base.metadata.create_all(
        bind=engine
    )

    db = next(
        get_db()
    )

    try:
        seed_admin_user(
            db
        )

    finally:
        db.close()

    yield


# ============================================================
# APLICACIÓN
# ============================================================

app = FastAPI(
    title="🚀 RamisToolX API - Corporación Ramis SAC",

    description="""
    ## Sistema Integral de Gestión de Activos y Control de Adquisiciones

    API desarrollada para la optimización de procesos
    logísticos y de almacén.

    Implementa estándares de OpenAPI 3.0 y principios
    de la norma ISO 25010.

    ### 🛠️ Equipo de Desarrollo (Orbit):

    * **JxL** (Backend & Lead Developer)
    * **Dan** (Analista de Sistemas)
    * **Pawel** (QA & Testing)
    * **Rusbel** (DevOps & Dockerizacion)

    ### 🔑 Seguridad:

    Esta API utiliza OAuth2 con JWT (JSON Web Tokens)
    para el control de acceso basado en roles.
    """,

    version="1.2.0",

    contact={
        "name": "Equipo Orbit - UPeU Juliaca",
        "url": (
            "https://github.com/"
            "russbell456/ramissac"
        ),
    },

    lifespan=lifespan,
)


# ============================================================
# DIRECTORIOS
# ============================================================

FOLDERS = [
    "uploads",
    "uploads/comprobantes",
    "uploads/ordenes_compra",
    "temp_files",
    "static",
    "static/firmas",
    "static/generados",
    "static/templates",
]


for folder in FOLDERS:
    os.makedirs(
        folder,
        exist_ok=True,
    )


# ============================================================
# MANEJO DE VALIDACIONES
# ============================================================

app.add_exception_handler(
    RequestValidationError,
    request_validation_exception_handler,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static",
)

app.mount(
    "/uploads",
    StaticFiles(
        directory="uploads"
    ),
    name="uploads",
)


# ============================================================
# ROOT
# ============================================================

@app.get(
    "/",
    tags=["Sistema"],
)
def root():
    return {
        "status": "Online",
        "project": "RamisToolX",
        "version": "1.2.0",
        "message": (
            "Backend central operativo"
        ),
    }


# ============================================================
# ADMINISTRADOR PREDEFINIDO
# ============================================================

def seed_admin_user(
    db: Session,
):
    """
    Crea el administrador inicial si todavía no existe.

    Este usuario es el único administrador inicial del sistema.

    Credenciales iniciales:

        email: admin@example.com
        password: admin123

    IMPORTANTE:
    El endpoint /auth/register NO puede crear administradores.
    """

    admin_email = "admin@example.com"

    existing = (
        db.query(User)
        .filter(
            User.email == admin_email
        )
        .first()
    )

    if existing:
        print(
            "Usuario admin ya existe."
        )
        return

    admin_user = User(
        nombre="Admin",
        dni="00000000A",
        cargo="Administrador",
        apellidos="Principal",
        codigo_unico="ADMIN-ORBIT",
        email=admin_email,
        password=Hash.get_password_hash(
            "admin123"
        ),

        # ====================================================
        # ROL PRIVILEGIADO
        # ====================================================
        role="admin",

        # ====================================================
        # ESTADO INICIAL
        # ====================================================
        estado_laboral="activo",
        activo=True,
    )

    db.add(
        admin_user
    )

    db.commit()

    print(
        "Usuario admin creado correctamente."
    )


# ============================================================
# REGISTRO DE ROUTERS
# ============================================================

app.include_router(
    auth_router
)

app.include_router(
    almacen_articulo_router
)

app.include_router(
    almacen_prestamo_router
)

app.include_router(
    almacen_devolucion_router
)

app.include_router(
    almacen_obras_router
)

app.include_router(
    almacen_terceros_router
)

app.include_router(
    vehiculo_router
)

app.include_router(
    ruta_router
)

app.include_router(
    mantenimiento_router
)