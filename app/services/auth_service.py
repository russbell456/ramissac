from __future__ import annotations

import base64
import binascii

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auditoria_service import AuditoriaService


# ============================================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================================

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15

# Roles válidos del ERP.
# Esta lista NO concede permisos.
ROLES_VALIDOS = {
    "user",
    "trabajador",
    "almacenero",
    "admin",
    "conductor",
    "ingeniero",
    "supervisor",
}

# Los nuevos roles no pueden registrarse públicamente.
PUBLIC_REGISTRATION_ROLES = {
    "user",
    "trabajador",
}

# Se conserva la clasificación existente.
# No se agregan conductor, ingeniero ni supervisor.
ROLES_ADMINISTRATIVOS = {
    "almacenero",
    "admin",
}

ESTADOS_LABORALES = {
    "activo",
    "suspendido",
    "cesado",
}

# Campos modificables por el flujo normal de usuarios.
CAMPOS_EDITABLES = {
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
    "foto_url",
}

# Exclusivos de la edición administrativa autorizada.
CAMPOS_ADMIN = {
    "role",
    "activo",
    "estado_laboral",
    "licencia_vencimiento",
    "licencia_categoria",
    "emo_vencimiento",
    "pase_minero_vencimiento",
}

# Campos que pueden borrarse enviando null explícito.
CAMPOS_ANULABLES = {
    "supervisor_id",
    "telefono",
    "telefono_secundario",
    "direccion",
    "foto_url",
    "cargo",
    "area",
    "licencia_vencimiento",
    "licencia_categoria",
    "emo_vencimiento",
    "pase_minero_vencimiento",
}

CAMPOS_AUDITORIA = (
    CAMPOS_EDITABLES
    | CAMPOS_ADMIN
    | {"foto_url"}
)

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
FIRMAS_DIR = STATIC_DIR / "firmas"
FOTOS_USUARIOS_DIR = STATIC_DIR / "fotos_usuarios"


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

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
        AuditoriaService(self.db).registrar(
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

        email = email.strip().lower()
        dni = dni.strip().upper()

        if codigo_unico is not None:
            codigo_unico = codigo_unico.strip() or None

        # Prohibir creación pública de roles especiales.
        if role not in PUBLIC_REGISTRATION_ROLES:
            raise ValueError(
                "El registro público solamente permite "
                "los roles user y trabajador."
            )

        if self.user_repo.get_by_email(email):
            raise ValueError(
                "El email ya está registrado"
            )

        if self.user_repo.get_by_document(dni):
            raise ValueError(
                "El documento ya está registrado"
            )

        if (
            codigo_unico
            and self.user_repo.get_by_codigo_unico(codigo_unico)
        ):
            raise ValueError(
                "El código interno ya está registrado"
            )

        if supervisor_id is not None:
            supervisor = self.user_repo.get_by_id(
                supervisor_id
            )

            if not supervisor or not supervisor.activo:
                raise ValueError(
                    "El supervisor no existe o está inactivo"
                )

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
            password=hash_password(password),
            codigo_unico=codigo_unico,
            role=role,
            estado_laboral="activo",
            activo=True,
        )

        return self.user_repo.create_user(user)

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

        # Mantener las restricciones del sistema actual.
        if (
            not user.activo
            or user.estado_laboral != "activo"
        ):
            return None

        ahora = datetime.now(timezone.utc)
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

        if not verify_password(
            password,
            user.password,
        ):
            user.intentos_fallidos += 1

            if user.intentos_fallidos >= MAX_INTENTOS:
                user.bloqueado_hasta = (
                    ahora
                    + timedelta(minutes=MINUTOS_BLOQUEO)
                )
                user.intentos_fallidos = 0

            self.user_repo.update_user(user)
            return None

        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        user.ultimo_acceso = ahora

        return self.user_repo.update_user(user)

    # ========================================================
    # TRABAJADORES
    # ========================================================

    def obtener_trabajadores(self) -> list[User]:
        """
        Integra conductor al listado utilizado por la
        rama del compañero.

        Se conservan los filtros de cuentas activas y
        estado laboral activo del sistema principal.

        Ingeniero y supervisor no se incluyen aquí
        automáticamente.
        """
        return (
            self.db.query(User)
            .filter(
                User.role.in_(
                    [
                        "trabajador",
                        "almacenero",
                        "conductor",
                    ]
                ),
                User.activo.is_(True),
                User.estado_laboral == "activo",
            )
            .order_by(User.apellidos.asc())
            .all()
        )

    # ========================================================
    # LISTADO GENERAL
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

        user = self.user_repo.get_by_id(user_id)

        if not user:
            raise ValueError(
                "Usuario no encontrado"
            )

        return user

    # ========================================================
    # ACTUALIZAR USUARIO
    # ========================================================

    def actualizar_usuario(
        self,
        user_id: int,
        datos: dict,
        usuario_auditoria: int,
        permitir_admin: bool = False,
    ) -> User:

        user = self.obtener_usuario(user_id)
        datos = dict(datos)

        # Preservar el correo como identificador inmutable.
        if "email" in datos:
            raise ValueError(
                "El correo electrónico no puede modificarse."
            )

        # La contraseña solo se modifica con su método propio.
        if "password" in datos:
            raise ValueError(
                "La contraseña no puede modificarse "
                "mediante la edición del usuario."
            )

        # No permitir modificación genérica de firmas.
        if (
            "firma_base64" in datos
            or "firma_url" in datos
        ):
            raise ValueError(
                "La firma debe modificarse mediante "
                "su flujo autorizado."
            )

        # Conservar la restricción de campos administrativos.
        # Los permisos efectivos deben verificarse en el router.
        if not permitir_admin:
            for campo in CAMPOS_ADMIN:
                datos.pop(campo, None)

        # Restringir el método a campos conocidos.
        # Evita cambios accidentales de columnas de seguridad.
        campos_permitidos = set(CAMPOS_EDITABLES)

        if permitir_admin:
            campos_permitidos |= CAMPOS_ADMIN

        campos_desconocidos = (
            set(datos) - campos_permitidos
        )

        if campos_desconocidos:
            raise ValueError(
                "Campos no permitidos para actualizar "
                "el usuario: "
                + ", ".join(sorted(campos_desconocidos))
            )

        # ----------------------------------------------------
        # DOCUMENTO
        # ----------------------------------------------------

        if (
            "dni" in datos
            and datos["dni"] is not None
        ):
            dni = str(datos["dni"]).strip().upper()

            if self.user_repo.document_exists(
                dni,
                user_id,
            ):
                raise ValueError(
                    "El documento ya está registrado"
                )

            datos["dni"] = dni

        # ----------------------------------------------------
        # CÓDIGO ÚNICO
        # ----------------------------------------------------

        if "codigo_unico" in datos:
            codigo = datos["codigo_unico"]

            if codigo is not None:
                codigo = str(codigo).strip() or None
                datos["codigo_unico"] = codigo

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

        # ----------------------------------------------------
        # SUPERVISOR
        # ----------------------------------------------------

        if "supervisor_id" in datos:
            supervisor_id = datos["supervisor_id"]

            if supervisor_id == user_id:
                raise ValueError(
                    "Un usuario no puede ser "
                    "su propio supervisor"
                )

            if supervisor_id is not None:
                supervisor = self.user_repo.get_by_id(
                    supervisor_id
                )

                if (
                    not supervisor
                    or not supervisor.activo
                ):
                    raise ValueError(
                        "El supervisor no existe "
                        "o está inactivo"
                    )

        # ----------------------------------------------------
        # ROL
        # ----------------------------------------------------

        if (
            "role" in datos
            and datos["role"] is not None
        ):
            if datos["role"] not in ROLES_VALIDOS:
                raise ValueError("Rol no válido")

        # ----------------------------------------------------
        # ESTADO LABORAL
        # ----------------------------------------------------

        if (
            "estado_laboral" in datos
            and datos["estado_laboral"] is not None
        ):
            if (
                datos["estado_laboral"]
                not in ESTADOS_LABORALES
            ):
                raise ValueError(
                    "Estado laboral no válido"
                )

        # ----------------------------------------------------
        # AUDITORÍA: VALORES ANTERIORES
        # ----------------------------------------------------

        valores_anteriores = {
            campo: getattr(user, campo)
            for campo in datos
            if campo in CAMPOS_AUDITORIA
        }

        # ----------------------------------------------------
        # APLICAR CAMBIOS
        # ----------------------------------------------------

        for campo, valor in datos.items():
            if (
                valor is not None
                or campo in CAMPOS_ANULABLES
            ):
                setattr(user, campo, valor)

        # ----------------------------------------------------
        # SINCRONIZAR ESTADO LABORAL
        # ----------------------------------------------------

        if (
            permitir_admin
            and datos.get("estado_laboral") is not None
        ):
            nuevo_estado = datos["estado_laboral"]

            if nuevo_estado == "cesado":
                user.fecha_baja = datetime.now(
                    timezone.utc
                ).date()
                user.activo = False

            elif nuevo_estado == "suspendido":
                user.activo = False

            elif nuevo_estado == "activo":
                user.fecha_baja = None

        # ----------------------------------------------------
        # PERSISTIR
        # ----------------------------------------------------

        self.user_repo.update_user(user)

        # ----------------------------------------------------
        # REGISTRAR AUDITORÍA
        # ----------------------------------------------------

        cambios = []

        for campo, valor_anterior in (
            valores_anteriores.items()
        ):
            valor_nuevo = getattr(user, campo)

            if valor_anterior != valor_nuevo:
                cambios.append(
                    f"{campo}: "
                    f"{valor_anterior!s} -> "
                    f"{valor_nuevo!s}"
                )

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

    def guardar_firma_base64(
        self,
        user_id: int,
        firma_base64: str,
        usuario_auditoria: int | None = None,
    ) -> User:

        user = self.obtener_usuario(user_id)

        if not firma_base64:
            raise ValueError(
                "La firma Base64 no puede estar vacía."
            )

        firma_limpia = firma_base64.strip()

        # Admitir el formato data:image/png;base64,...
        if "," in firma_limpia:
            encabezado, contenido = (
                firma_limpia.split(",", 1)
            )

            if "base64" not in encabezado.lower():
                raise ValueError(
                    "El formato de la firma no es válido."
                )

            firma_limpia = contenido.strip()

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

        firma_png = b"\x89PNG\r\n\x1a\n"

        if not datos.startswith(firma_png):
            raise ValueError(
                "La firma debe ser una imagen PNG válida."
            )

        tenia_firma = bool(user.firma_base64)

        # Conservar la firma almacenada en PostgreSQL.
        user.firma_base64 = firma_limpia
        self.user_repo.update_user(user)

        if usuario_auditoria is not None:
            descripcion = (
                "Se actualizó la firma digital del usuario."
                if tenia_firma
                else "Se registró una firma digital "
                     "para el usuario."
            )

            self._auditar(
                usuario_auditoria=usuario_auditoria,
                accion="ACTUALIZAR_FIRMA_USUARIO",
                entidad_id=user.id,
                descripcion=descripcion,
            )

        return user

    # ========================================================
    # GENERAR IMAGEN DE LA FIRMA
    # ========================================================

    def generar_imagen_firma(
        self,
        user_id: int,
    ) -> str:

        user = self.obtener_usuario(user_id)

        if not user.firma_base64:
            raise ValueError(
                "El usuario no tiene una firma registrada."
            )

        try:
            datos = base64.b64decode(
                user.firma_base64.strip(),
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

        if not datos.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            raise ValueError(
                "La firma almacenada no es un PNG válido."
            )

        FIRMAS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        nombre_archivo = (
            f"firma_usuario_{user.id}.png"
        )

        ruta_archivo = (
            FIRMAS_DIR / nombre_archivo
        )

        ruta_archivo.write_bytes(datos)

        return (
            f"/static/firmas/{nombre_archivo}"
        )

    # ========================================================
    # GUARDAR FOTO DE USUARIO
    # ========================================================

    def guardar_foto_usuario(
        self,
        user_id: int,
        contenido: bytes,
        extension: str,
        usuario_auditoria: int | None = None,
    ) -> User:

        user = self.obtener_usuario(user_id)

        if not contenido:
            raise ValueError(
                "La foto está vacía."
            )

        extension = extension.lower().strip()

        extensiones_permitidas = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        if extension not in extensiones_permitidas:
            raise ValueError(
                "Formato de imagen no permitido. "
                "Use JPG, JPEG, PNG o WEBP."
            )

        FOTOS_USUARIOS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        foto_anterior = user.foto_url

        nombre_archivo = (
            f"usuario_{user.id}{extension}"
        )

        ruta_archivo = (
            FOTOS_USUARIOS_DIR / nombre_archivo
        )

        # Conservar el comportamiento de reemplazo
        # de fotos utilizado por el servicio actual.
        if user.foto_url:
            nombre_anterior = (
                user.foto_url
                .rstrip("/")
                .split("/")[-1]
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

        ruta_archivo.write_bytes(contenido)

        user.foto_url = (
            f"/static/fotos_usuarios/{nombre_archivo}"
        )

        self.user_repo.update_user(user)

        if usuario_auditoria is not None:
            descripcion = (
                "Se actualizó la foto del usuario."
                if foto_anterior
                else "Se registró una foto para el usuario."
            )

            self._auditar(
                usuario_auditoria=usuario_auditoria,
                accion="ACTUALIZAR_FOTO_USUARIO",
                entidad_id=user.id,
                descripcion=descripcion,
            )

        return user

    # ========================================================
    # CAMBIAR ESTADO DE USUARIO
    # ========================================================

    def cambiar_estado(
        self,
        user_id: int,
        activo: bool,
        estado_laboral: str,
        usuario_auditoria: int,
    ) -> User:

        user = self.obtener_usuario(user_id)

        if estado_laboral not in ESTADOS_LABORALES:
            raise ValueError(
                "Estado laboral no válido"
            )

        estado_anterior = user.estado_laboral
        activo_anterior = user.activo
        fecha_baja_anterior = user.fecha_baja

        if estado_laboral == "cesado":
            user.fecha_baja = datetime.now(
                timezone.utc
            ).date()
            user.activo = False
        else:
            user.activo = activo

        if estado_laboral == "suspendido":
            user.activo = False

        if estado_laboral == "activo":
            user.fecha_baja = None

        user.estado_laboral = estado_laboral

        self.user_repo.update_user(user)

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
    # CAMBIAR CONTRASEÑA
    # ========================================================

    def cambiar_password(
        self,
        user_id: int,
        password_actual: str,
        password_nueva: str,
    ) -> None:

        user = self.obtener_usuario(user_id)

        if not verify_password(
            password_actual,
            user.password,
        ):
            raise ValueError(
                "La contraseña actual es incorrecta"
            )

        if password_actual == password_nueva:
            raise ValueError(
                "La nueva contraseña debe ser diferente"
            )

        user.password = hash_password(
            password_nueva
        )

        self.user_repo.update_user(user)
