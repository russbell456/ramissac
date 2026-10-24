from typing import Annotated
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.vehiculo_service import VehiculoService
from app.schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate, VehiculoResponse
from app.schemas.jornada_transporte_schema import KilometrajeCorregir
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.jornada_transporte import JornadaTransporte
from app.models.jornada_transporte import IncidenciaRuta
from types import SimpleNamespace
from app.models.mantenimiento import Mantenimiento
from app.utils.vehiculo_report import estado_vigencia, generar_reporte_vehiculo

router = APIRouter(
    prefix="/api/vehiculos",
    tags=["Vehículos"],
    dependencies=[Depends(get_current_user)]
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

def require_transport_role(user: CurrentUserDep) -> User:
    if user.role not in {"admin", "conductor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para gestionar vehículos.")
    return user

def require_admin(user: CurrentUserDep) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acción exclusiva del administrador.")
    return user

@router.get("/", response_model=list[VehiculoResponse])
def listar_vehiculos(db: DbDep, _: Annotated[User, Depends(require_transport_role)]):
    service = VehiculoService(db)
    return service.get_all_vehiculos()

@router.get("/{id}", response_model=VehiculoResponse)
def obtener_vehiculo(id: int, db: DbDep, _: Annotated[User, Depends(require_transport_role)]):
    service = VehiculoService(db)
    return service.get_vehiculo_by_id(id)

@router.post("/", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(schema: VehiculoCreate, db: DbDep, _: Annotated[User, Depends(require_admin)]):
    service = VehiculoService(db)
    return service.create_vehiculo(schema)

@router.put("/{id}", response_model=VehiculoResponse)
def actualizar_vehiculo(id: int, schema: VehiculoUpdate, db: DbDep, _: Annotated[User, Depends(require_admin)]):
    service = VehiculoService(db)
    return service.update_vehiculo(id, schema)

@router.delete("/{id}")
def eliminar_vehiculo(id: int, db: DbDep, user: Annotated[User, Depends(require_admin)]):
    service = VehiculoService(db)
    return service.delete_vehiculo(id, user.id)

@router.post("/{id}/corregir-kilometraje", response_model=VehiculoResponse)
def corregir_kilometraje(id: int, data: KilometrajeCorregir, db: DbDep, user: Annotated[User, Depends(require_admin)]):
    return VehiculoService(db).corregir_kilometraje(id, data.kilometraje, data.motivo, user.id)

@router.get("/{id}/kilometraje", response_model=dict)
def obtener_kilometraje(id: int, db: DbDep, _: Annotated[User, Depends(require_transport_role)]):
    """Devuelve solo el kilometraje actual del vehículo para autocompletar formularios."""
    service = VehiculoService(db)
    vehiculo = service.get_vehiculo_by_id(id)
    return {
        "vehiculo_id": vehiculo.id,
        "kilometraje_actual": vehiculo.kilometraje_actual or 0.0,
        "placa": vehiculo.placa,
    }


@router.get("/{id}/vigencias", response_model=dict)
def obtener_vigencias(id: int, db: DbDep, _: Annotated[User, Depends(require_transport_role)]):
    vehiculo = VehiculoService(db).get_vehiculo_by_id(id)
    return {campo: estado_vigencia(getattr(vehiculo, campo)) for campo in (
        "soat_vencimiento", "rt_vencimiento", "poliza_vencimiento", "pase_minero_vencimiento"
    )}


@router.get("/{id}/reporte-pdf")
def reporte_pdf(
    id: int, db: DbDep, _: Annotated[User, Depends(require_transport_role)],
    estado: str = Query("pendientes", pattern="^(pendientes|todas)$"),
    desde: date | None = None, hasta: date | None = None,
):
    if desde and hasta and desde > hasta:
        raise HTTPException(400, 'El inicio del rango no puede ser posterior al fin.')
    vehiculo = VehiculoService(db).get_vehiculo_by_id(id)
    consulta = db.query(JornadaTransporte).filter(
        JornadaTransporte.vehiculo_id == id, JornadaTransporte.tiene_observaciones.is_(True)
    )
    if estado == "pendientes":
        consulta = consulta.filter(JornadaTransporte.observacion_resuelta.is_(False))
    if desde:
        consulta = consulta.filter(JornadaTransporte.fecha_inicio >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        consulta = consulta.filter(JornadaTransporte.fecha_inicio <= datetime.combine(hasta, datetime.max.time()))
    jornadas = consulta.order_by(JornadaTransporte.fecha_inicio.desc()).all()
    incidencias = db.query(IncidenciaRuta).join(JornadaTransporte).filter(JornadaTransporte.vehiculo_id == id)
    if estado == 'pendientes':
        incidencias = incidencias.filter(IncidenciaRuta.resuelta.is_(False))
    if desde:
        incidencias = incidencias.filter(IncidenciaRuta.fecha >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        incidencias = incidencias.filter(IncidenciaRuta.fecha <= datetime.combine(hasta, datetime.max.time()))
    for incidencia in incidencias.all():
        jornadas.append(SimpleNamespace(fecha_inicio=incidencia.fecha, conductor_id=incidencia.jornada.conductor_id,
            severidad=incidencia.severidad, observaciones=incidencia.descripcion,
            foto_observacion=incidencia.foto_incidencia, fotos_observacion=incidencia.fotos,
            observacion_resuelta=incidencia.resuelta))
    for jornada in jornadas:
        conductor = db.query(User).filter_by(id=jornada.conductor_id).first()
        jornada.conductor_nombre = f'{conductor.nombre} {conductor.apellidos}' if conductor else str(jornada.conductor_id)
    mantenimientos = db.query(Mantenimiento).filter(
        Mantenimiento.vehiculo_id == id, Mantenimiento.estado != "inactivo"
    ).order_by(Mantenimiento.fecha_ingreso.desc()).all()
    contenido = generar_reporte_vehiculo(vehiculo, jornadas, mantenimientos)
    return StreamingResponse(
        contenido, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="vehiculo-{vehiculo.placa}.pdf"'},
    )
