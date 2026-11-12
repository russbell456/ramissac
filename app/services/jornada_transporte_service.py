from __future__ import annotations

from datetime import datetime, time, timedelta
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.averia import Averia
from app.models.auditoria_sistema import AuditoriaSistema
from app.services.notificacion_transporte_service import notificar, resolver_avisos
from app.utils.transport_time import local_time, utc_naive, LIMA
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
    SubaccionCerrar,
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
        if data.solicitud_id:
            previa = self.db.query(JornadaTransporte).filter_by(solicitud_id=data.solicitud_id).first()
            if previa:
                if previa.conductor_id != conductor_id:
                    raise HTTPException(409, 'Identificador de solicitud ya utilizado.')
                return previa
        conductor = self.db.query(User).filter(User.id == conductor_id).with_for_update().first()
        if conductor is None or conductor.role != "conductor":
            raise HTTPException(status_code=403, detail="Solo los conductores pueden registrar acciones directamente.")

        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == data.vehiculo_id).with_for_update().first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        es_grua = data.accion_tipo == "Operar Grúa"
        if vehiculo.estado == 'inactivo':
            raise HTTPException(409, 'El vehículo está inactivo.')
        if not es_grua and data.km_inicial is not None and data.km_inicial < (vehiculo.kilometraje_actual or 0):
            raise HTTPException(status_code=400, detail="El kilometraje ingresado no puede ser menor al último registrado.")
        es_conduccion = data.accion_tipo == "Empezar a Conducir"
        if es_conduccion and (vehiculo.estado not in {"disponible", "en_ruta"} or vehiculo.estado_semaforo == "rojo"):
            raise HTTPException(status_code=400, detail="El vehículo no está disponible para esta acción.")

        activas = self.db.query(JornadaTransporte).filter(
            JornadaTransporte.conductor_id == conductor_id,
            JornadaTransporte.jornada_padre_id.is_(None),
            JornadaTransporte.estado.in_(["pendiente", "en_curso", "pendiente_de_cierre", "cerrada_por_sistema"]),
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
        salto_km = 0.0 if es_grua or data.km_inicial is None else data.km_inicial - (vehiculo.kilometraje_actual or 0)
        if salto_km > 600 and (not data.odometro_evidencia_url or not data.odometro_motivo):
            raise HTTPException(400, "Un salto mayor a 600 km requiere foto del odómetro y motivo (mínimo 15 caracteres).")
        if not es_grua and data.km_inicial is not None:
            vehiculo.kilometraje_actual = data.km_inicial
        fecha_registro = datetime.utcnow()
        if salto_km > 600:
            for admin in self.db.query(User).filter_by(role='admin').all():
                notificar(self.db, admin.id, f'odometro:{data.solicitud_id or fecha_registro.isoformat()}',
                    'Odómetro por revisar', f'{vehiculo.placa}: salto de {salto_km:.1f} km con evidencia adjunta.')
        es_duracion = data.accion_tipo in {"Operar Grúa", "Trabajos a Externos"}
        if es_duracion and padre and self.db.query(JornadaTransporte).filter(
            JornadaTransporte.jornada_padre_id == padre.id,
            JornadaTransporte.estado == "en_curso",
        ).first():
            raise HTTPException(409, "Ya existe una subacción de duración en curso.")
        if es_conduccion:
            anteriores = self.db.query(JornadaTransporte).filter(
                JornadaTransporte.vehiculo_id == vehiculo.id,
                JornadaTransporte.jornada_padre_id.is_(None),
                JornadaTransporte.estado == "en_curso",
            ).all()
            for anterior in anteriores:
                if self.db.query(JornadaTransporte).filter_by(jornada_padre_id=anterior.id, estado='en_curso').first():
                    raise HTTPException(409, 'Cierre la subacción activa antes del relevo.')
                anterior.estado = "pendiente_de_cierre"
                anterior.fin_operativo = fecha_registro
                notificar(self.db, anterior.conductor_id, f'relevo:{anterior.id}',
                    'Cierre de jornada pendiente', 'Otro conductor tomó el vehículo. Registre su odómetro final.',
                    persistente=True, entidad='jornada', entidad_id=anterior.id)
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
            estado="en_curso" if es_conduccion or es_duracion else "finalizada",
            fecha_inicio=fecha_registro,
            fecha_fin=None if es_conduccion or es_duracion else fecha_registro,
            odometro_evidencia_url=data.odometro_evidencia_url,
            odometro_motivo=data.odometro_motivo,
            odometro_requiere_revision=salto_km > 600,
            solicitud_id=data.solicitud_id,
            fotos_observacion=data.fotos_observacion,
        )

        if es_conduccion:
            vehiculo.estado = "en_ruta"
            
        self.db.add(jornada)
        self.db.flush()
        faltantes = [k for k, valor in (data.checklist_flash or {}).items() if valor is False]
        if faltantes:
            for admin in self.db.query(User).filter_by(role='admin').all():
                notificar(self.db, admin.id, f'checklist:{jornada.id}', 'Faltantes del checklist',
                    ', '.join(faltantes), entidad='jornada', entidad_id=jornada.id)
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
        if self.db.query(JornadaTransporte).filter(JornadaTransporte.conductor_id == conductor.id, JornadaTransporte.estado.in_(["pendiente", "en_curso", "pendiente_de_cierre", "cerrada_por_sistema"]), JornadaTransporte.jornada_padre_id.is_(None)).first():
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
        jornada.checklists.append(Checklist(**data.model_dump(exclude={"tiene_observaciones", "severidad", "foto_observacion", "fotos_observacion", "odometro_evidencia_url", "odometro_motivo"})))
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
        self, jornada_id: int, data: ChecklistCreate, conductor_id: int, usuario_id: int | None = None
    ) -> JornadaTransporte:
        jornada = self.obtener(jornada_id)
        self.db.query(User).filter(User.id == jornada.conductor_id).with_for_update().first()
        self.db.refresh(jornada)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado not in {"en_curso", "pendiente_de_cierre", "cerrada_por_sistema"} or jornada.jornada_padre_id is not None:
            raise HTTPException(status_code=400, detail="Solo se puede finalizar una jornada en curso.")
        if data.tipo != "final":
            raise HTTPException(status_code=400, detail="El checklist de este flujo debe ser final.")
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        es_historica = jornada.estado in {'pendiente_de_cierre', 'cerrada_por_sistema'}
        minimo = (jornada.km_inicial or 0) if es_historica else (vehiculo.kilometraje_actual or 0)
        if data.kilometraje < minimo:
            raise HTTPException(status_code=400, detail="El kilometraje no puede disminuir.")
        if any(a.estado == 'en_curso' for a in jornada.sub_acciones):
            raise HTTPException(409, 'Cierre o cancele las subacciones activas antes de finalizar.')
        semaforo = self._evaluar_semaforo(data)
        jornada.checklists.append(Checklist(**data.model_dump(exclude={"tiene_observaciones", "severidad", "foto_observacion", "fotos_observacion", "odometro_evidencia_url", "odometro_motivo"})))
        if jornada.estado_semaforo != "rojo" or semaforo == "rojo":
            jornada.foto_observacion = data.foto_observacion or jornada.foto_observacion
            jornada.severidad = data.severidad or jornada.severidad
            jornada.observaciones = data.observaciones or jornada.observaciones
            jornada.tiene_observaciones = data.tiene_observaciones or jornada.tiene_observaciones
        distancia = data.kilometraje - (jornada.km_inicial or data.kilometraje)
        if distancia > 600 and (not data.odometro_evidencia_url or not data.odometro_motivo):
            raise HTTPException(400, "Una distancia mayor a 600 km requiere foto del odómetro y motivo (mínimo 15 caracteres).")
        vehiculo.kilometraje_actual = max(vehiculo.kilometraje_actual or 0, data.kilometraje)
        jornada.fotos_observacion = data.fotos_observacion
        jornada.odometro_evidencia_url = data.odometro_evidencia_url
        jornada.odometro_motivo = data.odometro_motivo
        jornada.odometro_requiere_revision = distancia > 600
        jornada.km_final = data.kilometraje
        jornada.estado = "finalizada"
        jornada.fecha_fin = jornada.fin_operativo or jornada.fecha_fin or datetime.utcnow()
        resolver_avisos(self.db, 'jornada', jornada.id)
        self.db.add(AuditoriaSistema(usuario_id=usuario_id or conductor_id, entidad='jornada_transporte',
            registro_id=jornada.id, accion='cierre_jornada', valores_nuevos={'km_final': data.kilometraje}))
        otra_activa = self.db.query(JornadaTransporte).filter(
            JornadaTransporte.vehiculo_id == vehiculo.id,
            JornadaTransporte.id != jornada.id,
            JornadaTransporte.jornada_padre_id.is_(None),
            JornadaTransporte.estado == "en_curso",
        ).first()
        vehiculo.estado = "en_ruta" if otra_activa else "disponible"

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
        self.db.flush()
        self.consolidar_horas(conductor_id, local_time(jornada.fecha_inicio).date())

        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def _calcular_metricas(
        self, jornada: JornadaTransporte, km_inicial: float, km_final: float
    ) -> None:
        """Calcula horas efectivas y km recorridos, generando alertas e incidencias si se superan umbrales."""
        fecha_inicio = local_time(jornada.fecha_inicio or datetime.utcnow())
        fecha_fin = local_time(jornada.fecha_fin or datetime.utcnow())

        duracion_horas = (fecha_fin - fecha_inicio).total_seconds() / 3600.0

        # Descuento de 1 hora de almuerzo si la jornada cruza el mediodía
        descuento_almuerzo = 0.0
        if (fecha_inicio.time() < time(13, 0) <= fecha_fin.time()) or duracion_horas > 8:
            descuento_almuerzo = 1.0

        horas_efectivas = max(0, duracion_horas - descuento_almuerzo)
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

        if km_recorridos > 300:
            jornada.alerta_km = True
            self.db.add(
                IncidenciaRuta(
                    jornada_id=jornada.id,
                    tipo="falla",
                    descripcion=f"Alerta: Kilometraje recorrido excede 300km ({km_recorridos:.1f}km).",
                )
            )

    def consolidar_horas(self, conductor_id, fecha):
        inicio = utc_naive(datetime.combine(fecha, time.min, tzinfo=LIMA))
        fin = inicio + timedelta(days=1)
        jornadas = self.db.query(JornadaTransporte).filter(
            JornadaTransporte.conductor_id == conductor_id,
            JornadaTransporte.jornada_padre_id.is_(None),
            JornadaTransporte.fecha_inicio < fin, JornadaTransporte.fecha_fin > inicio,
            JornadaTransporte.estado.in_(['finalizada', 'cerrada_por_sistema']),
        ).order_by(JornadaTransporte.fecha_inicio, JornadaTransporte.id).all()
        bruto, cruza, duraciones = 0.0, False, []
        mediodia = inicio + timedelta(hours=13)
        for jornada in jornadas:
            a, b = max(inicio, utc_naive(jornada.fecha_inicio)), min(fin, utc_naive(jornada.fecha_fin))
            horas = max(0, (b - a).total_seconds() / 3600)
            duraciones.append(horas)
            bruto += horas
            cruza |= a < mediodia <= b
        descuento = min(1.0, bruto) if cruza or bruto > 8 else 0.0
        restante = descuento
        for jornada, horas in zip(jornadas, duraciones):
            aplicado = min(restante, horas)
            jornada.horas_efectivas = round(horas - aplicado, 2)
            restante -= aplicado
        return {'fecha': fecha, 'conductor_id': conductor_id, 'horas_brutas': round(bruto, 2),
            'refrigerio': descuento, 'horas_efectivas': round(bruto - descuento, 2)}

    def registrar_incidencia(
        self, jornada_id: int, data: IncidenciaRutaCreate, conductor_id: int
    ) -> IncidenciaRuta:
        if data.solicitud_id:
            previa = self.db.query(IncidenciaRuta).filter_by(solicitud_id=data.solicitud_id).first()
            if previa:
                if previa.jornada.conductor_id != conductor_id or previa.jornada_id != jornada_id:
                    raise HTTPException(409, 'Identificador de solicitud ya utilizado.')
                return previa
        jornada = self.obtener(jornada_id)
        self.db.query(User).filter(User.id == jornada.conductor_id).with_for_update().first()
        self.db.refresh(jornada)
        if jornada.conductor_id != conductor_id:
            raise HTTPException(status_code=403, detail="La jornada no pertenece al conductor actual.")
        if jornada.estado != "en_curso":
            if not data.solicitud_id or not data.fecha or not jornada.fecha_inicio or not jornada.fecha_fin or not (
                utc_naive(jornada.fecha_inicio) <= utc_naive(data.fecha) <= utc_naive(jornada.fecha_fin)
            ):
                raise HTTPException(status_code=400, detail="La evidencia offline debe corresponder al intervalo de la jornada.")
        if data.fecha is not None:
            data.fecha = utc_naive(data.fecha)
        if data.severidad is None or not (data.foto_incidencia or data.fotos):
            raise HTTPException(400, "Adjunte la fotografía de la incidencia.")
        incidencia = IncidenciaRuta(**data.model_dump(exclude_none=True), jornada_id=jornada_id)
        if not incidencia.foto_incidencia and data.fotos:
            incidencia.foto_incidencia = data.fotos[0]
        if data.severidad:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
            semaforo = {"leve": "verde", "moderada": "amarillo", "critica": "rojo"}[data.severidad]
            self._aplicar_semaforo(jornada, vehiculo, semaforo, data.descripcion, cerrar=False)
            if jornada.estado_semaforo != "rojo" or data.severidad == "critica":
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
        return {"leve": "verde", "moderada": "amarillo", "critica": "rojo"}.get(
            data.severidad, "verde"
        )

    def cerrar_subaccion(self, jornada_id: int, data: SubaccionCerrar, usuario: User) -> JornadaTransporte:
        self.db.query(User).filter_by(id=usuario.id).with_for_update().first()
        jornada = self.obtener(jornada_id)
        self.db.refresh(jornada)
        if jornada.jornada_padre_id is None or jornada.estado != "en_curso":
            raise HTTPException(400, "La subacción no está en curso.")
        if usuario.role != "admin" and jornada.conductor_id != usuario.id:
            raise HTTPException(403, "No puede cerrar esta subacción.")
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).with_for_update().first()
        if jornada.accion_tipo == "Operar Grúa":
            if data.horometro_final is None or data.horometro_final < jornada.detalles_grua.horometro_inicial:
                raise HTTPException(400, "Ingrese un horómetro final válido.")
            jornada.detalles_grua.horometro_final = data.horometro_final
        else:
            if data.km_final is None or data.km_final < (vehiculo.kilometraje_actual or 0):
                raise HTTPException(400, "El kilometraje no puede disminuir.")
            salto = data.km_final - (vehiculo.kilometraje_actual or 0)
            if salto > 600 and (not data.odometro_evidencia_url or not data.odometro_motivo):
                raise HTTPException(400, "Un salto mayor a 600 km requiere foto y motivo.")
            vehiculo.kilometraje_actual = data.km_final
            jornada.km_final = data.km_final
            jornada.odometro_evidencia_url = data.odometro_evidencia_url
            jornada.odometro_motivo = data.odometro_motivo
            jornada.odometro_requiere_revision = salto > 600
        jornada.estado = "finalizada"
        jornada.fecha_fin = datetime.utcnow()
        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def cancelar_subaccion(self, jornada_id: int, motivo: str, usuario: User) -> JornadaTransporte:
        if len(motivo.strip()) < 10:
            raise HTTPException(400, 'El motivo debe tener al menos 10 caracteres.')
        self.db.query(User).filter_by(id=usuario.id).with_for_update().first()
        jornada = self.obtener(jornada_id)
        self.db.refresh(jornada)
        if jornada.jornada_padre_id is None or jornada.estado != "en_curso":
            raise HTTPException(400, "La subacción no está en curso.")
        if usuario.role != "admin" and jornada.conductor_id != usuario.id:
            raise HTTPException(403, "No puede cancelar esta subacción.")
        jornada.estado = "cancelada"
        jornada.fecha_fin = datetime.utcnow()
        jornada.motivo_cancelacion = motivo.strip()
        jornada.cancelado_por_id = usuario.id
        self.db.add(AuditoriaSistema(
            usuario_id=usuario.id, entidad="jornada_transporte", registro_id=jornada.id,
            accion="cancelacion_subaccion", valores_anteriores={"estado": "en_curso"},
            valores_nuevos={"estado": "cancelada"}, motivo=jornada.motivo_cancelacion,
        ))
        self.db.commit()
        self.db.refresh(jornada)
        return jornada

    def cerrar_jornadas_vencidas(self, ahora: datetime | None = None) -> int:
        ahora = local_time(ahora or datetime.utcnow())
        dia = ahora.date() if ahora.time().replace(tzinfo=None) >= time(23, 59) else (ahora - timedelta(days=1)).date()
        limite = utc_naive(datetime.combine(dia, time(23, 59), tzinfo=LIMA))
        jornadas = self.db.query(JornadaTransporte).filter(
            JornadaTransporte.jornada_padre_id.is_(None),
            JornadaTransporte.estado.in_(["en_curso", "pendiente_de_cierre"]),
            JornadaTransporte.fecha_inicio <= limite,
        ).all()
        for jornada in jornadas:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == jornada.vehiculo_id).first()
            jornada.estado = "cerrada_por_sistema"
            jornada.cerrado_por_sistema = True
            jornada.fecha_fin = jornada.fin_operativo or limite
            jornada.km_final = vehiculo.kilometraje_actual if vehiculo else jornada.km_inicial
            for sub in jornada.sub_acciones:
                if sub.estado == 'en_curso':
                    sub.estado = 'cancelada'
                    sub.motivo_cancelacion = 'Cierre automático nocturno; actividad sin cierre.'
                    sub.fecha_fin = limite
            self._calcular_metricas(jornada, jornada.km_inicial or 0, jornada.km_final or 0)
            self.db.flush()
            self.consolidar_horas(jornada.conductor_id, local_time(jornada.fecha_inicio).date())
            if vehiculo and vehiculo.estado == 'en_ruta':
                vehiculo.estado = 'disponible'
            self.db.add(AuditoriaSistema(
                entidad="jornada_transporte", registro_id=jornada.id,
                accion="cierre_automatico", valores_nuevos={"estado": "cerrada_por_sistema"},
                motivo="Cierre nocturno automático; odómetro pendiente de regularización.",
            ))
        self.db.commit()
        return len(jornadas)

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
