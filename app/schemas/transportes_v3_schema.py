from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr

Imagen = Annotated[str, Field(pattern=r'^/uploads/transportes/[a-f0-9]+\.(jpg|png|webp)$', max_length=500)]


class DocumentoCrear(BaseModel):
    licencia_categoria: str | None = Field(None, max_length=20)
    tipo: str = Field(min_length=2, max_length=50)
    archivo_url: str = Field(pattern=r'^/uploads/transportes/[a-f0-9]+\.(jpg|png|webp|pdf)$', max_length=500)
    fecha_vencimiento: date | None = None


class DocumentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entidad: str
    entidad_id: int
    tipo: str
    archivo_url: str | None
    fecha_vencimiento: date | None
    estado: str
    version: int
    archivado: bool


class ResolverObservacion(BaseModel):
    descripcion: str = Field(min_length=10, max_length=4000)
    foto_url: Imagen


class DispositivoCrear(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class FirmaActualizar(BaseModel):
    firma_url: Imagen


class ConductorRapido(BaseModel):
    nombre: str = Field(min_length=2)
    apellidos: str = Field(default='', max_length=150)
    dni: str = Field(pattern=r'^\d{8}$')


class DocumentoRevision(BaseModel):
    estado: Literal['aprobado', 'rechazado']
    motivo: str = Field(default='', max_length=2000)


class ConductorAcceso(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
