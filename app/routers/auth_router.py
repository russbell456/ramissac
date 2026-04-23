from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies.auth_dependencies import get_current_user
from app.schemas.user_schema import UserCreate, UserResponse, Token
from app.services.auth_service import AuthService
from app.database.connection import get_db
from app.security.jwt_handler import create_access_token
import traceback

router = APIRouter(prefix="/auth", tags=["auth"])
ALLOWED_ROLES = {"user", "trabajador", "almacenero", "admin"}

# Dependencias centralizadas (S8410)
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[dict, Depends(get_current_user)]

@router.post(
    "/register", 
    response_model=UserResponse,
    responses={
        400: {"description": "Rol no válido o datos faltantes"},
        500: {"description": "Error interno al registrar"}
    }
)
def register(user_data: UserCreate, db: DbDep):
    service = AuthService(db)
    role = user_data.role or "user"
    
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol no válido. Roles permitidos: {', '.join(sorted(ALLOWED_ROLES))}"
        )
    
    if role in ["trabajador", "almacenero"] and (not user_data.dni or not user_data.apellidos):
        raise HTTPException(status_code=400, detail="DNI y apellidos son obligatorios para este rol")
    
    try:
        return service.register_user(
            nombre=user_data.nombre,
            apellidos=user_data.apellidos,
            dni=user_data.dni,
            cargo=user_data.cargo,
            email=user_data.email,
            password=user_data.password,
            role=role
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception: # S1481 corregido (se quita 'e')
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error al registrar usuario")

@router.post(
    "/login", 
    response_model=Token,
    responses={401: {"description": "Credenciales inválidas"}, 500: {"description": "Error de autenticación"}}
)
def login(user: UserLogin, db: DbDep):
    service = AuthService(db)
    try:
        auth_user = service.authenticate_user(user.email, user.password)
        if not auth_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
        
        token = create_access_token({"sub": auth_user.email, "role": auth_user.role})
        
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
    except Exception: # S1481 corregido
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error al autenticar usuario")

@router.get(
    "/trabajadores", 
    response_model=list[UserResponse],
    responses={403: {"description": "No autorizado"}}
)
def obtener_trabajadores(db: DbDep, user: UserDep):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="No autorizado")

    service = AuthService(db)
    # Ya no necesitas pasar 'db' aquí, el servicio ya lo tiene en su __init__
    return service.obtener_trabajadores()