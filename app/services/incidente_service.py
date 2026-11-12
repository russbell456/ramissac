
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.incidente import Incidente
from app.models.averia import Averia
from app.models.vehiculo import Vehiculo
from app.models.transportes_enums import EstadoIncidente, CriticidadAveria
from app.schemas.incidente_schema import IncidenteCreate, IncidenteUpdate


class IncidenteService:
    def __init__(self, db: Session):
        self.db = db

    def get_incidente_by_id(self, incidente_id: int) -> Incidente:
        incidente = self.db.query(Incidente).filter(
            Incidente.id == incidente_id
        ).first()

        if not incidente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incidente no encontrado.",
            )

        return incidente

    def get_all_incidentes(self) -> list[Incidente]:
        return self.db.query(Incidente).all()

    def get_incidentes_por_vehiculo(
        self,
        vehiculo_id: int,
    ) -> list[Incidente]:
        return (
            self.db.query(Incidente)
            .filter(Incidente.vehiculo_id == vehiculo_id)
            .all()
        )

    def create_incidente(
        self,
        schema: IncidenteCreate,
        usuario_id: int,
    ) -> Incidente:
        # Validar vehiculo si se indica
        if schema.vehiculo_id is not None:
            vehiculo = self.db.query(Vehiculo).filter(
                Vehiculo.id == schema.vehiculo_id,
                Vehiculo.estado != "inactivo",
            ).first()

            if not vehiculo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vehiculo no encontrado.",
                )

        incidente = Incidente(
            vehiculo_id=schema.vehiculo_id,
            ruta_id=schema.ruta_id,
            tipo=schema.tipo,
            estado=EstadoIncidente.REPORTADO.value,
            descripcion=schema.descripcion,
            afecta_personas=schema.afecta_personas,
            dano_vehiculo=schema.dano_vehiculo,
            requiere_acta=schema.requiere_acta,
            registrado_por=usuario_id,
            observaciones=schema.observaciones,
        )

        self.db.add(incidente)
        self.db.commit()
        self.db.refresh(incidente)

        # Si el incidente genera dano al vehiculo,
        # asociar/generar una averia.
        if schema.dano_vehiculo and schema.vehiculo_id is not None:
            self._generar_averia_desde_incidente(
                incidente,
                usuario_id,
            )

        return incidente

    def _generar_averia_desde_incidente(
        self,
        incidente: Incidente,
        usuario_id: int,
    ) -> Averia:
        """Genera una averia asociada al incidente.

        Si el incidente afecta personas, la averia generada es de
        criticidad CRITICA, permitiendo bloquear el vehiculo segun
        las reglas del modulo.
        """
        criticidad = (
            CriticidadAveria.CRITICA.value
            if incidente.afecta_personas
            else CriticidadAveria.MEDIA.value
        )

        averia = Averia(
            vehiculo_id=incidente.vehiculo_id,
            ruta_id=incidente.ruta_id,
            descripcion=(
                f"Averia generada desde incidente #{incidente.id}: "
                f"{incidente.descripcion}"
            ),
            criticidad=criticidad,
            estado="reportada",
            origen_incidente_id=incidente.id,
            registrado_por=usuario_id,
        )

        self.db.add(averia)
        self.db.commit()
        self.db.refresh(averia)

        # Una averia critica bloquea el vehiculo.
        if averia.criticidad == CriticidadAveria.CRITICA.value:
            vehiculo = self.db.query(Vehiculo).filter(
                Vehiculo.id == averia.vehiculo_id
            ).first()

            if vehiculo and vehiculo.estado != "inactivo":
                vehiculo.estado = "bloqueado"
                self.db.commit()

        return averia

    def update_incidente(
        self,
        incidente_id: int,
        schema: IncidenteUpdate,
    ) -> Incidente:
        incidente = self.get_incidente_by_id(incidente_id)

        if schema.tipo is not None:
            incidente.tipo = schema.tipo

        if schema.estado is not None:
            incidente.estado = schema.estado

        if schema.descripcion is not None:
            incidente.descripcion = schema.descripcion

        if schema.afecta_personas is not None:
            incidente.afecta_personas = schema.afecta_personas

        if schema.dano_vehiculo is not None:
            incidente.dano_vehiculo = schema.dano_vehiculo

        if schema.requiere_acta is not None:
            incidente.requiere_acta = schema.requiere_acta

        if schema.observaciones is not None:
            incidente.observaciones = schema.observaciones

        self.db.commit()
        self.db.refresh(incidente)

        return incidente

    def delete_incidente(
        self,
        incidente_id: int,
    ) -> Incidente:
        incidente = self.get_incidente_by_id(incidente_id)

        self.db.delete(incidente)
        self.db.commit()

        return incidente

