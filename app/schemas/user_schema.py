
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
# ROLES DEL SISTEMA
# ============================================================

# Se conservan los roles existentes y se incorporan
# conductor, ingeniero y supervisor.
#
# Esta definición solo establece valores válidos.
# NO otorga permisos ni acceso a módulos.

Role = Literal[
    "user",
    "trabajador",
    "almacenero",
    "admin",
    "conductor",
    "ingeniero",
    "supervisor",
]

# Registro público: mantener exactamente la restricción
# de seguridad existente.
#
# Conductor, ingeniero y supervisor deberán ser asignados
# por el flujo administrativo autorizado.

PublicRole = Literal[
    "user",
    "trabajador",
]


# ============================================================
# VALIDACIONES REUTILIZABLES
# ============================================================

def _normalizar_nombre(value: str) -> str:
    value = " ".join(value.split())

    if len(value) < 2:
        raise ValueError(
            "Debe contener al menos 2 caracteres"
        )

    return value


def _normalizar_documento(
    value: str,
    *,
    permitir_vacio: bool = False,
) -> str:
    value = value.strip().upper()

    if not value and not permitir_vacio:
        raise ValueError(
            "El documento no puede estar vacío"
        )

    return value


def _normalizar_email(value: EmailStr) -> str:
    return str(value).strip().lower()


def _normalizar_texto_opcional(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    return value.strip() or None


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

    # No permitir asignación pública de roles privilegiados.
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
        return _normalizar_nombre(value)

    @field_validator("dni")
    @classmethod
    def limpiar_documento(
        cls,
        value: str,
    ) -> str:
        value = value.strip().upper()

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
        return _normalizar_email(value)

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
        return _normalizar_texto_opcional(value)


# ============================================================
# LOGIN
# ============================================================

class UserLogin(BaseModel):

    email: EmailStr

    # Conservar la validación actual.
    # No exigir 8 caracteres al iniciar sesión porque
    # podrían existir credenciales antiguas válidas.
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
        return _normalizar_email(value)


# ============================================================
# ACTUALIZACIÓN NORMAL
# ============================================================

# No incluye:
# - password
# - role
# - activo
# - estado_laboral
# - email
#
# Se conservan las restricciones actuales.

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

        return _normalizar_nombre(value)

    @field_validator("dni")
    @classmethod
    def limpiar_documento_opcional(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return _normalizar_documento(value)

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
        return _normalizar_texto_opcional(value)


# ============================================================
# ACTUALIZACIÓN ADMINISTRATIVA
# ============================================================

# Solo debe utilizarse en endpoints protegidos para admin.
#
# Se incorporan los roles nuevos y los campos de
# documentación del conductor.
#
# No se incluyen email ni password.
# Tampoco firma_base64 ni firma_url:
# la firma debe conservar su propio flujo autorizado.

class UserAdminUpdate(UserUpdate):

    role: Role | None = None

    estado_laboral: EstadoLaboral | None = None

    activo: bool | None = None

    # Documentación del conductor.
    # Todos los campos son opcionales para no exigir
    # documentación de conductor a los demás roles.

    licencia_vencimiento: date | None = None

    licencia_categoria: str | None = Field(
        default=None,
        max_length=20,
    )

    emo_vencimiento: date | None = None

    pase_minero_vencimiento: date | None = None

    @field_validator("licencia_categoria")
    @classmethod
    def limpiar_licencia_categoria(
        cls,
        value: str | None,
    ) -> str | None:
        return _normalizar_texto_opcional(value)


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
# RESPUESTA COMPLETA DEL USUARIO
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

    # Se conserva la implementación actual de firma.
    firma_base64: str | None = None

    # Compatibilidad con la implementación de la otra rama.
    firma_url: str | None = None

    cargo: str | None = None

    area: str | None = None

    fecha_ingreso: date | None = None

    fecha_baja: date | None = None

    estado_laboral: str

    supervisor_id: int | None = None

    role: str

    activo: bool

    # Documentación del conductor.
    licencia_vencimiento: date | None = None

    licencia_categoria: str | None = None

    emo_vencimiento: date | None = None

    pase_minero_vencimiento: date | None = None

    ultimo_acceso: datetime | None = None

    fecha_creacion: datetime

    fecha_actualizacion: datetime


# ============================================================
# PERFIL PROPIO
# ============================================================

# El usuario conserva únicamente las operaciones
# que ya estaban permitidas:
# - teléfono
# - teléfono secundario
# - dirección
# - foto_url
#
# No puede cambiar desde este schema:
# - email
# - role
# - password
# - estado_laboral
# - activo
# - documentación administrativa del conductor

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
        return _normalizar_texto_opcional(value)


# ============================================================
# CAMBIO DE CONTRASEÑA
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
