from __future__ import annotations

from datetime import datetime
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.averia import Averia
from app.models.jornada_transporte import (
    AccionCocada, AccionInspeccion, AccionTorque, AccionTrabajosExternos,
    Checklist, IncidenciaRuta, JornadaTransporte,
)
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
        conductor = self.db.query(User).filter(User.id == conductor_id).with_for_update().first()
        if conductor is None or conductor.role != "conductor":
            raise HTTPException(status_code=403, detail="Solo los conductores pueden registrar acciones directamente.")

        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == data.vehiculo_id).with_for_update().first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        es_grua = data.accion_tipo == "Operar Grúa"
        if not es_grua and data.km_inicial is not None and data.km_inicial < (vehiculo.kilometraje_actual or 0):
            raise HTTPException(status_code=400, detail="El kilometraje ingresado no puede ser menor al último registrado.")
        es_conduccion = data.accion_tipo == "Empezar a Conducir"
        if es_conduccion and (vehiculo.estado != "disponible" or vehiculo.estado_semaforo == "rojo"):
            raise HTTPException(status_code=400, detail="El vehículo no está disponible para esta acción.")

        activas = self.db.query(JornadaTransporte).filter(
            JornadaTransporte.conductor_id == conductor_id,
            JornadaTransporte.jornada_padre_id.is_(None),
            JornadaTransporte.estado.in_(["pendiente", "en_curso"]),
        ).all()
        padre = next((j for j in activas if j.vehiculo_id == vehiculo.id and j.estado == "en_curso"), None)
        if es_conduccion and activas:
            raise HTTPException(409, "El conductor ya tiene una jornada activa.")
        if not es_conduccion and padre is None:
            raise HTTPException(409, "Abra una jornada con Empezar a Conducir antes de registrar sub-acciones.")
        if data.jornada_padre_id is not None and (padre is None or padre.id != data.jornada_padre_id):
            raise HTTPException(409, "La jornada padre no corresponde a la jornada activa del conductor y vehículo.")
        tipo = unicodedata.normalize("NFKD", vehiculo.tipo or vehiculo.modelo).encode("ascii", "ignore").decode().lower()
        if data.accion_tipo == "Operar Grúa" and not ("grua" in tipo or (not vehiculo.tipo and vehiculo.placa in {"Z7F-777", "Z7M-813"})):
            raise HTTPException(400, "Operar Grúa solo está permitido para camiones grúa.")
        if tipo in {"camioneta", "coaster"} and data.accion_tipo in {"Medición de Cocada", "Medición de Torque", "Trabajos a Externos"}:
            raise HTTPException(400, "La acción no está habilitada para este tipo de vehículo.")
        semaforo = self._evaluar_semaforo(data)
        if data.detalles_combustible and data.detalles_combustible.odometro is not None and data.detalles_combustible.odometro != data.km_inicial:
            raise HTTPException(400, "El odómetro del abastecimiento debe coincidir con el kilometraje registrado.")
        if not es_grua and data.km_inicial is not None:
            vehiculo.kilometraje_actual = data.km_inicial
        fecha_registro = datetime.utcnow()
        jornada = JornadaTransporte(
            jornada_padre_id=padre.id if padre else None,
            estado_semaforo=vehiculo.estado_semaforo if es_conduccion else semaforo,
            tiene_observaciones=data.tiene_observaciones,
            severidad=data.severidad,
            foto_observacion=data.foto_observacion,
            conductor_id=conductor_id,
            vehiculo_id=data.vehiculo_id,
            accion_tipo=data.accion_tipo,
            ruta=data.ruta,
            nivel_combustible=data.nivel_combustible if data.nivel_combustible is not None else padre.nivel_combustible if padre else None,
            checklist_flash=data.checklist_flash,
            observaciones=data.observaciones,
            km_inicial=None if es_grua else data.km_inicial,
            estado="en_curso" if es_conduccion else "finalizada",
            fecha_inicio=fecha_registro,
            fecha_fin=None if es_conduccion else fecha_registro,
        )

        if es_conduccion:
            vehiculo.estado = "en_ruta"
            
        self.db.add(jornada)
        self.db.flush()
        self._aplicar_semaforo(jornada, vehiculo, semaforo, data.observaciones, cerrar=es_conduccion)
        if padre and semaforo != "verde":
            if padre.estado_semaforo != "rojo":
                padre.foto_observacion = data.foto_observacion
                padre.observaciones = data.observaciones
                padre.severidad = data.severidad
                padre.tiene_observaciones = True
            self._aplicar_semaforo(padre, vehiculo, semaforo, data.observaciones, crear_alerta=False, cerrar=False)

        from app.models.jornada_transporte import AccionGrua, AccionCombustible, AccionMantenimiento
        if data.accion_tipo == "Operar Grúa" and data.detalles_grua:
            grua = AccionGrua(jornada_id=jornada.id, **data.detalles_grua.model_dump())
            self.db.add(grua)
        elif data.accion_tipo == "Abastecer Combustible" and data.detalles_combustible:
            comb = AccionCombustible(jornada_id=jornada.id, **data.detalles_combustible.model_dump())
            comb.odometro = data.km_inicial
            self.db.add(comb)
        elif data.accion_tipo == "Mantenimiento Preventivo / Correctivo" and data.detalles_mantenimiento:
            mantenimiento = AccionMantenimiento(jornada_id=jornada.id, **data.detalles_mantenimiento.model_dump())
            self.db.add(mantenimiento)
        elif data.accion_tipo == "Inspección Técnica" and data.detalles_inspeccion:
            self.db.add(AccionInspeccion(
                jornada_id=jornada.id, **data.detalles_inspeccion.model_dump()
            ))
        elif data.accion_tipo == "Medición de Cocada" and data.detalles_cocada:
            self.db.add(AccionCocada(
                jornada_id=jornada.id, **data.detalles_cocada.model_dump()
            ))
        elif data.accion_tipo == "Medición de Torque" and data.detalles_torque:
            self.db.add(AccionTorque(
                jornada_id=jornada.id, **data.detalles_torque.model_dump()
            ))
        elif data.accion_tipo == "Trabajos a Externos" and data.detalles_trabajos_externos:
            self.db.add(AccionTrabajosExternos(
                jornada_id=jornada.id, **data.detalles_trabajos_externos.model_dump()
            ))

        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def asignar(self, data: JornadaAsignacionCreate) -> JornadaTransporte:
        conductor = self.db.query(User).filter(User.id == data.conductor_id).with_for_update().first()
        if conductor is None:
            raise HTTPException(404, "Conductor no encontrado.")
        if conductor.role != "conductor":
            raise HTTPException(400, "El usuario seleccionado no tiene el rol de conductor.")
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == data.vehiculo_id, Vehiculo.estado != "inactivo").with_for_update().first()
        if vehiculo is None:
            raise HTTPException(404, "Vehículo no encontrado.")
        if vehiculo.estado != "disponible" or vehiculo.estado_semaforo == "rojo":
            raise HTTPException(400, "El vehículo no está disponible para asignación.")
        if self.db.query(JornadaTransporte).filter(JornadaTransporte.conductor_id == conductor.id, JornadaTransporte.estado.in_(["pendiente", "en_curso"]), JornadaTransporte.jornada_padre_id.is_(None)).first():
            raise HTTPException(409, "El conductor ya tiene una jornada activa.")

        jornada = JornadaTransporte(
            vehiculo_id=data.vehiculo_id,
            conductor_id=data.conductor_id,
            estado="pendiente",
            estado_semaforo=vehiculo.estado_semaforo,
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
        self.db.query(User).filter(User.id == jornada.conductor_id).with_for_update().first()
        self.db.refresh(jornada)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "pendiente":
            raise HTTPException(status_code=400, detail="La jornada no acepta un checklist inicial.")
        if data.tipo != "inicial":
            raise HTTPException(status_code=400, detail="El checklist de este flujo debe ser inicial.")

        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        if vehiculo.estado_semaforo == "rojo":
            raise HTTPException(400, "No disponible por falla crítica.")
        if data.kilometraje < (vehiculo.kilometraje_actual or 0):
            raise HTTPException(status_code=400, detail="El kilometraje no puede disminuir.")

        semaforo = self._evaluar_semaforo(data)
        jornada.checklists.append(Checklist(**data.model_dump(exclude={"tiene_observaciones", "severidad", "foto_observacion"})))
        if jornada.estado_semaforo != "rojo" or semaforo == "rojo":
            jornada.foto_observacion = data.foto_observacion or jornada.foto_observacion
            jornada.severidad = data.severidad or jornada.severidad
            jornada.observaciones = data.observaciones or jornada.observaciones
            jornada.tiene_observaciones = data.tiene_observaciones or jornada.tiene_observaciones
        vehiculo.kilometraje_actual = data.kilometraje
        jornada.km_inicial = data.kilometraje
        try:
            jornada.nivel_combustible = int(self._nivel_porcentaje(data.nivel_combustible))
        except ValueError:
            raise HTTPException(400, "Indique el combustible inicial como porcentaje.")
        if semaforo != "rojo":
            jornada.estado = "en_curso"
            jornada.fecha_inicio = datetime.utcnow()
            vehiculo.estado = "en_ruta"
        else:
            jornada.estado = "cancelada_por_averia"
            vehiculo.estado = "en_mantenimiento"

        self._aplicar_semaforo(jornada, vehiculo, semaforo, data.observaciones)
        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def registrar_checklist_final(
        self, jornada_id: int, data: ChecklistCreate, conductor_id: int
    ) -> JornadaTransporte:
        jornada = self.obtener(jornada_id)
        self.db.query(User).filter(User.id == jornada.conductor_id).with_for_update().first()
        self.db.refresh(jornada)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "en_curso":
            raise HTTPException(status_code=400, detail="Solo se puede finalizar una jornada en curso.")
        if data.tipo != "final":
            raise HTTPException(status_code=400, detail="El checklist de este flujo debe ser final.")
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        if data.kilometraje < (vehiculo.kilometraje_actual or 0):
            raise HTTPException(status_code=400, detail="El kilometraje no puede disminuir.")
        semaforo = self._evaluar_semaforo(data)
        jornada.checklists.append(Checklist(**data.model_dump(exclude={"tiene_observaciones", "severidad", "foto_observacion"})))
        if jornada.estado_semaforo != "rojo" or semaforo == "rojo":
            jornada.foto_observacion = data.foto_observacion or jornada.foto_observacion
            jornada.severidad = data.severidad or jornada.severidad
            jornada.observaciones = data.observaciones or jornada.observaciones
            jornada.tiene_observaciones = data.tiene_observaciones or jornada.tiene_observaciones
        vehiculo.kilometraje_actual = data.kilometraje
        jornada.km_final = data.kilometraje
        jornada.estado = "finalizada"
        jornada.fecha_fin = datetime.utcnow()
        vehiculo.estado = "disponible" if data.conforme else "en_mantenimiento"

        self._aplicar_semaforo(jornada, vehiculo, semaforo, data.observaciones, cerrar=False)
        try:
            nivel_final = self._nivel_porcentaje(data.nivel_combustible)
        except ValueError:
            raise HTTPException(400, "Indique el nivel final como porcentaje entre 0 y 100.")
        if not 0 <= nivel_final <= 100:
            raise HTTPException(400, "El nivel final debe estar entre 0 y 100.")
        jornada.nivel_combustible_final = nivel_final
        jornada.galones_abastecidos = sum(
            a.detalles_combustible.galones or 0 for a in jornada.sub_acciones if a.detalles_combustible
        )
        if vehiculo.capacidad_tanque_galones and jornada.nivel_combustible is not None:
            consumo = (jornada.nivel_combustible - nivel_final) / 100 * vehiculo.capacidad_tanque_galones + jornada.galones_abastecidos
            if consumo >= 0:
                jornada.galones_consumidos = round(consumo, 4)
                distancia = data.kilometraje - jornada.km_inicial if jornada.km_inicial is not None else 0
                jornada.rendimiento_km_galon = round(distancia / consumo, 4) if consumo > 0 else None
        km_inicial = jornada.km_inicial if jornada.km_inicial is not None else data.kilometraje
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
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
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
        self.db.query(User).filter(User.id == jornada.conductor_id).with_for_update().first()
        self.db.refresh(jornada)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "en_curso":
            raise HTTPException(status_code=400, detail="Solo se pueden registrar incidencias en curso.")
        if data.severidad is None or not data.foto_incidencia:
            raise HTTPException(400, "Adjunte la fotografía de la incidencia.")
        incidencia = IncidenciaRuta(**data.model_dump(exclude_none=True), jornada_id=jornada_id)
        if data.severidad:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
            self._aplicar_semaforo(jornada, vehiculo, "rojo" if data.severidad == "grave" else "amarillo", data.descripcion, cerrar=False)
            if jornada.estado_semaforo != "rojo" or data.severidad == "grave":
                jornada.foto_observacion = data.foto_incidencia
                jornada.observaciones = data.descripcion
                jornada.severidad = data.severidad
                jornada.tiene_observaciones = True
        self.db.add(incidencia)
        self.db.commit()
        self.db.refresh(incidencia)
        return incidencia

    @staticmethod
    def _evaluar_semaforo(data):
        no_conforme = getattr(data, "conforme", True) is False or any(
            value is False for value in (getattr(data, "checklist_flash", None) or {}).values()
        )
        if no_conforme and (not data.foto_observacion or not (data.observaciones or "").strip() or data.observaciones == "Sin novedades"):
            raise HTTPException(400, "Un checklist no conforme requiere descripción y fotografía.")
        if no_conforme or data.severidad == "grave":
            return "rojo"
        return "amarillo" if data.tiene_observaciones or data.severidad == "leve" else "verde"

    def _aplicar_semaforo(self, jornada, vehiculo, semaforo, descripcion, crear_alerta=True, cerrar=True):
        orden = {"verde": 0, "amarillo": 1, "rojo": 2}
        if orden[semaforo] > orden.get(jornada.estado_semaforo, 0):
            jornada.estado_semaforo = semaforo
        if orden[semaforo] > orden.get(vehiculo.estado_semaforo, 0):
            vehiculo.estado_semaforo = semaforo
        if vehiculo.estado_semaforo == "rojo":
            vehiculo.estado = "en_mantenimiento"
        if semaforo == "rojo":
            if cerrar:
                jornada.estado = "cancelada_por_averia"
                jornada.fecha_fin = datetime.utcnow()
            if crear_alerta:
                self.db.add(Averia(vehiculo_id=vehiculo.id, descripcion=descripcion or "Falla crítica detectada.", criticidad="critica"))

    @staticmethod
    def _nivel_porcentaje(valor):
        niveles = {"1/4": 25, "1/2": 50, "3/4": 75, "Lleno": 100, "Vacío": 0}
        if valor in niveles:
            return niveles[valor]
        porcentaje = float(valor.replace("%", "").strip())
        if not 0 <= porcentaje <= 100:
            raise ValueError("Nivel fuera de rango")
        return porcentaje
