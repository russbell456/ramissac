from __future__ import annotations
<<<<<<< HEAD

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
=======
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
import os

from app.database.base import Base
from app.database.connection import engine, get_db
from app.models.user import User
from app.security.hashing import Hash
from sqlalchemy.orm import Session

# -------------------------------
# IMPORTAR ROUTERS
# -------------------------------
from app.routers.auth_router import router as auth_router
<<<<<<< HEAD

from app.routers.almacen_articulo_router import router as almacen_articulo_router
from app.routers.almacen_prestamo import router as almacen_prestamo_router
from app.routers.almacen_devolucion import router as almacen_devolucion_router
app = FastAPI(title="Sistema con Roles y Auth")

# -------------------------------
# RUTA ROOT (IMPORTANTE PARA RAILWAY)
# -------------------------------
@app.get("/")
def root():
    return {"status": "OK", "message": "FastAPI alive"}

# -------------------------------
# CREACIÓN AUTOMÁTICA DE CARPETAS
# -------------------------------
FOLDERS = [
    "uploads",
    "uploads/comprobantes",
    "uploads/ordenes_compra",
    "temp_files",
    "static",
    "static/firmas",
    "static/generados",
    "static/templates"  # 👈 plantillas
=======
from app.routers.rqs_router import router as rqs_router
from app.routers.rq_item_router import router as rq_item_router
from app.routers.orden_compra_router import router as orden_compra_router
from app.routers.inventario_router import router as inventario_router
from app.routers.pdf_import_router import router as importar_rq
from app.routers.upload_router import router as upload_router
from app.routers.comprobantes_router import router as comprobantes_router
from app.routers.rq_personalizado_router import router as rq_personalizado_router
from app.routers.almacen_articulo_router import router as almacen_articulo_router
from app.routers.almacen_prestamo import router as almacen_prestamo_router
from app.routers.almacen_devolucion import router as almacen_devolucion_router

# -------------------------------
# CONFIGURACIÓN DE LA API (SWAGGER PROFESIONAL)
# -------------------------------
app = FastAPI(
    title="🚀 RamisToolX API - Corporación Ramis SAC",
    description="""
    ## Sistema Integral de Gestión de Activos y Control de Adquisiciones
    
    API desarrollada para la optimización de procesos logísticos y de almacén. 
    Implementa estándares de **OpenAPI 3.0** y principios de la norma **ISO 25010**.

    ### 🛠️ Equipo de Desarrollo (Orbit):
    * **JxL** (Backend & Lead Developer)
    * **Dan** (Analista de Sistemas)
    * **Pawel** (QA & Testing)
    * **Rusbel** (DevOps & Dockerizacion)
    
    ### 🔑 Seguridad:
    Esta API utiliza **OAuth2** con **JWT (JSON Web Tokens)** para el control de acceso basado en roles.
    """,
    version="1.2.0",
    contact={
        "name": "Equipo Orbit - UPeU Juliaca",
        "url": "https://github.com/russbell456/ramissac",
    }
)

# -------------------------------
# MIDDLEWARE (CORS) - Vital para que la App Móvil conecte
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción poner el dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# RUTA ROOT (CONTROL DE SALUD)
# -------------------------------
@app.get("/", tags=["Sistema"])
def root():
    return {
        "status": "Online",
        "project": "RamisToolX",
        "version": "1.2.0",
        "message": "Backend central operativo"
    }

# -------------------------------
# INFRAESTRUCTURA Y CARPETAS
# -------------------------------
FOLDERS = [
    "uploads/comprobantes",
    "uploads/ordenes_compra",
    "temp_files",
    "static/firmas",
    "static/generados",
    "static/templates"
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
]

for folder in FOLDERS:
    os.makedirs(folder, exist_ok=True)

<<<<<<< HEAD
# -------------------------------
# ARCHIVOS ESTÁTICOS
# -------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------------
# CREAR USUARIO ADMIN AUTOMÁTICAMENTE
=======
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# -------------------------------
# DATA SEEDING (ADMIN POR DEFECTO)
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
# -------------------------------
def seed_admin_user(db: Session):
    admin_email = "admin@example.com"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin_user = User(
            nombre="Admin",
<<<<<<< HEAD
            apellidos="User",
            dni="00000000A",
            cargo="Administrador",
            codigo_unico="ADMIN001",  
=======
            apellidos="Principal",
            dni="00000000",
            cargo="Administrador del Sistema",
            codigo_unico="ADMIN-ORBIT",
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
            email=admin_email,
            password=Hash.get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()
<<<<<<< HEAD
        print("Usuario admin creado correctamente.")
    else:
        print("Usuario admin ya existe.")

# -------------------------------
# STARTUP (CLAVE PARA RAILWAY)
# -------------------------------
@app.on_event("startup")
def on_startup():
    # Crear tablas
    Base.metadata.create_all(bind=engine)

    # Seed admin
=======
        print("✅ Usuario admin de respaldo creado.")

# -------------------------------
# STARTUP EVENT
# -------------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    db = next(get_db())
    try:
        seed_admin_user(db)
    finally:
        db.close()

# -------------------------------
<<<<<<< HEAD
# ROUTERS
# -------------------------------

app.include_router(almacen_devolucion_router)
app.include_router(almacen_articulo_router)
app.include_router(almacen_prestamo_router)
app.include_router(auth_router)

=======
# INCLUSIÓN DE ROUTERS (ORDEN LÓGICO)
# -------------------------------
# 1. Acceso y Archivos
app.include_router(auth_router)
app.include_router(upload_router)

# 2. Gestión de Requerimientos
app.include_router(importar_rq)
app.include_router(rqs_router)
app.include_router(rq_item_router)
app.include_router(rq_personalizado_router)

# 3. Logística y Compras
app.include_router(orden_compra_router)
app.include_router(comprobantes_router)

# 4. Inventario y Almacén
app.include_router(inventario_router)
app.include_router(almacen_articulo_router)
app.include_router(almacen_prestamo_router)
app.include_router(almacen_devolucion_router)
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
