from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.schemas.user_schema import (
    ChangePassword,
    Token,
    UserAdminUpdate,
    UserCreate,
    UserProfileUpdate,
    UserLogin,
    UserResponse,
    UserSignatureUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from app.security.jwt_handler import create_access_token
from app.services.auth_service import (
    AuthService,
    ESTADOS_LABORALES,
    ROLES_VALIDOS,
)


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# ============================================================
# DEPENDENCIAS
# ============================================================

DbDep = Annotated[
    Session,
    Depends(get_db),
]

UserDep = Annotated[
    dict,
    Depends(get_current_user),
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_campo(
    user,
    campo: str,
):
    """
    Permite obtener un campo tanto si el usuario autenticado
    llega como diccionario como si llega como objeto.
    """

    if isinstance(user, dict):
        return user.get(campo)

    return getattr(
        user,
        campo,
        None,
    )


def exigir_admin(
    user,
) -> None:
    """
    Solamente un administrador puede ejecutar
    operaciones administrativas.

    Esto incluye:
    - editar usuarios;
    - cambiar roles;
    - cambiar estado laboral;
    - activar/desactivar;
    - subir foto de otro usuario;
    - cambiar firma de otro usuario.
    """

    if (
        obtener_campo(
            user,
            "role",
        )
        != "admin"
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No autorizado. "
                "Se requiere rol admin."
            ),
        )


def exigir_admin_o_almacenero(
    user,
) -> None:
    """
    Permite operaciones destinadas tanto a admin
    como a almacenero.
    """

    if (
        obtener_campo(
            user,
            "role",
        )
        not in {
            "admin",
            "almacenero",
        }
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado.",
        )


def obtener_id(
    user,
) -> int:
    """
    Obtiene el ID del usuario autenticado.
    """

    user_id = obtener_campo(
        user,
        "id",
    )

    if user_id is None:

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Usuario autenticado inválido."
            ),
        )

    return int(user_id)


# ============================================================
# REGISTRO
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario o trabajador",
)
def register(
    user_data: UserCreate,
    db: DbDep,
):
    """
    Registro público.

    Los únicos roles permitidos son:

    - user
    - trabajador

    No se permite crear públicamente:

    - almacenero
    - admin

    IMPORTANTE:
    La foto y firma NO se reciben todavía en este endpoint.
    Se mantienen mediante sus endpoints correspondientes.
    """

    service = AuthService(db)

    try:

        new_user = service.register_user(
            nombre=user_data.nombre,
            apellidos=user_data.apellidos,
            tipo_documento=user_data.tipo_documento,
            dni=user_data.dni,
            genero=user_data.genero,
            fecha_nacimiento=user_data.fecha_nacimiento,
            telefono=user_data.telefono,
            telefono_secundario=(
                user_data.telefono_secundario
            ),
            direccion=user_data.direccion,
            cargo=user_data.cargo,
            area=user_data.area,
            fecha_ingreso=user_data.fecha_ingreso,
            supervisor_id=user_data.supervisor_id,
            email=str(user_data.email),
            password=user_data.password,
            codigo_unico=user_data.codigo_unico,
            role=user_data.role or "user",
        )

        return new_user

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "El correo, documento o código "
                "ya está registrado."
            ),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al registrar usuario"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al registrar usuario.",
        ) from exc


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión",
)
def login(
    user_data: UserLogin,
    db: DbDep,
):
    """
    Inicia sesión y devuelve JWT.
    """

    service = AuthService(db)

    try:

        auth_user = (
            service.authenticate_user(
                email=str(
                    user_data.email
                ),
                password=user_data.password,
            )
        )

        if not auth_user:

            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED
                ),
                detail=(
                    "Credenciales inválidas "
                    "o cuenta no disponible."
                ),
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

        token = create_access_token(
            {
                "sub": auth_user.email,
                "role": auth_user.role,
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": auth_user.role,
            "user": auth_user,
        }

    except HTTPException:
        raise

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al autenticar usuario"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al autenticar usuario.",
        ) from exc


# ============================================================
# PERFIL PROPIO
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener usuario autenticado",
)
def obtener_mi_perfil(
    db: DbDep,
    current_user: UserDep,
):
    """
    Obtiene los datos del usuario actualmente autenticado.
    """

    service = AuthService(db)

    try:

        return service.obtener_usuario(
            obtener_id(
                current_user
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc


# ============================================================
# ACTUALIZAR PERFIL PROPIO
# ============================================================

@router.patch(
    "/me",
    response_model=UserResponse,
    summary=(
        "Actualizar datos de contacto "
        "del usuario autenticado"
    ),
)
def actualizar_mi_perfil(
    data: UserProfileUpdate,
    db: DbDep,
    current_user: UserDep,
):
    """
    El usuario puede modificar:

    - teléfono;
    - teléfono secundario;
    - dirección;
    - foto_url.

    No puede modificar:

    - email;
    - role;
    - password;
    - estado laboral;
    - activo.
    """

    service = AuthService(db)

    try:

        return service.actualizar_usuario(
            user_id=obtener_id(
                current_user
            ),
            datos=data.model_dump(
                exclude_unset=True
            ),
            usuario_auditoria=obtener_id(
                current_user
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al actualizar perfil propio"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Error al actualizar el perfil."
            ),
        ) from exc


# ============================================================
# FIRMA DIGITAL - PROPIA
# ============================================================

@router.put(
    "/me/firma",
    response_model=UserResponse,
    summary="Guardar firma digital en Base64",
)
def guardar_mi_firma(
    data: UserSignatureUpdate,
    db: DbDep,
    current_user: UserDep,
):
    """
    Permite al usuario autenticado guardar su propia firma.
    """

    service = AuthService(db)

    try:

        user = service.guardar_firma_base64(
            user_id=obtener_id(
                current_user
            ),
            firma_base64=data.firma_base64,
        )

        return user

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al guardar firma"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al guardar la firma.",
        ) from exc


@router.post(
    "/me/firma/imagen",
    response_model=dict,
    summary="Convertir firma Base64 a imagen PNG",
)
def generar_mi_imagen_firma(
    db: DbDep,
    current_user: UserDep,
):
    """
    Convierte la firma almacenada en Base64
    en una imagen PNG.
    """

    service = AuthService(db)

    try:

        url = service.generar_imagen_firma(
            user_id=obtener_id(
                current_user
            )
        )

        return {
            "mensaje": (
                "Firma convertida correctamente."
            ),
            "firma_url": url,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Error al generar imagen de firma"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Error al generar la imagen de firma."
            ),
        ) from exc


# ============================================================
# FOTO - PROPIA
# ============================================================

@router.post(
    "/me/foto",
    response_model=UserResponse,
    summary="Subir foto del usuario",
)
async def subir_mi_foto(
    db: DbDep,
    current_user: UserDep,
    archivo: UploadFile = File(...),
):
    """
    Permite al usuario autenticado subir su propia foto.
    """

    service = AuthService(db)

    try:

        if not archivo.filename:

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Debe seleccionar una imagen."
                ),
            )

        extension = (
            Path(
                archivo.filename
            ).suffix.lower()
        )

        extensiones_permitidas = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        if (
            extension
            not in extensiones_permitidas
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Formato de imagen no permitido. "
                    "Use JPG, JPEG, PNG o WEBP."
                ),
            )

        contenido = await archivo.read()

        if not contenido:

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail="La imagen está vacía.",
            )

        return service.guardar_foto_usuario(
            user_id=obtener_id(
                current_user
            ),
            contenido=contenido,
            extension=extension,
        )

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al guardar foto de usuario"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al guardar la foto.",
        ) from exc


# ============================================================
# PASSWORD - PROPIA
# ============================================================

@router.post(
    "/me/cambiar-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar contraseña propia",
)
def cambiar_mi_password(
    data: ChangePassword,
    db: DbDep,
    current_user: UserDep,
):
    """
    El usuario cambia su propia contraseña.

    IMPORTANTE:
    No existe un endpoint administrativo aquí para
    modificar password desde UserAdminUpdate.
    """

    service = AuthService(db)

    try:

        service.cambiar_password(
            user_id=obtener_id(
                current_user
            ),
            password_actual=data.password_actual,
            password_nueva=data.password_nueva,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al cambiar contraseña"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al cambiar la contraseña.",
        ) from exc


# ============================================================
# TRABAJADORES
# ============================================================

@router.get(
    "/trabajadores",
    response_model=list[UserResponse],
    summary=(
        "Listar trabajadores y "
        "almaceneros activos"
    ),
)
def obtener_trabajadores(
    db: DbDep,
    current_user: UserDep,
):
    """
    Admin y almacenero pueden consultar
    trabajadores y almaceneros activos.
    """

    exigir_admin_o_almacenero(
        current_user
    )

    return AuthService(
        db
    ).obtener_trabajadores()


# ============================================================
# LISTAR USUARIOS
# ============================================================

@router.get(
    "/usuarios",
    response_model=list[UserResponse],
    summary="Buscar y filtrar usuarios",
)
def listar_usuarios(
    db: DbDep,
    current_user: UserDep,
    role: str | None = Query(
        default=None
    ),
    estado_laboral: str | None = Query(
        default=None
    ),
    activo: bool | None = Query(
        default=None
    ),
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
):
    """
    Solamente admin puede listar todos los usuarios
    con filtros administrativos.
    """

    exigir_admin(
        current_user
    )

    # ========================================================
    # VALIDAR FILTRO ROLE
    # ========================================================

    if (
        role is not None
        and role not in ROLES_VALIDOS
    ):

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Filtro de rol no válido.",
        )

    # ========================================================
    # VALIDAR FILTRO ESTADO
    # ========================================================

    if (
        estado_laboral is not None
        and estado_laboral
        not in ESTADOS_LABORALES
    ):

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Filtro de estado laboral "
                "no válido."
            ),
        )

    return AuthService(
        db
    ).listar_usuarios(
        role=role,
        estado_laboral=estado_laboral,
        activo=activo,
        search=search,
    )


# ============================================================
# OBTENER USUARIO
# ============================================================

@router.get(
    "/usuario/{user_id}",
    response_model=UserResponse,
    summary="Consultar usuario por ID",
)
def obtener_usuario(
    user_id: int,
    db: DbDep,
    current_user: UserDep,
):
    """
    Solo admin puede consultar cualquier usuario por ID.
    """

    exigir_admin(
        current_user
    )

    try:

        return AuthService(
            db
        ).obtener_usuario(
            user_id
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc


# ============================================================
# ACTUALIZAR USUARIO ADMINISTRATIVO
# ============================================================

@router.put(
    "/usuario/{user_id}",
    response_model=UserResponse,
    summary=(
        "Actualizar datos administrativos "
        "del usuario"
    ),
)
def actualizar_usuario(
    user_id: int,
    data: UserAdminUpdate,
    db: DbDep,
    current_user: UserDep,
):
    """
    SOLO ADMIN.

    Permite modificar:

    - nombre
    - apellidos
    - tipo de documento
    - DNI
    - género
    - fecha de nacimiento
    - teléfono
    - teléfono secundario
    - dirección
    - cargo
    - área
    - fecha de ingreso
    - supervisor
    - código único
    - role
    - estado laboral
    - activo

    NO permite modificar:

    - email
    - password

    La foto y firma tienen endpoints independientes.
    """

    exigir_admin(
        current_user
    )

    service = AuthService(db)

    try:

        return service.actualizar_usuario(
            user_id=user_id,
            datos=data.model_dump(
                exclude_unset=True
            ),
            usuario_auditoria=obtener_id(
                current_user
            ),
            permitir_admin=True,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "El documento o código "
                "ya está registrado."
            ),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al actualizar usuario"
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al actualizar usuario.",
        ) from exc


# ============================================================
# FOTO DE OTRO USUARIO - ADMIN
# ============================================================

@router.post(
    "/usuario/{user_id}/foto",
    response_model=UserResponse,
    summary="Subir foto de un usuario",
)
async def subir_foto_usuario_admin(
    user_id: int,
    db: DbDep,
    current_user: UserDep,
    archivo: UploadFile = File(...),
):
    """
    SOLO ADMIN.

    Permite que un administrador suba o reemplace
    la fotografía de cualquier usuario.
    """

    exigir_admin(
        current_user
    )

    service = AuthService(db)

    try:

        # ====================================================
        # VALIDAR ARCHIVO
        # ====================================================

        if not archivo.filename:

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Debe seleccionar una imagen."
                ),
            )

        extension = (
            Path(
                archivo.filename
            ).suffix.lower()
        )

        extensiones_permitidas = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        if (
            extension
            not in extensiones_permitidas
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Formato de imagen no permitido. "
                    "Use JPG, JPEG, PNG o WEBP."
                ),
            )

        # ====================================================
        # LEER ARCHIVO
        # ====================================================

        contenido = await archivo.read()

        if not contenido:

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail="La imagen está vacía.",
            )

        # ====================================================
        # GUARDAR FOTO
        # ====================================================

        return service.guardar_foto_usuario(
            user_id=user_id,
            contenido=contenido,
            extension=extension,
            usuario_auditoria=obtener_id(
                current_user
            ),
        )

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al subir foto del usuario %s",
            user_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al guardar la foto.",
        ) from exc


# ============================================================
# FIRMA DE OTRO USUARIO - ADMIN
# ============================================================

@router.put(
    "/usuario/{user_id}/firma",
    response_model=UserResponse,
    summary="Guardar firma de un usuario",
)
def guardar_firma_usuario_admin(
    user_id: int,
    data: UserSignatureUpdate,
    db: DbDep,
    current_user: UserDep,
):
    """
    SOLO ADMIN.

    Permite que un administrador registre o reemplace
    la firma digital de cualquier usuario.
    """

    exigir_admin(
        current_user
    )

    service = AuthService(db)

    try:

        return service.guardar_firma_base64(
            user_id=user_id,
            firma_base64=data.firma_base64,
            usuario_auditoria=obtener_id(
                current_user
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al guardar firma del usuario %s",
            user_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al guardar la firma.",
        ) from exc


# ============================================================
# GENERAR IMAGEN DE FIRMA - ADMIN
# ============================================================

@router.post(
    "/usuario/{user_id}/firma/imagen",
    response_model=dict,
    summary="Convertir firma de usuario a PNG",
)
def generar_imagen_firma_usuario_admin(
    user_id: int,
    db: DbDep,
    current_user: UserDep,
):
    """
    SOLO ADMIN.

    Convierte la firma Base64 almacenada del usuario
    en un archivo PNG dentro de static/firmas.
    """

    exigir_admin(
        current_user
    )

    service = AuthService(db)

    try:

        url = service.generar_imagen_firma(
            user_id=user_id
        )

        return {
            "mensaje": (
                "Firma convertida correctamente."
            ),
            "firma_url": url,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Error al generar imagen de firma "
            "del usuario %s",
            user_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Error al generar la imagen de firma."
            ),
        ) from exc


# ============================================================
# CAMBIAR ESTADO
# ============================================================

@router.patch(
    "/usuario/{user_id}/estado",
    response_model=UserResponse,
    summary=(
        "Activar, suspender o dar de baja "
        "un usuario"
    ),
)
def cambiar_estado_usuario(
    user_id: int,
    data: UserStatusUpdate,
    db: DbDep,
    current_user: UserDep,
):
    """
    SOLO ADMIN.

    Permite:
    - activo
    - suspendido
    - cesado
    """

    exigir_admin(
        current_user
    )

    try:

        return AuthService(
            db
        ).cambiar_estado(
            user_id=user_id,
            activo=data.activo,
            estado_laboral=data.estado_laboral,
            usuario_auditoria=obtener_id(
                current_user
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al cambiar estado del usuario %s",
            user_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al cambiar estado.",
        ) from exc


# ============================================================
# ACTUALIZAR DATOS PERSONALES DE USUARIO
# ============================================================

@router.patch(
    "/usuario/{user_id}/datos",
    response_model=UserResponse,
    summary=(
        "Actualizar datos personales "
        "de un usuario"
    ),
)
def actualizar_datos_usuario(
    user_id: int,
    data: UserUpdate,
    db: DbDep,
    current_user: UserDep,
):
    """
    SOLO ADMIN.

    Esta ruta se conserva por compatibilidad.

    Permite modificar los datos contenidos en UserUpdate.

    No permite:
    - role
    - activo
    - estado_laboral
    - email
    - password

    Para modificar role, activo o estado laboral se utiliza
    PUT /auth/usuario/{user_id}.
    """

    exigir_admin(
        current_user
    )

    try:

        return AuthService(
            db
        ).actualizar_usuario(
            user_id=user_id,
            datos=data.model_dump(
                exclude_unset=True
            ),
            usuario_auditoria=obtener_id(
                current_user
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "El documento o código "
                "ya está registrado."
            ),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Error al actualizar datos "
            "del usuario %s",
            user_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Error al actualizar datos.",
        ) from exc