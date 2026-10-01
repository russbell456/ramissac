from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inspeccion import ChecklistItem, Inspeccion, InspeccionDetalle
from app.models.vehiculo import Vehiculo
from app.models.ruta_asignacion import RutaAsignacion
from app.models.transportes_enums import (
    CriticidadItem,
    EstadoInspeccion,
    ResultadoChecklist,
    TipoInspeccion,
)
from app.schemas.inspeccion_schema import (
    ChecklistItemCreate,
    InspeccionCreate,
    InspeccionResolver,
)
from app.services.lifecycle_service import LifecycleService

# Resultados que permiten iniciar una ruta (SALIDA aprobada)
RESULTADOS_SALIDA_APROBADA = {
    EstadoInspeccion.APROBADA.value,
    EstadoInspeccion.APROBADA_CON_OBSERVACIONES.value,
}


class InspeccionService:
    def __init__(self, db: Session):
        self.db = db
        self.lifecycle = LifecycleService(db)

    # ------------------------------------------------------------------
    # Checklist items
    # ------------------------------------------------------------------
    def get_checklist_item_by_id(self, item_id: int) -> ChecklistItem:
        item = self.db.query(ChecklistItem).filter(
            ChecklistItem.id == item_id,
            ChecklistItem.activo.is_(True),
        ).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ítem de checklist no encontrado.",
            )
        return item

    def get_all_checklist_items(self) -> list[ChecklistItem]:
        return (
            self.db.query(ChecklistItem)
            .filter(ChecklistItem.activo.is_(True))
            .all()
        )

    def create_checklist_item(self, schema: ChecklistItemCreate) -> ChecklistItem:
        existente = (
            self.db.query(ChecklistItem)
            .filter(ChecklistItem.codigo == schema.codigo)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código del ítem ya está registrado.",
            )
        item = ChecklistItem(
            codigo=schema.codigo,
            nombre=schema.nombre,
            descripcion=schema.descripcion,
            criticidad=schema.criticidad,
            activo=schema.activo,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # Inspecciones
    # ------------------------------------------------------------------
    def get_inspeccion_by_id(self, inspeccion_id: int) -> Inspeccion:
        inspeccion = self.db.query(Inspeccion).filter(
            Inspeccion.id == inspeccion_id,
            Inspeccion.activa.is_(True),
        ).first()
        if not inspeccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspección no encontrada.",
            )
        return inspeccion

    def get_all_inspecciones(self) -> list[Inspeccion]:
        return (
            self.db.query(Inspeccion)
            .filter(Inspeccion.activa.is_(True))
            .all()
        )

    def get_inspecciones_por_vehiculo(self, vehiculo_id: int) -> list[Inspeccion]:
        return (
            self.db.query(Inspeccion)
            .filter(
                Inspeccion.vehiculo_id == vehiculo_id,
                Inspeccion.activa.is_(True),
            )
            .all()
        )

    def _validar_vehiculo(self, vehiculo_id: int) -> Vehiculo:
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == vehiculo_id,
            Vehiculo.estado != "inactivo",
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado.",
            )
        return vehiculo

    def _validar_ruta(self, ruta_id: int) -> RutaAsignacion:
        ruta = self.db.query(RutaAsignacion).filter(
            RutaAsignacion.id == ruta_id,
            RutaAsignacion.estado_ruta != "inactivo",
        ).first()
        if not ruta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ruta no encontrada.",
            )
        return ruta

    def create_inspeccion(
        self,
        schema: InspeccionCreate,
        usuario_id: int,
    ) -> Inspeccion:
        vehiculo = self._validar_vehiculo(schema.vehiculo_id)
        if schema.ruta_id is not None:
            ruta = self._validar_ruta(schema.ruta_id)
            if ruta.vehiculo_id != vehiculo.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La ruta no corresponde al vehículo de la inspección.",
                )

        # Construir detalles (validando que cada ítem exista)
        detalles = []
        for d in schema.detalles:
            self.get_checklist_item_by_id(d.item_id)
            detalles.append(
                InspeccionDetalle(
                    item_id=d.item_id,
                    resultado=d.resultado,
                    comentario=d.comentario,
                )
            )

        inspeccion = Inspeccion(
            vehiculo_id=schema.vehiculo_id,
            ruta_id=schema.ruta_id,
            tipo=schema.tipo,
            resultado=None,  # pendiente hasta resolver
            realizada_por=usuario_id,
            observaciones=schema.observaciones,
            activa=True,
            detalles=detalles,
        )
        self.db.add(inspeccion)
        self.db.commit()
        self.db.refresh(inspeccion)
        return inspeccion

    # ------------------------------------------------------------------
    # Resolución (aprobación/rechazo) de inspecciones
    # ------------------------------------------------------------------
    def resolver_inspeccion(
        self,
        inspeccion_id: int,
        schema: InspeccionResolver,
        usuario_id: int,
    ) -> Inspeccion:
        inspeccion = self.get_inspeccion_by_id(inspeccion_id)
        if inspeccion.resultado is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La inspección ya fue resuelta.",
            )

        if schema.resultado == EstadoInspeccion.APROBADA.value:
            self._validar_conformidad_requerida(inspeccion)

        inspeccion.resultado = schema.resultado
        if schema.observaciones:
            inspeccion.observaciones = schema.observaciones
        inspeccion.realizada_por = usuario_id

        self.db.commit()
        self.db.refresh(inspeccion)
        return inspeccion

    def _validar_conformidad_requerida(self, inspeccion: Inspeccion) -> None:
        """Si hay ítems críticos no conformes no se puede aprobar plenamente."""
        for d in inspeccion.detalles:
            item = self.get_checklist_item_by_id(d.item_id)
            if (
                item.criticidad in (CriticidadItem.ALTA.value, CriticidadItem.CRITICA.value)
                and d.resultado == ResultadoChecklist.NO_CONFORME.value
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "No se puede aprobar la inspección: existe un ítem de "
                        "criticidad alta/crítica con resultado no conforme."
                    ),
                )

    # ------------------------------------------------------------------
    # Reglas para SALIDA (inicio de ruta)
    # ------------------------------------------------------------------
    def tiene_salida_aprobada(self, ruta_id: int, vehiculo_id: int) -> bool:
        """¿Existe una inspección SALIDA aprobada para la ruta/vehículo?"""
        inspeccion = self.obtener_salida(ruta_id, vehiculo_id)
        if not inspeccion or inspeccion.resultado is None:
            return False
        return inspeccion.resultado in RESULTADOS_SALIDA_APROBADA

    def obtener_salida(self, ruta_id: int, vehiculo_id: int) -> Inspeccion | None:
        return (
            self.db.query(Inspeccion)
            .filter(
                Inspeccion.ruta_id == ruta_id,
                Inspeccion.vehiculo_id == vehiculo_id,
                Inspeccion.tipo == TipoInspeccion.SALIDA.value,
                Inspeccion.activa.is_(True),
            )
            .order_by(Inspeccion.fecha.desc())
            .first()
        )

    # ------------------------------------------------------------------
    # Reglas para POST_MANTENIMIENTO (liberación a disponible)
    # ------------------------------------------------------------------
    def tiene_post_mantenimiento_aprobada(self, vehiculo_id: int) -> bool:
        """¿Existe una inspección POST_MANTENIMIENTO aprobada para el vehículo?"""
        inspeccion = (
            self.db.query(Inspeccion)
            .filter(
                Inspeccion.vehiculo_id == vehiculo_id,
                Inspeccion.tipo == TipoInspeccion.POST_MANTENIMIENTO.value,
                Inspeccion.activa.is_(True),
            )
            .order_by(Inspeccion.fecha.desc())
            .first()
        )
        if not inspeccion or inspeccion.resultado is None:
            return False
        return inspeccion.resultado in RESULTADOS_SALIDA_APROBADA

    def resolver_post_mantenimiento(self, inspeccion_id: int, schema, usuario_id: int) -> Inspeccion:
        """Resuelve una inspección POST_MANTENIMIENTO y libera el vehículo si es aprobada.

        Si la inspección POST_MANTENIMIENTO es RECHAZADA, el vehículo permanece
        en estado 'observado'.
        """
        inspeccion = self.resolver_inspeccion(inspeccion_id, schema, usuario_id)
        if inspeccion.tipo == TipoInspeccion.POST_MANTENIMIENTO.value:
            vehiculo = self._validar_vehiculo(inspeccion.vehiculo_id)
            if inspeccion.resultado in RESULTADOS_SALIDA_APROBADA:
                self.lifecycle.liberar_post_mantenimiento(vehiculo)
                self.db.commit()
                self.db.refresh(inspeccion)
        return inspeccion

