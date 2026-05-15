from __future__ import annotations

from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.core.security import hash_password, verify_password

class AuthService:
    def __init__(self, db: Session):
<<<<<<< HEAD
        self.db = db  # Guardamos la sesión
=======
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
        self.user_repo = UserRepository(db)

    def register_user(self, nombre: str, apellidos: str, dni: str, cargo: str | None, email: str, password: str, role: str = "user"):
        if self.user_repo.get_by_email(email):
            raise ValueError("El email ya está registrado")
        
        hashed_password = hash_password(password)
        user = User(
            nombre=nombre,
            apellidos=apellidos,
            dni=dni,
            cargo=cargo,
            email=email,
            password=hashed_password,
            role=role
        )
        return self.user_repo.create_user(user)

    def authenticate_user(self, email: str, password: str):
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password):
            return None
        return user

    # NUEVO MÉTODO: Obtener todos los trabajadores
<<<<<<< HEAD
    def obtener_trabajadores(self):
        # Usamos la sesión que ya vive en el servicio
        return self.db.query(User).filter(User.role == "trabajador").all()
=======
    def obtener_trabajadores(self, db: Session):
        return db.query(User).filter(User.role == "trabajador").all()
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
