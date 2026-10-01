from __future__ import annotations

from app.models.user import User
from app.models.almacen_articulos import AlmacenArticulo
from app.models.almacen_articulo_imagen import AlmacenArticuloImagen
from app.models.almacen_auditoria import AlmacenAuditoria
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle
from app.models.almacen_devolucion import AlmacenDevolucion, AlmacenDevolucionDetalle
from app.models.almacen_obras import AlmacenObra
from app.models.almacen_terceros import AlmacenTercero
from app.models.vehiculo import Vehiculo
from app.models.ruta_asignacion import RutaAsignacion
from app.models.mantenimiento import Mantenimiento
from app.models.mantenimiento_plan import PlanMantenimiento, PlanDetalleMantenimiento
from app.models.inspeccion import ChecklistItem, Inspeccion, InspeccionDetalle
from app.models.averia import Averia
from app.models.incidente import Incidente
from app.models.jornada_transporte import JornadaTransporte, Checklist, IncidenciaRuta

__all__ = [
    "User",
    "AlmacenArticulo",
    "AlmacenArticuloImagen",
    "AlmacenAuditoria",
    "AlmacenPrestamo",
    "AlmacenPrestamoDetalle",
    "AlmacenDevolucion",
    "AlmacenDevolucionDetalle",
    "AlmacenObra",
    "AlmacenTercero",
    "Vehiculo",
    "RutaAsignacion",
    "Mantenimiento",
    "PlanMantenimiento",
    "PlanDetalleMantenimiento",
    "ChecklistItem",
    "Inspeccion",
    "InspeccionDetalle",
    "Averia",
    "Incidente",
    "JornadaTransporte",
    "Checklist",
    "IncidenciaRuta",
]
