from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.averia import Averia
from app.models.jornada_transporte import Checklist, IncidenciaRuta, JornadaTransporte
from app.models.mantenimiento import Mantenimiento
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.schemas.jornada_transporte_schema import (
    ChecklistCreate,
    IncidenciaRutaCreate,
    JornadaAsignacionCreate,
    RegistroAccionCreate,
)


class JornadaTransporteService:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> list[JornadaTransporte]:
        return self.db.query(JornadaTransporte).order_by(JornadaTransporte.id.desc()).all()

    def obtener(self, jornada_id: int) -> JornadaTransporte:
        jornada = self.db.query(JornadaTransporte).filter(JornadaTransporte.id == jornada_id).first()
        if jornada is None:
            raise HTTPException(status_code=404, detail="Jornada de transporte no encontrada.")
        return jornada

    def registrar_accion(self, conductor_id: int, data: RegistroAccionCreate) -> JornadaTransporte:
        conductor = self.db.query(User).filter(User.id == conductor_id).first()
        if conductor is None or conductor.role != "conductor":
            raise HTTPException(status_code=403, detail="Solo los conductores pueden registrar acciones directamente.")

        vehiculo = None
        if data.vehiculo_id is not None:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == data.vehiculo_id).first()
            if vehiculo is None:
                raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
            if vehiculo.estado != "disponible" and data.accion_tipo == "Empezar a Conducir":
                raise HTTPException(status_code=400, detail="El vehículo no está disponible para esta acción.")
        
        jornada = JornadaTransporte(
            conductor_id=conductor_id,
            vehiculo_id=data.vehiculo_id,
            accion_tipo=data.accion_tipo,
            ruta=data.ruta,
            nivel_combustible=data.nivel_combustible,
            checklist_flash=data.checklist_flash,
            observaciones=data.observaciones,
            estado="en_curso",
            fecha_inicio=datetime.utcnow()
        )
        
        if vehiculo and data.accion_tipo == "Empezar a Conducir":
            vehiculo.estado = "en_ruta"
            
        self.db.add(jornada)
        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def asignar(self, data: JornadaAsignacionCreate) -> JornadaTransporte:
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == data.vehiculo_id,
            Vehiculo.estado != "inactivo",
        ).first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        if vehiculo.estado != "disponible":
            raise HTTPException(status_code=400, detail="El vehículo no está disponible para asignación.")
        conductor = self.db.query(User).filter(User.id == data.conductor_id).first()
        if conductor is None:
            raise HTTPException(status_code=404, detail="Conductor no encontrado.")
        if conductor.role != "conductor":
            raise HTTPException(status_code=400, detail="El usuario seleccionado no tiene el rol de conductor.")

        jornada = JornadaTransporte(
            vehiculo_id=data.vehiculo_id,
            conductor_id=data.conductor_id,
            estado="pendiente",
        )
        vehiculo.estado = "asignado"
        self.db.add(jornada)
        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def registrar_checklist_inicial(
        self, jornada_id: int, data: ChecklistCreate, conductor_id: int
    ) -> JornadaTransporte:
        jornada = self.obtener(jornada_id)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "pendiente":
            raise HTTPException(status_code=400, detail="La jornada no acepta un checklist inicial.")
        if data.tipo != "inicial":
            raise HTTPException(status_code=400, detail="El checklist de este flujo debe ser inicial.")

        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        if data.kilometraje < (vehiculo.kilometraje_actual or 0):
            raise HTTPException(status_code=400, detail="El kilometraje no puede disminuir.")

        jornada.checklists.append(Checklist(**data.model_dump()))
        vehiculo.kilometraje_actual = data.kilometraje
        jornada.km_inicial = data.kilometraje
        if data.conforme:
            jornada.estado = "en_curso"
            jornada.fecha_inicio = datetime.utcnow()
            vehiculo.estado = "en_ruta"
        else:
            jornada.estado = "cancelada_por_averia"
            vehiculo.estado = "en_mantenimiento"
            self.db.add(Averia(
                vehiculo_id=vehiculo.id,
                descripcion=data.observaciones or "Avería detectada en checklist inicial.",
                criticidad="media",
            ))
        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def registrar_checklist_final(
        self, jornada_id: int, data: ChecklistCreate, conductor_id: int
    ) -> JornadaTransporte:
        jornada = self.obtener(jornada_id)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "en_curso":
            raise HTTPException(status_code=400, detail="Solo se puede finalizar una jornada en curso.")
        if data.tipo != "final":
            raise HTTPException(status_code=400, detail="El checklist de este flujo debe ser final.")
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        if data.kilometraje < (vehiculo.kilometraje_actual or 0):
            raise HTTPException(status_code=400, detail="El kilometraje no puede disminuir.")
        jornada.checklists.append(Checklist(**data.model_dump()))
        vehiculo.kilometraje_actual = data.kilometraje
        jornada.km_final = data.kilometraje
        jornada.estado = "finalizada"
        jornada.fecha_fin = datetime.utcnow()
        vehiculo.estado = "disponible" if data.conforme else "en_mantenimiento"

        km_inicial = jornada.km_inicial or data.kilometraje
        self._calcular_metricas(jornada, km_inicial, data.kilometraje)

        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def _calcular_metricas(
        self, jornada: JornadaTransporte, km_inicial: float, km_final: float
    ) -> None:
        """Calcula horas efectivas y km recorridos, generando alertas e incidencias si se superan umbrales."""
        fecha_inicio = jornada.fecha_inicio or datetime.utcnow()
        fecha_fin = jornada.fecha_fin or datetime.utcnow()

        duracion_horas = (fecha_fin - fecha_inicio).total_seconds() / 3600.0

        # Descuento de 1 hora de almuerzo si la jornada cruza el mediodía
        descuento_almuerzo = 0.0
        if fecha_inicio.hour < 12 and fecha_fin.hour >= 12:
            descuento_almuerzo = 1.0

        horas_efectivas = duracion_horas - descuento_almuerzo
        jornada.horas_efectivas = round(horas_efectivas, 2)

        if horas_efectivas > 10:
            jornada.alerta_horas = True
            self.db.add(
                IncidenciaRuta(
                    jornada_id=jornada.id,
                    tipo="falla",
                    descripcion=f"Alerta: Jornada superó 10 horas efectivas ({horas_efectivas:.1f}h).",
                )
            )

        km_recorridos = km_final - km_inicial
        jornada.km_inicial = km_inicial
        jornada.km_final = km_final

        if km_recorridos > 200:
            jornada.alerta_km = True
            self.db.add(
                IncidenciaRuta(
                    jornada_id=jornada.id,
                    tipo="falla",
                    descripcion=f"Alerta: Kilometraje recorrido excede 200km ({km_recorridos:.1f}km).",
                )
            )
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).first()
            if vehiculo:
                self.db.add(
                    Averia(
                        vehiculo_id=vehiculo.id,
                        descripcion=f"Alerta: Kilometraje recorrido excede 200km ({km_recorridos:.1f}km).",
                        criticidad="media",
                    )
                )

    def registrar_incidencia(
        self, jornada_id: int, data: IncidenciaRutaCreate, conductor_id: int
    ) -> IncidenciaRuta:
        jornada = self.obtener(jornada_id)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "en_curso":
            raise HTTPException(status_code=400, detail="Solo se pueden registrar incidencias en curso.")
        incidencia = IncidenciaRuta(**data.model_dump(exclude_none=True), jornada_id=jornada_id)
        self.db.add(incidencia)
        self.db.commit()
        self.db.refresh(incidencia)
        return incidencia
