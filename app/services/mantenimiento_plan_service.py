from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.mantenimiento_plan import (
    PlanMantenimiento,
    PlanDetalleMantenimiento,
)
from app.models.vehiculo import Vehiculo
from app.schemas.mantenimiento_schema import (
    PlanMantenimientoCreate,
    PlanMantenimientoUpdate,
)


class PlanMantenimientoService:
    """Gestión de planes de mantenimiento preventivo.

    Soporta control por kilometraje, fecha, horas y control mixto.
    En control mixto se considera la primera condición que se cumpla.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_plan_by_id(self, plan_id: int) -> PlanMantenimiento:
        plan = self.db.query(PlanMantenimiento).filter(
            PlanMantenimiento.id == plan_id
        ).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan de mantenimiento no encontrado.",
            )
        return plan

    def get_all_planes(self) -> list[PlanMantenimiento]:
        return self.db.query(PlanMantenimiento).all()

    def get_planes_por_vehiculo(self, vehiculo_id: int) -> list[PlanMantenimiento]:
        return (
            self.db.query(PlanMantenimiento)
            .filter(PlanMantenimiento.vehiculo_id == vehiculo_id)
            .all()
        )

    def create_plan(self, schema: PlanMantenimientoCreate) -> PlanMantenimiento:
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id,
            Vehiculo.estado != "inactivo",
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado.",
            )

        if schema.tipo_control == "mixto":
            # Control mixto requiere al menos dos umbrales definidos.
            umbrales = [
                schema.intervalo_kilometraje,
                schema.intervalo_dias,
                schema.intervalo_horas,
            ]
            if sum(1 for u in umbrales if u is not None) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El control mixto requiere al menos dos umbrales.",
                )
        else:
            # Control individual requiere su umbral correspondiente.
            columna = {
                "kilometraje": schema.intervalo_kilometraje,
                "fecha": schema.intervalo_dias,
                "horas": schema.intervalo_horas,
            }.get(schema.tipo_control)
            if columna is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Falta el umbral para el tipo de control indicado.",
                )

        plan = PlanMantenimiento(
            vehiculo_id=schema.vehiculo_id,
            nombre=schema.nombre,
            descripcion=schema.descripcion,
            tipo_control=schema.tipo_control,
            intervalo_kilometraje=schema.intervalo_kilometraje,
            intervalo_dias=schema.intervalo_dias,
            intervalo_horas=schema.intervalo_horas,
            estado_control="NORMAL",
            activo=True,
        )
        for det in schema.detalles:
            plan.detalles.append(
                PlanDetalleMantenimiento(
                    descripcion=det.descripcion,
                    orden=det.orden,
                )
            )

        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_plan(self, plan_id: int, schema: PlanMantenimientoUpdate) -> PlanMantenimiento:
        plan = self.get_plan_by_id(plan_id)

        if schema.nombre is not None:
            plan.nombre = schema.nombre
        if schema.descripcion is not None:
            plan.descripcion = schema.descripcion
        if schema.tipo_control is not None:
            plan.tipo_control = schema.tipo_control
        if schema.intervalo_kilometraje is not None:
            plan.intervalo_kilometraje = schema.intervalo_kilometraje
        if schema.intervalo_dias is not None:
            plan.intervalo_dias = schema.intervalo_dias
        if schema.intervalo_horas is not None:
            plan.intervalo_horas = schema.intervalo_horas
        if schema.estado_control is not None:
            plan.estado_control = schema.estado_control
        if schema.activo is not None:
            plan.activo = schema.activo

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def evaluar_control(
        self,
        plan: PlanMantenimiento,
        *,
        vehiculo_kilometraje: float,
        ultima_ejecucion: datetime | None,
        horas_operacion: float = 0.0,
    ) -> str:
        """Devuelve el estado de control (NORMAL, PROXIMO, VENCIDO).

        En control mixto se considera la primera condición que se cumpla
        (la más restrictiva).
        """
        vencido = []
        proximo = []

        # Por kilometraje
        if plan.intervalo_kilometraje:
            umbral = plan.intervalo_kilometraje
            vencido.append(vehiculo_kilometraje >= umbral)
            proximo.append(vehiculo_kilometraje >= umbral * 0.9)

        # Por fecha (días desde la última ejecución)
        if plan.intervalo_dias:
            base = ultima_ejecucion or datetime.utcnow()
            dias = (datetime.utcnow() - base).days
            vencido.append(dias >= plan.intervalo_dias)
            proximo.append(dias >= plan.intervalo_dias * 0.9)

        # Por horas de operación
        if plan.intervalo_horas:
            vencido.append(horas_operacion >= plan.intervalo_horas)
            proximo.append(horas_operacion >= plan.intervalo_horas * 0.9)

        if any(vencido):
            return "VENCIDO"
        if any(proximo):
            return "PROXIMO"
        return "NORMAL"

