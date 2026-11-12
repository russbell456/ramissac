from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


# ============================================================
# TIPOS GENERALES
# ============================================================

TipoDocumento = Literal[
    "DNI",
    "CE",
    "PASAPORTE",
    "OTRO",
]

Genero = Literal[
    "masculino",
    "femenino",
    "otro",
    "no_especifica",
]

EstadoLaboral = Literal[
    "activo",
    "suspendido",
    "cesado",
]


# ============================================================
# ROLES
# ============================================================

Role = Literal[
    "user",
    "trabajador",
    "almacenero",
    "admin",
]

# Roles permitidos durante el registro público.
# IMPORTANTE:
# No se permite registrar públicamente como almacenero o admin.
PublicRole = Literal[
    "user",
    "trabajador",
]


# ============================================================
# CREACIÓN PÚBLICA DE USUARIO
# ============================================================

class UserCreate(BaseModel):

    nombre: str = Field(
        min_length=2,
        max_length=100,
    )

    apellidos: str = Field(
        min_length=2,
        max_length=150,
    )

    tipo_documento: TipoDocumento = "DNI"

    dni: str = Field(
        min_length=1,
        max_length=20,
    )

    genero: Genero | None = None

    fecha_nacimiento: date | None = None

    telefono: str | None = Field(
        default=None,
        max_length=20,
    )

    telefono_secundario: str | None = Field(
        default=None,
        max_length=20,
    )

    direccion: str | None = Field(
        default=None,
        max_length=250,
    )

    cargo: str | None = Field(
        default=None,
        max_length=100,
    )

    area: str | None = Field(
        default=None,
        max_length=100,
    )

    fecha_ingreso: date | None = None

    supervisor_id: int | None = Field(
        default=None,
        gt=0,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    codigo_unico: str | None = Field(
        default=None,
        max_length=30,
    )

    role: PublicRole = Field(
        default="user",
        validation_alias=AliasChoices(
            "role",
            "rol",
        ),
    )

    @field_validator(
        "nombre",
        "apellidos",
    )
    @classmethod
    def validar_nombre(
        cls,
        value: str,
    ) -> str:

        value = " ".join(
            value.split()
        )

        if len(value) < 2:
            raise ValueError(
                "Debe contener al menos 2 caracteres"
            )

        return value

    @field_validator("dni")
    @classmethod
    def limpiar_documento(
        cls,
        value: str,
    ) -> str:

        value = (
            value.strip()
            .upper()
        )

        if not value:
            raise ValueError(
                "El documento es obligatorio"
            )

        return value

    @field_validator("email")
    @classmethod
    def normalizar_email(
        cls,
        value: EmailStr,
    ) -> str:

        return (
            str(value)
            .strip()
            .lower()
        )

    @field_validator(
        "telefono",
        "telefono_secundario",
        "direccion",
        "cargo",
        "area",
        "codigo_unico",
    )
    @classmethod
    def limpiar_texto_opcional(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None


# ============================================================
# LOGIN
# ============================================================

class UserLogin(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )

    @field_validator("email")
    @classmethod
    def normalizar_email(
        cls,
        value: EmailStr,
    ) -> str:

        return (
            str(value)
            .strip()
            .lower()
        )


# ============================================================
# ACTUALIZACIÓN NORMAL
# ============================================================
#
# IMPORTANTE:
#
# - NO contiene password.
# - NO contiene role.
# - NO contiene activo.
# - NO contiene estado_laboral.
#
# Esos campos administrativos solo pueden ser modificados
# mediante UserAdminUpdate y desde un endpoint protegido
# exclusivamente para administradores.
#
# El EMAIL tampoco se incluye porque será INMUTABLE.
# ============================================================

class UserUpdate(BaseModel):

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    apellidos: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    tipo_documento: TipoDocumento | None = None

    dni: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    genero: Genero | None = None

    fecha_nacimiento: date | None = None

    telefono: str | None = Field(
        default=None,
        max_length=20,
    )

    telefono_secundario: str | None = Field(
        default=None,
        max_length=20,
    )

    direccion: str | None = Field(
        default=None,
        max_length=250,
    )

    cargo: str | None = Field(
        default=None,
        max_length=100,
    )

    area: str | None = Field(
        default=None,
        max_length=100,
    )

    fecha_ingreso: date | None = None

    supervisor_id: int | None = Field(
        default=None,
        gt=0,
    )

    codigo_unico: str | None = Field(
        default=None,
        max_length=30,
    )

    @field_validator(
        "nombre",
        "apellidos",
    )
    @classmethod
    def validar_nombre_opcional(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = " ".join(
            value.split()
        )

        if len(value) < 2:
            raise ValueError(
                "Debe contener al menos 2 caracteres"
            )

        return value

    @field_validator("dni")
    @classmethod
    def limpiar_documento_opcional(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = (
            value.strip()
            .upper()
        )

        if not value:
            raise ValueError(
                "El documento no puede estar vacío"
            )

        return value

    @field_validator(
        "telefono",
        "telefono_secundario",
        "direccion",
        "cargo",
        "area",
        "codigo_unico",
    )
    @classmethod
    def limpiar_texto_opcional(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None


# ============================================================
# ACTUALIZACIÓN ADMINISTRATIVA
# ============================================================
#
# Este esquema es utilizado por el endpoint protegido de admin.
#
# Un ADMIN puede modificar:
#
# - datos personales
# - DNI
# - género
# - fecha de nacimiento
# - teléfonos
# - dirección
# - cargo
# - área
# - fecha de ingreso
# - supervisor
# - código único
# - role
# - estado laboral
# - activo
#
# NO puede modificar:
#
# - email
# - password
#
# La contraseña tiene su propio flujo de cambio.
# El email se mantiene como identificador inmutable.
# ============================================================

class UserAdminUpdate(UserUpdate):

    role: Role | None = None

    estado_laboral: EstadoLaboral | None = None

    activo: bool | None = None


# ============================================================
# CAMBIO DE ESTADO
# ============================================================

class UserStatusUpdate(BaseModel):

    activo: bool

    estado_laboral: EstadoLaboral


# ============================================================
# FIRMA DIGITAL
# ============================================================

class UserSignatureUpdate(BaseModel):

    firma_base64: str = Field(
        min_length=1,
    )


# ============================================================
# RESPUESTA
# ============================================================

class UserResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    codigo_unico: str | None = None

    nombre: str

    apellidos: str

    tipo_documento: str

    dni: str

    genero: str | None = None

    fecha_nacimiento: date | None = None

    telefono: str | None = None

    telefono_secundario: str | None = None

    direccion: str | None = None

    email: EmailStr

    foto_url: str | None = None

    firma_base64: str | None = None

    cargo: str | None = None

    area: str | None = None

    fecha_ingreso: date | None = None

    fecha_baja: date | None = None

    estado_laboral: str

    supervisor_id: int | None = None

    role: str

    activo: bool

    ultimo_acceso: datetime | None = None

    fecha_creacion: datetime

    fecha_actualizacion: datetime


# ============================================================
# PERFIL PROPIO
# ============================================================
#
# Este esquema se mantiene separado de UserAdminUpdate.
#
# El usuario puede actualizar únicamente:
# - teléfono
# - teléfono secundario
# - dirección
# - foto_url
#
# No puede modificar:
# - email
# - role
# - password
# - estado laboral
# - activo
# ============================================================

class UserProfileUpdate(BaseModel):

    telefono: str | None = Field(
        default=None,
        max_length=20,
    )

    telefono_secundario: str | None = Field(
        default=None,
        max_length=20,
    )

    direccion: str | None = Field(
        default=None,
        max_length=250,
    )

    foto_url: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator(
        "telefono",
        "telefono_secundario",
        "direccion",
        "foto_url",
    )
    @classmethod
    def limpiar_texto_perfil(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None


# ============================================================
# PASSWORD
# ============================================================
#
# Este es el ÚNICO esquema destinado al cambio de contraseña.
#
# La edición administrativa de usuario NO contiene password.
# ============================================================

class ChangePassword(BaseModel):

    password_actual: str = Field(
        min_length=1,
        max_length=128,
    )

    password_nueva: str = Field(
        min_length=8,
        max_length=128,
    )


# ============================================================
# TOKEN
# ============================================================

class Token(BaseModel):

    access_token: str

    token_type: str = "bearer"

    role: str

    user: UserResponse