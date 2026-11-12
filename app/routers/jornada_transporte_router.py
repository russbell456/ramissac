from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.schemas.jornada_transporte_schema import (
    ChecklistCreate,
    ChecklistResponse,
    IncidenciaRutaCreate,
    IncidenciaRutaResponse,
    JornadaAsignacionCreate,
    RegistroAccionCreate,
    JornadaDetalleResponse,
    JornadaResponse,
    SubaccionCancelar,
    SubaccionCerrar,
)
from app.services.jornada_transporte_service import JornadaTransporteService

router = APIRouter(prefix="/api/jornadas", tags=["Gestión de Flota"])
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[JornadaResponse], include_in_schema=False)
@router.get("/", response_model=list[JornadaResponse])
def listar_jornadas(db: DbDep, user: UserDep):
    if user.role not in {'admin', 'conductor'}:
        raise HTTPException(403, 'No autorizado.')
    items = JornadaTransporteService(db).listar()
    return items if user.role == 'admin' else [j for j in items if j.conductor_id == user.id]


@router.post("/fotos", status_code=201)
async def subir_foto(user: UserDep, file: UploadFile = File(...)):
    if user.role not in {"conductor", "admin"}:
        raise HTTPException(403, "No tiene permiso para adjuntar evidencias.")
    contenido = await file.read(10 * 1024 * 1024 + 1)
    if len(contenido) > 10 * 1024 * 1024:
        raise HTTPException(413, "La fotografía no puede superar 10 MB.")
    from io import BytesIO
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(BytesIO(contenido)) as imagen:
            extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(imagen.format)
            if not extension or imagen.width * imagen.height > 25000000:
                raise HTTPException(400, "Use una imagen JPG, PNG o WebP de hasta 25 megapíxeles.")
            imagen.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400, "El archivo no es una imagen válida.")
    carpeta = Path("uploads/transportes")
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid4().hex}.{extension}"
    (carpeta / nombre).write_bytes(contenido)
    return {"url": f"/uploads/transportes/{nombre}"}


@router.get("/{jornada_id}", response_model=JornadaDetalleResponse)
def obtener_jornada(jornada_id: int, db: DbDep, user: UserDep):
    item = JornadaTransporteService(db).obtener(jornada_id)
    if user.role != 'admin' and (user.role != 'conductor' or item.conductor_id != user.id):
        raise HTTPException(403, 'No autorizado.')
    return item


@router.post("/asignar", response_model=JornadaResponse, status_code=status.HTTP_201_CREATED)
def asignar_vehiculo(data: JornadaAsignacionCreate, db: DbDep, user: UserDep):
    if user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo un administrador puede asignar vehículos.")
    return JornadaTransporteService(db).asignar(data)


@router.post("/registro-accion", response_model=JornadaResponse, status_code=status.HTTP_201_CREATED)
def registro_accion(data: RegistroAccionCreate, db: DbDep, user: UserDep):
    if user.role != "conductor":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo un conductor puede realizar el auto-registro.")
    return JornadaTransporteService(db).registrar_accion(user.id, data)


@router.post("/{jornada_id}/checklist-inicial", response_model=JornadaResponse)
def registrar_checklist_inicial(jornada_id: int, data: ChecklistCreate, db: DbDep, user: UserDep):
    return JornadaTransporteService(db).registrar_checklist_inicial(jornada_id, data, user.id)


@router.post("/{jornada_id}/checklist-final", response_model=JornadaResponse)
def registrar_checklist_final(jornada_id: int, data: ChecklistCreate, db: DbDep, user: UserDep):
    service = JornadaTransporteService(db)
    conductor_id = service.obtener(jornada_id).conductor_id if user.role == 'admin' else user.id
    return service.registrar_checklist_final(jornada_id, data, conductor_id, usuario_id=user.id)


@router.post("/{jornada_id}/incidencias", response_model=IncidenciaRutaResponse, status_code=status.HTTP_201_CREATED)
def registrar_incidencia(jornada_id: int, data: IncidenciaRutaCreate, db: DbDep, user: UserDep):
    return JornadaTransporteService(db).registrar_incidencia(jornada_id, data, user.id)


@router.post("/{jornada_id}/cerrar", response_model=JornadaResponse)
def cerrar_subaccion(jornada_id: int, data: SubaccionCerrar, db: DbDep, user: UserDep):
    return JornadaTransporteService(db).cerrar_subaccion(jornada_id, data, user)


@router.post("/{jornada_id}/cancelar", response_model=JornadaResponse)
def cancelar_subaccion(jornada_id: int, data: SubaccionCancelar, db: DbDep, user: UserDep):
    return JornadaTransporteService(db).cancelar_subaccion(jornada_id, data.motivo, user)
