from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    nombre: str = Field(..., min_length=2, description="Nombres")
    apellidos: str = Field(..., min_length=2, description="Apellidos")
    dni: str = Field(..., min_length=8, max_length=8, description="DNI (8 dígitos)")
<<<<<<< HEAD
    # Corregido S8396: Valor por defecto explícito para Optional
    cargo: Optional[str] = Field(None, description="Cargo del usuario")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    # Corregido S8396: Valor por defecto explícito para Optional
=======
    cargo: Optional[str] = Field(None, description="Cargo del usuario")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    codigo_unico: Optional[str] = Field(None, description="Código único o correlativo (opcional)")
    role: Optional[str] = Field(
        default="user",
        description="Rol del usuario. Opciones válidas: user, trabajador, almacenero, admin"
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    nombre: str
    apellidos: str
    dni: str
<<<<<<< HEAD
    # Corregido S8396: Se asigna = None explícito
    cargo: Optional[str] = None
    email: EmailStr
    # Corregido S8396: Se asigna = None explícito
    codigo_unico: Optional[str] = None
=======
    cargo: Optional[str]
    email: EmailStr
    codigo_unico: Optional[str]
    # CAMBIO AQUÍ: Hazlo opcional y con un valor por defecto
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    role: Optional[str] = "user" 

    class Config:
        from_attributes = True

<<<<<<< HEAD

=======
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
<<<<<<< HEAD
    user: UserResponse
=======
    user: UserResponse  # Datos completos del usuario logueado
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
