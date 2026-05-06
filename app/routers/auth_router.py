from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies.auth_dependencies import get_current_user
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.database.connection import get_db
from app.security.jwt_handler import create_access_token
import traceback

router = APIRouter(prefix="/auth", tags=["auth"])
ALLOWED_ROLES = {"user", "trabajador", "almacenero", "admin"}

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Registro de usuarios. Requiere DNI, apellidos y cargo para trabajadores.
    """
    service = AuthService(db)
    
    role = user_data.role or "user"
    
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Rol no válido. Roles permitidos: {', '.join(sorted(ALLOWED_ROLES))}"
        )
    
    # Validación adicional para roles que requieren DNI y apellidos
    if role in ["trabajador", "almacenero"]:
        if not user_data.dni or not user_data.apellidos:
            raise HTTPException(status_code=400, detail="DNI y apellidos son obligatorios para este rol")
    
    try:
        new_user = service.register_user(
            nombre=user_data.nombre,
            apellidos=user_data.apellidos,
            dni=user_data.dni,
            cargo=user_data.cargo,
            email=user_data.email,
            password=user_data.password,
            role=role
        )
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error al registrar usuario")

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        auth_user = service.authenticate_user(user.email, user.password)
        if not auth_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
        
        token = create_access_token({"sub": auth_user.email, "role": auth_user.role})
        
        # Devolvemos token + datos completos del usuario
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": auth_user.role,
            "user": {
                "id": auth_user.id,
                "nombre": auth_user.nombre,
                "apellidos": auth_user.apellidos,
                "dni": auth_user.dni,
                "cargo": auth_user.cargo,
                "email": auth_user.email,
                "codigo_unico": auth_user.codigo_unico
            }
        }
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error al autenticar usuario")

# NUEVO ENDPOINT: Lista de trabajadores para el almacenero
@router.get("/trabajadores", response_model=list[UserResponse])
def obtener_trabajadores(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Lista de usuarios con role 'trabajador' (solo accesible para almacenero/admin).
    Devuelve id, nombre, apellidos, dni, cargo, codigo_unico, email, role.
    """
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="No autorizado para ver lista de trabajadores")

    service = AuthService(db)
    trabajadores = service.obtener_trabajadores(db)
    return trabajadores