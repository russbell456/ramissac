from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
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
)
from app.services.jornada_transporte_service import JornadaTransporteService

router = APIRouter(prefix="/api/jornadas", tags=["Gestión de Flota"])
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[User, Depends(get_current_user)]


@router.get("/", response_model=list[JornadaResponse])
def listar_jornadas(db: DbDep, _: UserDep):
    return JornadaTransporteService(db).listar()


@router.get("/{jornada_id}", response_model=JornadaDetalleResponse)
def obtener_jornada(jornada_id: int, db: DbDep, _: UserDep):
    return JornadaTransporteService(db).obtener(jornada_id)


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
    return JornadaTransporteService(db).registrar_checklist_final(jornada_id, data, user.id)


@router.post("/{jornada_id}/incidencias", response_model=IncidenciaRutaResponse, status_code=status.HTTP_201_CREATED)
def registrar_incidencia(jornada_id: int, data: IncidenciaRutaCreate, db: DbDep, user: UserDep):
    return JornadaTransporteService(db).registrar_incidencia(jornada_id, data, user.id)
