from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.connection import SessionLocal
from app.models.user import User
from app.models.vehiculo import Vehiculo

def seed() -> None:
    db: Session = SessionLocal()
    try:
        # 1. Sembrar Usuarios
        if not db.query(User).filter_by(email="admin@example.com").first():
            admin = User(
                nombre="Admin",
                apellidos="User",
                dni="00000000A",
                cargo="Administrador",
                codigo_unico="ADMIN001",
                email="admin@example.com",
                password=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)

        if not db.query(User).filter_by(email="trabajador@ramis.com").first():
            trabajador = User(
                nombre="Juan",
                apellidos="Trabajador",
                dni="11111111B",
                cargo="Trabajador",
                codigo_unico="TRAB001",
                email="trabajador@ramis.com",
                password=hash_password("123456789"),
                role="trabajador",
            )
            db.add(trabajador)

        if not db.query(User).filter_by(email="conductor@ramis.com").first():
            conductor = User(
                nombre="Carlos",
                apellidos="Conductor",
                dni="22222222C",
                cargo="Conductor",
                codigo_unico="COND001",
                email="conductor@ramis.com",
                password=hash_password("conductor123"),
                role="conductor",
            )
            db.add(conductor)

        if not db.query(User).filter_by(email="conductor2@ramis.com").first():
            conductor2 = User(
                nombre="Luis",
                apellidos="Mendoza",
                dni="33333333D",
                cargo="Conductor",
                codigo_unico="COND002",
                email="conductor2@ramis.com",
                password=hash_password("conductor123"),
                role="conductor",
            )
            db.add(conductor2)

        if not db.query(User).filter_by(email="conductor3@ramis.com").first():
            conductor3 = User(
                nombre="Mario",
                apellidos="Vargas",
                dni="44444444E",
                cargo="Conductor",
                codigo_unico="COND003",
                email="conductor3@ramis.com",
                password=hash_password("conductor123"),
                role="conductor",
            )
            db.add(conductor3)

        # 2. Sembrar Vehículos
        vehiculos_seed = [
            {"placa": "Z7P-702", "marca": "Camioneta", "modelo": "Estándar", "capacidad_carga": 1000.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "Z8I-845", "marca": "Camioneta", "modelo": "Estándar", "capacidad_carga": 1000.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "ZDO-953", "marca": "Coaster", "modelo": "Estándar", "capacidad_carga": 2500.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "ZDX-965", "marca": "Coaster", "modelo": "Estándar", "capacidad_carga": 2500.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "Z7G-937", "marca": "HINO", "modelo": "Camión de carga", "capacidad_carga": 5000.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "Z8K-916", "marca": "FUSO", "modelo": "Camión de carga", "capacidad_carga": 5000.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "Z7F-777", "marca": "FUSO", "modelo": "Camión Grúa", "capacidad_carga": 8000.0, "kilometraje_actual": 0.0, "estado": "disponible"},
            {"placa": "Z7M-813", "marca": "HINO", "modelo": "Camión Grúa", "capacidad_carga": 8000.0, "kilometraje_actual": 0.0, "estado": "disponible"},
        ]

        for v_data in vehiculos_seed:
            v_data["tipo"] = v_data["marca"] if v_data["marca"] in {"Camioneta", "Coaster"} else ("Camión Grúa" if "Grúa" in v_data["modelo"] else "Camión de Carga")
            if not db.query(Vehiculo).filter_by(placa=v_data["placa"]).first():
                vehiculo = Vehiculo(**v_data)
                db.add(vehiculo)

        db.commit()
        print("Usuarios y Vehículos seed verificados correctamente.")
    except Exception as error:
        db.rollback()
        print(f"Error: {error}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
