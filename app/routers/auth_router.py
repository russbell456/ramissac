from __future__ import annotations
<<<<<<< HEAD
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies.auth_dependencies import get_current_user
from app.schemas.user_schema import UserCreate, UserResponse, Token
=======
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies.auth_dependencies import get_current_user
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse, Token
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
from app.services.auth_service import AuthService
from app.database.connection import get_db
from app.security.jwt_handler import create_access_token
import traceback

<<<<<<< HEAD
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
=======
# Organizamos bajo una etiqueta de seguridad clara
router = APIRouter(prefix="/auth", tags=["Seguridad y Acceso"])
ALLOWED_ROLES = {"user", "trabajador", "almacenero", "admin"}

@router.post(
    "/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario"
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Crea una cuenta en el sistema **RamisToolX**.
    
    - **Validación de Roles**: Solo permite roles definidos (user, trabajador, almacenero, admin).
    - **Requisitos por Rol**: Si el usuario es 'trabajador' o 'almacenero', es obligatorio incluir DNI y Apellidos para la trazabilidad de activos.
    - **Integridad**: El sistema verifica que el email o DNI no existan previamente.
    """
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    service = AuthService(db)
    role = user_data.role or "user"
    
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol no válido. Roles permitidos: {', '.join(sorted(ALLOWED_ROLES))}"
        )
    
<<<<<<< HEAD
    if role in ["trabajador", "almacenero"] and (not user_data.dni or not user_data.apellidos):
        raise HTTPException(status_code=400, detail="DNI y apellidos son obligatorios para este rol")
    
    try:
        return service.register_user(
=======
    if role in ["trabajador", "almacenero"]:
        if not user_data.dni or not user_data.apellidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Error de validación: DNI y apellidos son obligatorios para personal operativo."
            )
    
    try:
        new_user = service.register_user(
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
            nombre=user_data.nombre,
            apellidos=user_data.apellidos,
            dni=user_data.dni,
            cargo=user_data.cargo,
            email=user_data.email,
            password=user_data.password,
            role=role
        )
<<<<<<< HEAD
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
=======
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo crítico en el registro.")

@router.post(
    "/login", 
    response_model=Token, 
    summary="Autenticación de usuario (JWT)"
)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Genera un token de acceso seguro para el usuario.
    
    - **Tipo de Token**: Bearer Token (JWT).
    - **Contenido**: El token incluye la identidad del usuario y su rol.
    - **Seguridad**: El token debe ser incluido en el encabezado de cada petición: `Authorization: Bearer <token>`.
    """
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    service = AuthService(db)
    try:
        auth_user = service.authenticate_user(user.email, user.password)
        if not auth_user:
<<<<<<< HEAD
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
=======
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Credenciales incorrectas. Verifique su email y contraseña."
            )
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
        
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
<<<<<<< HEAD
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
=======
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error en el proceso de autenticación.")

@router.get(
    "/trabajadores", 
    response_model=list[UserResponse], 
    summary="Listar personal operativo"
)
def obtener_trabajadores(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Obtiene la nómina de trabajadores registrados en el sistema.
    
    - **Restricción**: Solo accesible para usuarios con privilegios de **Almacenero** o **Admin**.
    - **Uso**: Útil para asignar préstamos de herramientas en el almacén de Ramis SAC.
    """
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso denegado: Se requiere rol administrativo para consultar la lista de trabajadores."
        )

    service = AuthService(db)
    trabajadores = service.obtener_trabajadores(db)
    return trabajadores
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
