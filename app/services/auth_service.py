from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auditoria_service import AuditoriaService
from app.core.security import (
    hash_password,
    verify_password,
)


# ============================================================
# CONFIGURACIÓN DE LOGIN
# ============================================================

MAX_INTENTOS = 5

MINUTOS_BLOQUEO = 15


# ============================================================
# ROLES DEL SISTEMA
# ============================================================

ROLES_VALIDOS = {
    "user",
    "trabajador",
    "almacenero",
    "admin",
}


# Roles permitidos durante el registro público.
#
# IMPORTANTE:
# admin y almacenero NO pueden crearse mediante
# el registro público.
PUBLIC_REGISTRATION_ROLES = {
    "user",
    "trabajador",
}


ROLES_ADMINISTRATIVOS = {
    "almacenero",
    "admin",
}


# ============================================================
# ESTADOS LABORALES
# ============================================================

ESTADOS_LABORALES = {
    "activo",
    "suspendido",
    "cesado",
}


# ============================================================
# DIRECTORIOS LOCALES
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parents[2]

STATIC_DIR = BASE_DIR / "static"

FIRMAS_DIR = (
    STATIC_DIR / "firmas"
)

FOTOS_USUARIOS_DIR = (
    STATIC_DIR / "fotos_usuarios"
)


class AuthService:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

        self.user_repo = UserRepository(
            db
        )

    # ========================================================
    # AUDITORÍA
    # ========================================================

    def _auditar(
        self,
        usuario_auditoria: int,
        accion: str,
        entidad_id: int,
        descripcion: str,
    ) -> None:

        AuditoriaService(
            self.db
        ).registrar(
            usuario_id=usuario_auditoria,
            accion=accion,
            entidad="users",
            entidad_id=entidad_id,
            descripcion=descripcion,
        )

    # ========================================================
    # REGISTRO PÚBLICO
    # ========================================================

    def register_user(
        self,
        *,
        nombre: str,
        apellidos: str,
        tipo_documento: str,
        dni: str,
        genero: str | None,
        fecha_nacimiento,
        telefono: str | None,
        telefono_secundario: str | None,
        direccion: str | None,
        cargo: str | None,
        area: str | None,
        fecha_ingreso,
        supervisor_id: int | None,
        email: str,
        password: str,
        codigo_unico: str | None,
        role: str = "user",
    ) -> User:

        email = (
            email
            .strip()
            .lower()
        )

        dni = (
            dni
            .strip()
            .upper()
        )

        if codigo_unico is not None:
            codigo_unico = (
                codigo_unico
                .strip()
            )

            if not codigo_unico:
                codigo_unico = None

        # ====================================================
        # SEGURIDAD PRINCIPAL DEL REGISTRO
        # ====================================================

        if role not in PUBLIC_REGISTRATION_ROLES:
            raise ValueError(
                "El registro público solamente "
                "permite los roles user y trabajador."
            )

        # ====================================================
        # EMAIL
        # ====================================================

        if self.user_repo.get_by_email(
            email
        ):
            raise ValueError(
                "El email ya está registrado"
            )

        # ====================================================
        # DOCUMENTO
        # ====================================================

        if self.user_repo.get_by_document(
            dni
        ):
            raise ValueError(
                "El documento ya está registrado"
            )

        # ====================================================
        # CÓDIGO ÚNICO
        # ====================================================

        if (
            codigo_unico
            and self.user_repo.get_by_codigo_unico(
                codigo_unico
            )
        ):
            raise ValueError(
                "El código interno ya está registrado"
            )

        # ====================================================
        # SUPERVISOR
        # ====================================================

        if supervisor_id is not None:

            supervisor = (
                self.user_repo.get_by_id(
                    supervisor_id
                )
            )

            if (
                not supervisor
                or not supervisor.activo
            ):
                raise ValueError(
                    "El supervisor no existe o está inactivo"
                )

        # ====================================================
        # CREAR USUARIO
        # ====================================================

        user = User(
            nombre=nombre,
            apellidos=apellidos,
            tipo_documento=tipo_documento,
            dni=dni,
            genero=genero,
            fecha_nacimiento=fecha_nacimiento,
            telefono=telefono,
            telefono_secundario=telefono_secundario,
            direccion=direccion,
            cargo=cargo,
            area=area,
            fecha_ingreso=fecha_ingreso,
            supervisor_id=supervisor_id,
            email=email,
            password=hash_password(
                password
            ),
            codigo_unico=codigo_unico,
            role=role,
            estado_laboral="activo",
            activo=True,
        )

        return self.user_repo.create_user(
            user
        )

    # ========================================================
    # AUTENTICACIÓN
    # ========================================================

    def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> User | None:

        user = self.user_repo.get_by_email(
            email.strip().lower()
        )

        if not user:
            return None

        if (
            not user.activo
            or user.estado_laboral != "activo"
        ):
            return None

        ahora = datetime.now(
            timezone.utc
        )

        bloqueo = user.bloqueado_hasta

        if bloqueo is not None:

            if bloqueo.tzinfo is None:
                bloqueo = bloqueo.replace(
                    tzinfo=timezone.utc
                )

            if bloqueo > ahora:
                return None

            user.bloqueado_hasta = None
            user.intentos_fallidos = 0

        # ====================================================
        # PASSWORD INCORRECTO
        # ====================================================

        if not verify_password(
            password,
            user.password,
        ):

            user.intentos_fallidos += 1

            if (
                user.intentos_fallidos
                >= MAX_INTENTOS
            ):

                user.bloqueado_hasta = (
                    ahora
                    + timedelta(
                        minutes=MINUTOS_BLOQUEO
                    )
                )

                user.intentos_fallidos = 0

            self.user_repo.update_user(
                user
            )

            return None

        # ====================================================
        # LOGIN CORRECTO
        # ====================================================

        user.intentos_fallidos = 0

        user.bloqueado_hasta = None

        user.ultimo_acceso = ahora

        return self.user_repo.update_user(
            user
        )

    # ========================================================
    # TRABAJADORES
    # ========================================================

    def obtener_trabajadores(
        self,
    ) -> list[User]:

        return (
            self.user_repo
            .list_trabajadores()
        )

    # ========================================================
    # LISTAR USUARIOS
    # ========================================================

    def listar_usuarios(
        self,
        role: str | None = None,
        estado_laboral: str | None = None,
        activo: bool | None = None,
        search: str | None = None,
    ) -> list[User]:

        return self.user_repo.list_users(
            role=role,
            estado_laboral=estado_laboral,
            activo=activo,
            search=search,
        )

    # ========================================================
    # OBTENER USUARIO
    # ========================================================

    def obtener_usuario(
        self,
        user_id: int,
    ) -> User:

        user = self.user_repo.get_by_id(
            user_id
        )

        if not user:
            raise ValueError(
                "Usuario no encontrado"
            )

        return user

    # ========================================================
    # ACTUALIZAR USUARIO
    # ========================================================
    #
    # Este método sirve tanto para:
    #
    # 1. Actualización normal.
    # 2. Actualización administrativa.
    #
    # permitir_admin=False:
    #   No permite role, activo ni estado_laboral.
    #
    # permitir_admin=True:
    #   Permite esos campos.
    #
    # IMPORTANTE:
    #
    # - EMAIL ES INMUTABLE.
    # - PASSWORD NO SE MODIFICA AQUÍ.
    # - FIRMA SE MODIFICA POR SU MÉTODO PROPIO.
    # - FOTO SE PUEDE MODIFICAR POR SU MÉTODO PROPIO.
    #
    # ========================================================

    def actualizar_usuario(
        self,
        user_id: int,
        datos: dict,
        usuario_auditoria: int,
        permitir_admin: bool = False,
    ) -> User:

        user = self.obtener_usuario(
            user_id
        )

        # Crear una copia para no modificar
        # accidentalmente el diccionario recibido
        # desde el router.
        datos = dict(datos)

        # ====================================================
        # PROTECCIÓN DEL EMAIL
        # ====================================================
        #
        # El email es el identificador de acceso.
        # No se permite modificarlo desde este método.
        #
        # Esto también protege el caso en que una petición
        # antigua todavía envíe el campo "email".
        # ====================================================

        if "email" in datos:

            raise ValueError(
                "El correo electrónico no puede modificarse."
            )

        # ====================================================
        # PROTECCIÓN DE PASSWORD
        # ====================================================
        #
        # La contraseña solamente se modifica mediante:
        #
        # cambiar_password()
        #
        # Nunca mediante la edición administrativa.
        # ====================================================

        if "password" in datos:

            raise ValueError(
                "La contraseña no puede modificarse "
                "mediante la edición del usuario."
            )

        # ====================================================
        # DOCUMENTO
        # ====================================================

        if (
            "dni" in datos
            and datos["dni"] is not None
        ):

            dni = (
                str(datos["dni"])
                .strip()
                .upper()
            )

            if self.user_repo.document_exists(
                dni,
                user_id,
            ):
                raise ValueError(
                    "El documento ya está registrado"
                )

            datos["dni"] = dni

        # ====================================================
        # CÓDIGO ÚNICO
        # ====================================================

        if "codigo_unico" in datos:

            codigo = datos[
                "codigo_unico"
            ]

            if codigo is not None:

                codigo = (
                    str(codigo)
                    .strip()
                )

                if not codigo:
                    codigo = None

                datos["codigo_unico"] = (
                    codigo
                )

                if (
                    codigo
                    and self.user_repo.codigo_exists(
                        codigo,
                        user_id,
                    )
                ):
                    raise ValueError(
                        "El código interno ya está registrado"
                    )

        # ====================================================
        # SUPERVISOR
        # ====================================================

        if "supervisor_id" in datos:

            supervisor_id = (
                datos["supervisor_id"]
            )

            if supervisor_id == user_id:

                raise ValueError(
                    "Un usuario no puede ser "
                    "su propio supervisor"
                )

            if supervisor_id is not None:

                supervisor = (
                    self.user_repo.get_by_id(
                        supervisor_id
                    )
                )

                if (
                    not supervisor
                    or not supervisor.activo
                ):
                    raise ValueError(
                        "El supervisor no existe "
                        "o está inactivo"
                    )

        # ====================================================
        # PROTECCIÓN DE CAMPOS ADMINISTRATIVOS
        # ====================================================

        if not permitir_admin:

            datos.pop(
                "role",
                None,
            )

            datos.pop(
                "activo",
                None,
            )

            datos.pop(
                "estado_laboral",
                None,
            )

        # ====================================================
        # VALIDACIÓN DEL ROLE
        # ====================================================

        if (
            "role" in datos
            and datos["role"] is not None
        ):

            nuevo_role = datos[
                "role"
            ]

            if nuevo_role not in ROLES_VALIDOS:

                raise ValueError(
                    "Rol no válido"
                )

        # ====================================================
        # VALIDACIÓN DEL ESTADO LABORAL
        # ====================================================

        if (
            "estado_laboral" in datos
            and datos["estado_laboral"]
            is not None
        ):

            nuevo_estado = datos[
                "estado_laboral"
            ]

            if (
                nuevo_estado
                not in ESTADOS_LABORALES
            ):

                raise ValueError(
                    "Estado laboral no válido"
                )

        # ====================================================
        # GUARDAR VALORES ANTERIORES
        # ====================================================
        #
        # Se guardan antes de modificar el usuario para que
        # la auditoría pueda indicar qué cambió.
        #
        # No incluimos:
        # - password
        # - firma_base64
        #
        # para evitar almacenar información sensible
        # en la auditoría.
        # ====================================================

        campos_auditoria = {
            "nombre",
            "apellidos",
            "tipo_documento",
            "dni",
            "genero",
            "fecha_nacimiento",
            "telefono",
            "telefono_secundario",
            "direccion",
            "cargo",
            "area",
            "fecha_ingreso",
            "supervisor_id",
            "codigo_unico",
            "role",
            "estado_laboral",
            "activo",
            "foto_url",
        }

        valores_anteriores = {
            campo: getattr(
                user,
                campo,
                None,
            )
            for campo in datos
            if campo in campos_auditoria
        }

        # ====================================================
        # APLICAR CAMBIOS
        # ====================================================

        for campo, valor in datos.items():

            # Nunca modificar password desde este método.
            if campo == "password":
                continue

            # Nunca modificar email desde este método.
            if campo == "email":
                continue

            if (
                valor is not None
                or campo in {
                    "supervisor_id",
                    "telefono",
                    "telefono_secundario",
                    "direccion",
                    "foto_url",
                    "cargo",
                    "area",
                }
            ):

                if hasattr(
                    user,
                    campo,
                ):

                    setattr(
                        user,
                        campo,
                        valor,
                    )

        # ====================================================
        # SINCRONIZAR ESTADO LABORAL
        # ====================================================
        #
        # Si el admin cambia el estado laboral:
        #
        # activo:
        #   fecha_baja = None
        #
        # suspendido:
        #   activo = False
        #
        # cesado:
        #   activo = False
        #   fecha_baja = fecha actual
        #
        # Si el admin NO modifica estado_laboral, no tocamos
        # la fecha de baja automáticamente.
        # ====================================================

        if (
            permitir_admin
            and "estado_laboral" in datos
            and datos["estado_laboral"]
            is not None
        ):

            nuevo_estado = (
                datos["estado_laboral"]
            )

            if nuevo_estado == "cesado":

                user.fecha_baja = (
                    datetime.now(
                        timezone.utc
                    ).date()
                )

                user.activo = False

            elif nuevo_estado == "suspendido":

                user.activo = False

            elif nuevo_estado == "activo":

                user.fecha_baja = None

        # ====================================================
        # GUARDAR EN BASE DE DATOS
        # ====================================================

        self.user_repo.update_user(
            user
        )

        # ====================================================
        # CONSTRUIR AUDITORÍA DE CAMBIOS
        # ====================================================

        cambios = []

        for campo, valor_anterior in (
            valores_anteriores.items()
        ):

            valor_nuevo = getattr(
                user,
                campo,
                None,
            )

            if valor_anterior != valor_nuevo:

                cambios.append(
                    f"{campo}: "
                    f"{valor_anterior!s} -> "
                    f"{valor_nuevo!s}"
                )

        # ====================================================
        # AUDITORÍA
        # ====================================================

        if cambios:

            descripcion = (
                "Se actualizaron datos del usuario. "
                + "; ".join(cambios)
            )

        else:

            descripcion = (
                "Se ejecutó una actualización "
                "del usuario sin cambios en los "
                "campos auditables."
            )

        self._auditar(
            usuario_auditoria=usuario_auditoria,
            accion="EDITAR_USUARIO",
            entidad_id=user.id,
            descripcion=descripcion,
        )

        return user

    # ========================================================
    # GUARDAR FIRMA BASE64
    # ========================================================
    #
    # Puede utilizarse tanto por:
    #
    # - el propio usuario
    # - un administrador
    #
    # Cuando usuario_auditoria se proporciona, se registra
    # la modificación en auditoría.
    #
    # Nunca se guarda el Base64 de la firma en la auditoría.
    # ========================================================

    def guardar_firma_base64(
        self,
        user_id: int,
        firma_base64: str,
        usuario_auditoria: int | None = None,
    ) -> User:

        user = self.obtener_usuario(
            user_id
        )

        if not firma_base64:

            raise ValueError(
                "La firma Base64 no puede estar vacía."
            )

        firma_limpia = (
            firma_base64.strip()
        )

        # ====================================================
        # SOPORTAR DATA URL
        # ====================================================
        #
        # Ejemplo:
        #
        # data:image/png;base64,iVBORw0...
        #
        # Se almacena solamente el contenido Base64.
        # ====================================================

        if "," in firma_limpia:

            encabezado, contenido = (
                firma_limpia.split(
                    ",",
                    1,
                )
            )

            if (
                "base64"
                not in encabezado.lower()
            ):

                raise ValueError(
                    "El formato de la firma no es válido."
                )

            firma_limpia = (
                contenido.strip()
            )

        # ====================================================
        # VALIDAR BASE64
        # ====================================================

        try:

            datos = base64.b64decode(
                firma_limpia,
                validate=True,
            )

        except (
            ValueError,
            binascii.Error,
        ) as exc:

            raise ValueError(
                "La firma no contiene un Base64 válido."
            ) from exc

        if not datos:

            raise ValueError(
                "La firma Base64 está vacía."
            )

        # ====================================================
        # VALIDAR PNG
        # ====================================================

        firma_png = (
            b"\x89PNG\r\n\x1a\n"
        )

        if not datos.startswith(
            firma_png
        ):

            raise ValueError(
                "La firma debe ser una imagen PNG válida."
            )

        # ====================================================
        # SABER SI YA EXISTÍA FIRMA
        # ====================================================

        tenia_firma = bool(
            user.firma_base64
        )

        # ====================================================
        # GUARDAR BASE64 EN BD
        # ====================================================

        user.firma_base64 = (
            firma_limpia
        )

        self.user_repo.update_user(
            user
        )

        # ====================================================
        # AUDITORÍA OPCIONAL
        # ====================================================

        if usuario_auditoria is not None:

            accion = (
                "ACTUALIZAR_FIRMA_USUARIO"
            )

            if tenia_firma:

                descripcion = (
                    "Se actualizó la firma "
                    "digital del usuario."
                )

            else:

                descripcion = (
                    "Se registró una firma "
                    "digital para el usuario."
                )

            self._auditar(
                usuario_auditoria=(
                    usuario_auditoria
                ),
                accion=accion,
                entidad_id=user.id,
                descripcion=descripcion,
            )

        return user

    # ========================================================
    # CONVERTIR FIRMA BASE64 A PNG
    # ========================================================

    def generar_imagen_firma(
        self,
        user_id: int,
    ) -> str:

        user = self.obtener_usuario(
            user_id
        )

        if not user.firma_base64:

            raise ValueError(
                "El usuario no tiene una firma registrada."
            )

        firma_base64 = (
            user.firma_base64.strip()
        )

        try:

            datos = base64.b64decode(
                firma_base64,
                validate=True,
            )

        except (
            ValueError,
            binascii.Error,
        ) as exc:

            raise ValueError(
                "La firma almacenada no contiene "
                "un Base64 válido."
            ) from exc

        firma_png = (
            b"\x89PNG\r\n\x1a\n"
        )

        if not datos.startswith(
            firma_png
        ):

            raise ValueError(
                "La firma almacenada no es un PNG válido."
            )

        # ====================================================
        # CREAR DIRECTORIO
        # ====================================================

        FIRMAS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ====================================================
        # NOMBRE DEL ARCHIVO
        # ====================================================

        nombre_archivo = (
            f"firma_usuario_{user.id}.png"
        )

        ruta_archivo = (
            FIRMAS_DIR
            / nombre_archivo
        )

        # ====================================================
        # ESCRIBIR IMAGEN
        # ====================================================

        ruta_archivo.write_bytes(
            datos
        )

        return (
            f"/static/firmas/{nombre_archivo}"
        )

    # ========================================================
    # GUARDAR FOTO LOCAL
    # ========================================================
    #
    # Puede utilizarse tanto para:
    #
    # - usuario propio
    # - administrador
    #
    # Si usuario_auditoria se proporciona, se registra
    # el cambio.
    # ========================================================

    def guardar_foto_usuario(
        self,
        user_id: int,
        contenido: bytes,
        extension: str,
        usuario_auditoria: int | None = None,
    ) -> User:

        user = self.obtener_usuario(
            user_id
        )

        if not contenido:

            raise ValueError(
                "La foto está vacía."
            )

        extension = (
            extension.lower()
            .strip()
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

            raise ValueError(
                "Formato de imagen no permitido. "
                "Use JPG, JPEG, PNG o WEBP."
            )

        # ====================================================
        # CREAR DIRECTORIO
        # ====================================================

        FOTOS_USUARIOS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ====================================================
        # GUARDAR REFERENCIA ANTERIOR
        # ====================================================

        foto_anterior = (
            user.foto_url
        )

        # ====================================================
        # NOMBRE DEL ARCHIVO
        # ====================================================

        nombre_archivo = (
            f"usuario_{user.id}{extension}"
        )

        ruta_archivo = (
            FOTOS_USUARIOS_DIR
            / nombre_archivo
        )

        # ====================================================
        # ELIMINAR FOTO ANTERIOR
        # ====================================================

        if user.foto_url:

            nombre_anterior = (
                user.foto_url
                .rstrip("/")
                .split("/")
                [-1]
            )

            ruta_anterior = (
                FOTOS_USUARIOS_DIR
                / nombre_anterior
            )

            if (
                ruta_anterior.exists()
                and ruta_anterior != ruta_archivo
            ):

                ruta_anterior.unlink()

        # ====================================================
        # GUARDAR NUEVA FOTO
        # ====================================================

        ruta_archivo.write_bytes(
            contenido
        )

        # ====================================================
        # GUARDAR SOLAMENTE URL EN BD
        # ====================================================

        user.foto_url = (
            f"/static/fotos_usuarios/"
            f"{nombre_archivo}"
        )

        self.user_repo.update_user(
            user
        )

        # ====================================================
        # AUDITORÍA OPCIONAL
        # ====================================================

        if usuario_auditoria is not None:

            if foto_anterior:

                descripcion = (
                    "Se actualizó la foto "
                    "del usuario."
                )

            else:

                descripcion = (
                    "Se registró una foto "
                    "para el usuario."
                )

            self._auditar(
                usuario_auditoria=(
                    usuario_auditoria
                ),
                accion="ACTUALIZAR_FOTO_USUARIO",
                entidad_id=user.id,
                descripcion=descripcion,
            )

        return user

    # ========================================================
    # CAMBIAR ESTADO
    # ========================================================

    def cambiar_estado(
        self,
        user_id: int,
        activo: bool,
        estado_laboral: str,
        usuario_auditoria: int,
    ) -> User:

        user = self.obtener_usuario(
            user_id
        )

        if (
            estado_laboral
            not in ESTADOS_LABORALES
        ):

            raise ValueError(
                "Estado laboral no válido"
            )

        estado_anterior = (
            user.estado_laboral
        )

        activo_anterior = (
            user.activo
        )

        fecha_baja_anterior = (
            user.fecha_baja
        )

        # ====================================================
        # CESADO
        # ====================================================

        if estado_laboral == "cesado":

            user.fecha_baja = (
                datetime.now(
                    timezone.utc
                ).date()
            )

            user.activo = False

        # ====================================================
        # OTROS ESTADOS
        # ====================================================

        else:

            user.activo = activo

        # ====================================================
        # SUSPENDIDO
        # ====================================================

        if estado_laboral == "suspendido":

            user.activo = False

        # ====================================================
        # ACTIVO
        # ====================================================

        if estado_laboral == "activo":

            user.fecha_baja = None

        user.estado_laboral = (
            estado_laboral
        )

        self.user_repo.update_user(
            user
        )

        # ====================================================
        # AUDITORÍA
        # ====================================================

        self._auditar(
            usuario_auditoria=usuario_auditoria,
            accion="CAMBIAR_ESTADO_USUARIO",
            entidad_id=user.id,
            descripcion=(
                f"Estado laboral: "
                f"{estado_anterior} -> "
                f"{user.estado_laboral}; "
                f"cuenta activa: "
                f"{activo_anterior} -> "
                f"{user.activo}; "
                f"fecha de baja: "
                f"{fecha_baja_anterior} -> "
                f"{user.fecha_baja}"
            ),
        )

        return user

    # ========================================================
    # CAMBIAR PASSWORD
    # ========================================================

    def cambiar_password(
        self,
        user_id: int,
        password_actual: str,
        password_nueva: str,
    ) -> None:

        user = self.obtener_usuario(
            user_id
        )

        if not verify_password(
            password_actual,
            user.password,
        ):

            raise ValueError(
                "La contraseña actual es incorrecta"
            )

        if (
            password_actual
            == password_nueva
        ):

            raise ValueError(
                "La nueva contraseña debe ser diferente"
            )

        user.password = hash_password(
            password_nueva
        )

        self.user_repo.update_user(
            user
        )