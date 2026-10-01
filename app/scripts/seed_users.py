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

        # 2. Sembrar Vehículos
        vehiculos_seed = [
            {"placa": "ABC-123", "marca": "Toyota", "modelo": "Hilux", "capacidad_carga": 1000.0, "kilometraje_actual": 15000.0, "estado": "disponible"},
            {"placa": "XYZ-789", "marca": "Ford", "modelo": "Ranger", "capacidad_carga": 1200.0, "kilometraje_actual": 42000.5, "estado": "disponible"},
            {"placa": "RAM-456", "marca": "Nissan", "modelo": "Frontier", "capacidad_carga": 1050.0, "kilometraje_actual": 8500.0, "estado": "disponible"},
        ]

        for v_data in vehiculos_seed:
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
