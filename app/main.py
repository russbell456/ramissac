from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
# APP
# -------------------------------
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
]

for folder in FOLDERS:
    os.makedirs(folder, exist_ok=True)

# -------------------------------
# ARCHIVOS ESTÁTICOS
# -------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------------
# CREAR USUARIO ADMIN AUTOMÁTICAMENTE
# -------------------------------
def seed_admin_user(db: Session):
    admin_email = "admin@example.com"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin_user = User(
            nombre="Admin",
            apellidos="User",
            dni="00000000A",
            cargo="Administrador",
            codigo_unico="ADMIN001",  
            email=admin_email,
            password=Hash.get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()
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
    db = next(get_db())
    try:
        seed_admin_user(db)
    finally:
        db.close()

# -------------------------------
# ROUTERS
# -------------------------------
app.include_router(comprobantes_router)
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(inventario_router)
app.include_router(importar_rq)
app.include_router(rqs_router)  
app.include_router(almacen_devolucion_router)
app.include_router(almacen_articulo_router)
app.include_router(almacen_prestamo_router)
app.include_router(rq_item_router)
app.include_router(orden_compra_router)
app.include_router(rq_personalizado_router)
