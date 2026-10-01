from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.averia import Averia
from app.models.vehiculo import Vehiculo
from app.models.transportes_enums import CriticidadAveria, EstadoAveria
from app.schemas.averia_schema import AveriaCreate, AveriaUpdate
from app.services.lifecycle_service import LifecycleService

# Estados en los que una avería se considera "activa" (no resuelta/cerrada)
ESTADOS_ACTIVOS = {
    EstadoAveria.REPORTADA.value,
    EstadoAveria.EN_EVALUACION.value,
    EstadoAveria.PROGRAMADA.value,
    EstadoAveria.EN_REPARACION.value,
}


class AveriaService:
    def __init__(self, db: Session):
        self.db = db
        self.lifecycle = LifecycleService(db)

    def get_averia_by_id(self, averia_id: int) -> Averia:
        averia = self.db.query(Averia).filter(Averia.id == averia_id).first()
        if not averia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avería no encontrada.",
            )
        return averia

    def get_all_averias(self) -> list[Averia]:
        return self.db.query(Averia).all()

    def get_averias_por_vehiculo(self, vehiculo_id: int) -> list[Averia]:
        return (
            self.db.query(Averia)
            .filter(Averia.vehiculo_id == vehiculo_id)
            .all()
        )

    def create_averia(self, schema: AveriaCreate, usuario_id: int) -> Averia:
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id,
            Vehiculo.estado != "inactivo",
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado.",
            )

        averia = Averia(
            vehiculo_id=schema.vehiculo_id,
            ruta_id=schema.ruta_id,
            descripcion=schema.descripcion,
            criticidad=schema.criticidad,
            estado=EstadoAveria.REPORTADA.value,
            origen_incidente_id=schema.origen_incidente_id,
            registrado_por=usuario_id,
        )
        self.db.add(averia)
        self.db.commit()
        self.db.refresh(averia)

        # Una avería crítica activa bloquea el vehículo
        if averia.criticidad == CriticidadAveria.CRITICA.value:
            self.lifecycle.bloquear(vehiculo)
            self.db.commit()

        return averia

    def update_averia(self, averia_id: int, schema: AveriaUpdate, usuario_id: int) -> Averia:
        averia = self.get_averia_by_id(averia_id)

        if schema.descripcion is not None:
            averia.descripcion = schema.descripcion
        if schema.criticidad is not None:
            averia.criticidad = schema.criticidad
        if schema.detalle_resolucion is not None:
            averia.detalle_resolucion = schema.detalle_resolucion

        if schema.estado is not None:
            self._aplicar_estado(averia, schema.estado, usuario_id)

        self.db.commit()
        self.db.refresh(averia)
        return averia

    def _aplicar_estado(
        self,
        averia: Averia,
        nuevo_estado: str,
        usuario_id: int,
    ) -> None:
        if nuevo_estado == averia.estado:
            return

        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == averia.vehiculo_id
        ).first()

        # Establecer el estado primero para que la lógica de reevaluación no
        # considere activa la avería que se acaba de resolver.
        averia.estado = nuevo_estado
        # Flush explícito (las sesiones de test usan autoflush=False) para que
        # la query de reevaluación vea el estado recién asignado.
        self.db.flush()

        if nuevo_estado == EstadoAveria.RESUELTA.value or nuevo_estado == EstadoAveria.CERRADA.value:
            averia.fecha_resolucion = datetime.now(timezone.utc)
            if vehiculo:
                # No asumir disponible si queda otra avería crítica activa.
                self._reevaluar_bloqueo(vehiculo)
        else:
            # Avance del ciclo: reportada -> en_evaluacion -> programada -> en_reparacion
            if nuevo_estado in ESTADOS_ACTIVOS and averia.criticidad == CriticidadAveria.CRITICA.value:
                if vehiculo:
                    self.lifecycle.bloquear(vehiculo)

    def _reevaluar_bloqueo(self, vehiculo: Vehiculo) -> None:
        """Tras resolver una avería, exige inspección antes de liberar el vehículo."""
        if self.lifecycle.hay_averia_critica_activa(vehiculo.id):
            self.lifecycle.bloquear(vehiculo)
        elif vehiculo.estado == "bloqueado":
            self.lifecycle.cambiar_estado(vehiculo, "observado")

    def resolver_averia(self, averia_id: int, usuario_id: int) -> Averia:
        averia = self.get_averia_by_id(averia_id)
        self._aplicar_estado(averia, EstadoAveria.RESUELTA.value, usuario_id)
        self.db.commit()
        self.db.refresh(averia)
        return averia

    def cerrar_averia(self, averia_id: int, usuario_id: int) -> Averia:
        averia = self.get_averia_by_id(averia_id)
        self._aplicar_estado(averia, EstadoAveria.CERRADA.value, usuario_id)
        self.db.commit()
        self.db.refresh(averia)
        return averia
