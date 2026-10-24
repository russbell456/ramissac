from __future__ import annotations
from sqlalchemy import Column, Date, Integer, String
from app.database.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)           # Ya existía
    apellidos = Column(String, nullable=False)        # Nuevo
    dni = Column(String, unique=True, nullable=False) # Nuevo (DNI único)
    cargo = Column(String, nullable=True)             # Nuevo (cargo del trabajador)
    codigo_unico = Column(String, unique=True, nullable=True) # Nuevo (código correlativo o personalizado)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column("rol", String, default="user")      # ← Mapea a la columna 'rol' en PostgreSQLA
    licencia_vencimiento = Column(Date, nullable=True)
    licencia_categoria = Column(String(20), nullable=True)
    emo_vencimiento = Column(Date, nullable=True)
    pase_minero_vencimiento = Column(Date, nullable=True)
    firma_url = Column(String(500), nullable=True)
