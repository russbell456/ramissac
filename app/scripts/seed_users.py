from __future__ import annotations

from app.database.connection import SessionLocal
from app.models.user import User
from app.security.hashing import Hash  # <-- usamos tu clase Hash
from sqlalchemy.orm import Session

def seed():
    db: Session = SessionLocal()
    try:
        # Crear usuario admin de prueba
        user = User(
            nombre="Admin",
            apellidos="User",
            dni="00000000A",
            cargo="Administrador",
            codigo_unico="ADMIN001",  
            email="admin@example.com",
            password=Hash.get_password_hash("admin123"),
            role="admin"
        )
        db.add(user)
        db.commit()
        print("Usuario admin creado correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
