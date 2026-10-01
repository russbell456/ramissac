from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.mantenimiento import Mantenimiento
from app.models.user import User
from app.schemas.mantenimiento_schema import MantenimientoCreate, MantenimientoUpdate, MantenimientoResponse
from app.services.mantenimiento_service import MantenimientoService
from app.models.vehiculo import Vehiculo
from app.schemas.jornada_transporte_schema import MantenimientoAlertaResponse

router = APIRouter(prefix="/api/mantenimientos", tags=["Mantenimiento"])
DbDep = Annotated[Session, Depends(get_db)]


def require_reader(user: User = Depends(get_current_user)) -> User:
    if user.role not in ["admin", "trabajador"]:
        raise HTTPException(status_code=403, detail="No autorizado.")
    return user


def require_manager(user: User = Depends(get_current_user)) -> User:
    if user.role not in ["admin", "trabajador"]:
        raise HTTPException(status_code=403, detail="No autorizado para gestionar mantenimientos.")
    return user


@router.get("/reportes/vencidos", response_model=list[MantenimientoResponse])
def mantenimientos_vencidos(db: DbDep, _: User = Depends(require_manager)):
    return db.query(Mantenimiento).filter(
        Mantenimiento.descripcion_trabajo.like("%VENCIDO%"),
        Mantenimiento.fecha_baja.is_(None),
    ).all()


@router.get("/alertas", response_model=list[MantenimientoAlertaResponse])
def alertas_mantenimiento(db: DbDep, _: User = Depends(require_reader)):
    """Devuelve vehículos cuyo kilometraje alcanzó el próximo mantenimiento."""
    vehiculos = db.query(Vehiculo).filter(Vehiculo.estado != "inactivo").all()
    resultado = []
    for vehiculo in vehiculos:
        ultimo = (
            db.query(Mantenimiento)
            .filter(
                Mantenimiento.vehiculo_id == vehiculo.id,
                Mantenimiento.proximo_kilometraje_mantenimiento.isnot(None),
                Mantenimiento.fecha_baja.is_(None),
            )
            .order_by(Mantenimiento.id.desc())
            .first()
        )
        proximo = ultimo.proximo_kilometraje_mantenimiento if ultimo else None
        resultado.append({
            "vehiculo_id": vehiculo.id,
            "kilometraje_actual": vehiculo.kilometraje_actual,
            "proximo_kilometraje_mantenimiento": proximo,
            "alerta": proximo is not None and vehiculo.kilometraje_actual >= proximo,
        })
    return resultado


@router.get("/", response_model=list[MantenimientoResponse])
def listar_mantenimientos(db: DbDep, _: User = Depends(require_reader), vehiculo_id: int | None = None, tipo: str | None = None):
    items = MantenimientoService(db).get_all_mantenimientos()
    return [item for item in items if (vehiculo_id is None or item.vehiculo_id == vehiculo_id) and (tipo is None or item.tipo == tipo)]


@router.get("/vehiculo/{vehiculo_id}/historial", response_model=list[MantenimientoResponse])
def historial_mantenimiento(vehiculo_id: int, db: DbDep, _: User = Depends(require_reader)):
    return [item for item in MantenimientoService(db).get_all_mantenimientos() if item.vehiculo_id == vehiculo_id]


@router.get("/{id}", response_model=MantenimientoResponse)
def obtener_mantenimiento(id: int, db: DbDep, _: User = Depends(require_reader)):
    return MantenimientoService(db).get_mantenimiento_by_id(id)


@router.post("/", response_model=MantenimientoResponse, status_code=status.HTTP_201_CREATED)
def crear_mantenimiento(schema: MantenimientoCreate, db: DbDep, user: User = Depends(require_manager)):
    service = MantenimientoService(db)
    if schema.tipo == "PREVENTIVO" and schema.plan_id is not None:
        return service.crear_preventivo(schema, user.id)
    return service.create_mantenimiento(schema)


@router.post("/preventivo", response_model=MantenimientoResponse, status_code=status.HTTP_201_CREATED)
def crear_preventivo(schema: MantenimientoCreate, db: DbDep, user: User = Depends(require_manager)):
    schema.tipo = "PREVENTIVO"
    return MantenimientoService(db).crear_preventivo(schema, user.id)


@router.post("/correctivo", response_model=MantenimientoResponse, status_code=status.HTTP_201_CREATED)
def crear_correctivo(schema: MantenimientoCreate, db: DbDep, user: User = Depends(require_manager)):
    schema.tipo = "CORRECTIVO"
    return MantenimientoService(db).create_mantenimiento(schema)


@router.patch("/{id}/ejecutar", response_model=MantenimientoResponse)
def ejecutar_mantenimiento(id: int, payload: dict, db: DbDep, user: User = Depends(require_manager)):
    return MantenimientoService(db).ejecutar_mantenimiento(
        id, payload.get("trabajador_id", user.id), float(payload.get("km_ejecucion", 0)),
        float(payload.get("horas_ejecucion", 0)), payload.get("observaciones_ejecucion"),
    )


@router.put("/{id}", response_model=MantenimientoResponse)
def actualizar_mantenimiento(id: int, schema: MantenimientoUpdate, db: DbDep, _: User = Depends(require_manager)):
    return MantenimientoService(db).update_mantenimiento(id, schema)


@router.delete("/{id}")
def eliminar_mantenimiento(id: int, db: DbDep, user: User = Depends(require_manager)):
    return MantenimientoService(db).delete_mantenimiento(id, user.id)
