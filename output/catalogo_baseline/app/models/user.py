from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    codigo_unico = Column(
        String(30),
        unique=True,
        nullable=True,
        index=True,
    )

    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(150), nullable=False)

    tipo_documento = Column(
        String(20),
        nullable=False,
        default="DNI",
    )

    dni = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    genero = Column(
        String(30),
        nullable=True,
    )

    fecha_nacimiento = Column(
        Date,
        nullable=True,
    )

    telefono = Column(
        String(20),
        nullable=True,
    )

    telefono_secundario = Column(
        String(20),
        nullable=True,
    )

    direccion = Column(
        String(250),
        nullable=True,
    )

    email = Column(
        String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    # =========================================================
    # FOTO DEL USUARIO
    # =========================================================
    #
    # En PostgreSQL solamente se guarda la URL/ruta.
    #
    # Ejemplo:
    #
    # /static/fotos_usuarios/usuario_25.png
    #
    foto_url = Column(
        String(500),
        nullable=True,
    )

    # =========================================================
    # FIRMA DIGITAL
    # =========================================================
    #
    # La firma se almacena como Base64 directamente
    # en PostgreSQL.
    #
    # El archivo PNG generado a partir del Base64
    # se almacena físicamente en:
    #
    # static/firmas/
    #
    firma_base64 = Column(
        Text,
        nullable=True,
    )

    cargo = Column(
        String(100),
        nullable=True,
    )

    area = Column(
        String(100),
        nullable=True,
    )

    fecha_ingreso = Column(
        Date,
        nullable=True,
    )

    fecha_baja = Column(
        Date,
        nullable=True,
    )

    estado_laboral = Column(
        String(20),
        nullable=False,
        default="activo",
    )

    supervisor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    supervisor = relationship(
        "User",
        remote_side=[id],
        foreign_keys=[supervisor_id],
    )

    password = Column(
        String(255),
        nullable=False,
    )

    role = Column(
        "rol",
        String(30),
        nullable=False,
        default="trabajador",
        index=True,
    )

    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    intentos_fallidos = Column(
        Integer,
        nullable=False,
        default=0,
    )

    bloqueado_hasta = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    ultimo_acceso = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_creacion = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_actualizacion = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )