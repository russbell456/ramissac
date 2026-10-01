from __future__ import annotations

from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.mantenimiento import Mantenimiento
from app.models.vehiculo import Vehiculo
from app.models.averia import Averia
from app.models.inspeccion import Inspeccion
from app.models.mantenimiento_plan import PlanMantenimiento
from app.models.user import User
from app.models.transportes_enums import TipoControlMantenimiento
from app.schemas.mantenimiento_schema import MantenimientoCreate, MantenimientoUpdate

class MantenimientoService:
    def __init__(self, db: Session):
        self.db = db

    def get_mantenimiento_by_id(self, mantenimiento_id: int) -> Mantenimiento:
        mantenimiento = self.db.query(Mantenimiento).filter(
            Mantenimiento.id == mantenimiento_id,
            Mantenimiento.estado != "inactivo"
        ).options(
            joinedload(Mantenimiento.vehiculo),
            joinedload(Mantenimiento.mecanico),
        ).first()
        if not mantenimiento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de mantenimiento no encontrado."
            )
        return mantenimiento

    def get_all_mantenimientos(self) -> list[Mantenimiento]:
        return self.db.query(Mantenimiento).options(
            joinedload(Mantenimiento.vehiculo),
            joinedload(Mantenimiento.mecanico),
        ).filter(Mantenimiento.fecha_baja.is_(None)).all()

    def create_mantenimiento(self, schema: MantenimientoCreate) -> Mantenimiento:
        # Verificar que el vehículo exista
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id,
            Vehiculo.estado != "inactivo"
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # Si el vehículo ya está en mantenimiento o en ruta, lanzar una advertencia/error de negocio
        if vehiculo.estado == "en_ruta":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede enviar a mantenimiento un vehículo que está actualmente en ruta."
            )

        # Validar avería asociada si corresponde
        if schema.averia_id is not None:
            averia = self.db.query(Averia).filter(Averia.id == schema.averia_id).first()
            if not averia:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Avería asociada no encontrada."
                )

        # Crear registro de mantenimiento
        nuevo_mantenimiento = Mantenimiento(
            vehiculo_id=schema.vehiculo_id,
            fecha_ingreso=schema.fecha_ingreso,
            descripcion_falla=schema.descripcion_falla,
            costo=schema.costo,
            tipo=schema.tipo,
            averia_id=schema.averia_id,
            plan_id=schema.plan_id,
            tipo_control=schema.tipo_control,
            intervalo_kilometraje=schema.intervalo_kilometraje,
            intervalo_dias=schema.intervalo_dias,
            intervalo_horas=schema.intervalo_horas,
            mecanico_id=schema.mecanico_id,
            kilometraje_mantenimiento=schema.kilometraje_mantenimiento,
            proximo_kilometraje_mantenimiento=schema.proximo_kilometraje_mantenimiento,
            fecha=schema.fecha or schema.fecha_ingreso,
            descripcion_trabajo=schema.descripcion_trabajo,
            estado="en_taller"
        )

        # Cambiar estado del vehículo a "en_mantenimiento"
        vehiculo.estado = "en_mantenimiento"

        self.db.add(nuevo_mantenimiento)
        self.db.commit()
        self.db.refresh(nuevo_mantenimiento)
        return nuevo_mantenimiento

    def update_mantenimiento(self, mantenimiento_id: int, schema: MantenimientoUpdate) -> Mantenimiento:
        mantenimiento = self.get_mantenimiento_by_id(mantenimiento_id)

        if schema.fecha_ingreso is not None:
            mantenimiento.fecha_ingreso = schema.fecha_ingreso
        if schema.descripcion_falla is not None:
            mantenimiento.descripcion_falla = schema.descripcion_falla
        if schema.costo is not None:
            mantenimiento.costo = schema.costo
        if schema.tipo is not None:
            mantenimiento.tipo = schema.tipo
        if schema.descripcion_trabajo is not None:
            mantenimiento.descripcion_trabajo = schema.descripcion_trabajo
        if schema.fecha_cierre is not None:
            mantenimiento.fecha_cierre = schema.fecha_cierre
        if schema.observaciones_ejecucion is not None:
            mantenimiento.observaciones_ejecucion = schema.observaciones_ejecucion
        if schema.km_ejecucion is not None:
            mantenimiento.km_ejecucion = schema.km_ejecucion
        if schema.horas_ejecucion is not None:
            mantenimiento.horas_ejecucion = schema.horas_ejecucion
        if schema.trabajador_id is not None:
            mantenimiento.trabajador_id = schema.trabajador_id
        if schema.mecanico_id is not None:
            mantenimiento.mecanico_id = schema.mecanico_id
        if schema.kilometraje_mantenimiento is not None:
            mantenimiento.kilometraje_mantenimiento = schema.kilometraje_mantenimiento
        if schema.proximo_kilometraje_mantenimiento is not None:
            if schema.proximo_kilometraje_mantenimiento < mantenimiento.kilometraje_mantenimiento:
                raise HTTPException(
                    status_code=400,
                    detail="El próximo kilometraje debe ser mayor o igual al kilometraje de mantenimiento.",
                )
            mantenimiento.proximo_kilometraje_mantenimiento = schema.proximo_kilometraje_mantenimiento
        if schema.fecha is not None:
            mantenimiento.fecha = schema.fecha

        if schema.estado is not None:
            mantenimiento.estado = schema.estado
            # Al completarse el mantenimiento, el vehículo pasa a OBSERVADO,
            # NO directamente a disponible. Se requiere una inspección
            # POST_MANTENIMIENTO aprobada para liberarlo a disponible.
            if schema.estado == "completado":
                vehiculo = self.db.query(Vehiculo).filter(
                    Vehiculo.id == mantenimiento.vehiculo_id
                ).first()
                if vehiculo and vehiculo.estado == "en_mantenimiento":
                    vehiculo.estado = "observado"
                if mantenimiento.fecha_cierre is None:
                    mantenimiento.fecha_cierre = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(mantenimiento)
        return mantenimiento

    def crear_preventivo(self, schema: MantenimientoCreate, usuario_id: int) -> Mantenimiento:
        """Crea un preventivo y calcula NORMAL/PROXIMO/VENCIDO.

        Para MIXTO basta con que se cumpla primero cualquiera de los umbrales.
        """
        schema.tipo = "PREVENTIVO"
        if schema.plan_id is None:
            raise HTTPException(status_code=400, detail="plan_id es obligatorio para preventivo.")
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id, Vehiculo.fecha_baja.is_(None)
        ).first()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        plan = self.db.query(PlanMantenimiento).filter(
            PlanMantenimiento.id == schema.plan_id, PlanMantenimiento.activo.is_(True)
        ).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan de mantenimiento no encontrado.")
        tipo_control = schema.tipo_control or plan.tipo_control
        km_umbral = schema.intervalo_kilometraje or plan.intervalo_kilometraje
        dias_umbral = schema.intervalo_dias or plan.intervalo_dias
        horas_umbral = schema.intervalo_horas or plan.intervalo_horas
        ahora = datetime.utcnow()
        vencido = False
        proximo = False
        if tipo_control in ("kilometraje", "mixto") and km_umbral is not None:
            vencido |= vehiculo.kilometraje_actual >= km_umbral
            proximo |= vehiculo.kilometraje_actual >= km_umbral * 0.8
        if tipo_control in ("fecha", "mixto") and dias_umbral is not None:
            dias = (ahora - schema.fecha_ingreso).days
            vencido |= dias >= dias_umbral
            proximo |= dias >= max(dias_umbral - 7, 0)
        if tipo_control == "horas" and horas_umbral is not None:
            proximo = False
        estado_control = "VENCIDO" if vencido else "PROXIMO" if proximo else "NORMAL"
        nuevo = Mantenimiento(
            vehiculo_id=schema.vehiculo_id, plan_id=schema.plan_id,
            fecha_ingreso=schema.fecha_ingreso, descripcion_falla=schema.descripcion_falla,
            costo=schema.costo, tipo="PREVENTIVO", estado="en_taller",
            tipo_control=tipo_control, intervalo_kilometraje=km_umbral,
            intervalo_dias=dias_umbral, intervalo_horas=horas_umbral,
            descripcion_trabajo=f"Estado de control: {estado_control}",
        )
        self.db.add(nuevo)
        self.db.commit()
        self.db.refresh(nuevo)
        return nuevo

    def ejecutar_mantenimiento(self, mantenimiento_id: int, trabajador_id: int,
                                km_ejecucion: float, horas_ejecucion: float = 0.0,
                                observaciones: str | None = None) -> Mantenimiento:
        mantenimiento = self.get_mantenimiento_by_id(mantenimiento_id)
        trabajador = self.db.query(User).filter(User.id == trabajador_id).first()
        if not trabajador:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado.")
        mantenimiento.km_ejecucion = km_ejecucion
        mantenimiento.horas_ejecucion = horas_ejecucion
        mantenimiento.trabajador_id = trabajador_id
        mantenimiento.observaciones_ejecucion = observaciones
        mantenimiento.estado = "completado"
        mantenimiento.fecha_cierre = datetime.utcnow()
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == mantenimiento.vehiculo_id).first()
        if vehiculo and vehiculo.estado == "en_mantenimiento":
            vehiculo.estado = "observado"
        self.db.commit()
        self.db.refresh(mantenimiento)
        return mantenimiento

    def delete_mantenimiento(self, mantenimiento_id: int, usuario_id: int) -> dict:
        mantenimiento = self.get_mantenimiento_by_id(mantenimiento_id)
        mantenimiento.estado = "inactivo"
        mantenimiento.fecha_baja = datetime.now(timezone.utc)
        mantenimiento.usuario_baja = usuario_id
        self.db.commit()
        return {"detail": "Mantenimiento marcado como inactivo correctamente."}
