from __future__ import annotations

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.models.vehiculo import Vehiculo
from app.models.auditoria_sistema import AuditoriaSistema
from app.models.jornada_transporte import JornadaTransporte
from app.schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate

class VehiculoService:
    def __init__(self, db: Session):
        self.db = db

    def get_vehiculo_by_id(self, vehiculo_id: int) -> Vehiculo:
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == vehiculo_id,
            Vehiculo.estado != "inactivo"
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )
        return vehiculo

    def get_all_vehiculos(self) -> list[Vehiculo]:
        return self.db.query(Vehiculo).filter(Vehiculo.estado != "inactivo").all()

    def create_vehiculo(self, schema: VehiculoCreate) -> Vehiculo:
        # Verificar si la placa ya está registrada
        existente = self.db.query(Vehiculo).filter(Vehiculo.placa == schema.placa).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La placa ya está registrada."
            )

        nuevo_vehiculo = Vehiculo(**schema.model_dump(), estado="disponible")
        self.db.add(nuevo_vehiculo)
        self.db.commit()
        self.db.refresh(nuevo_vehiculo)
        return nuevo_vehiculo

    def update_vehiculo(self, vehiculo_id: int, schema: VehiculoUpdate) -> Vehiculo:
        vehiculo = self.get_vehiculo_by_id(vehiculo_id)

        if schema.placa is not None:
            if schema.placa != vehiculo.placa and self.db.query(JornadaTransporte).filter(JornadaTransporte.vehiculo_id == vehiculo_id).first():
                raise HTTPException(409, "La placa no puede modificarse porque el vehículo ya tiene jornadas registradas.")
            # Verificar que la nueva placa no esté en uso por otro vehículo
            placa_existente = self.db.query(Vehiculo).filter(
                Vehiculo.placa == schema.placa,
                Vehiculo.id != vehiculo_id
            ).first()
            if placa_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La placa ya está en uso por otro vehículo."
                )
            vehiculo.placa = schema.placa

        if schema.tipo is not None:
            vehiculo.tipo = schema.tipo
        if schema.capacidad_tanque_galones is not None:
            vehiculo.capacidad_tanque_galones = schema.capacidad_tanque_galones
        if schema.marca is not None:
            vehiculo.marca = schema.marca
        if schema.modelo is not None:
            vehiculo.modelo = schema.modelo
        if schema.capacidad_carga is not None:
            vehiculo.capacidad_carga = schema.capacidad_carga
        for campo in ("soat_vencimiento", "rt_vencimiento", "tarjeta_propiedad_url", "poliza_vencimiento", "pase_minero_vencimiento"):
            valor = getattr(schema, campo)
            if valor is not None:
                raise HTTPException(409, 'Renueve los documentos desde el historial documental para conservar sus versiones.')

        # Kilometraje monotónico: nunca puede disminuir.
        if schema.kilometraje_actual is not None:
            raise HTTPException(409, 'Use la corrección de kilometraje con motivo y auditoría.')

        self.db.commit()
        self.db.refresh(vehiculo)
        return vehiculo

    def delete_vehiculo(self, vehiculo_id: int, usuario_id: int) -> dict:
        vehiculo = self.get_vehiculo_by_id(vehiculo_id)
        if self.db.query(JornadaTransporte).filter(JornadaTransporte.vehiculo_id == vehiculo_id,
            JornadaTransporte.estado.in_(['pendiente', 'en_curso', 'pendiente_de_cierre', 'cerrada_por_sistema'])).first():
            raise HTTPException(409, 'Regularice las jornadas pendientes antes de dar de baja la unidad.')
        estado_anterior = vehiculo.estado
        vehiculo.estado = "inactivo"
        vehiculo.fecha_baja = datetime.now(timezone.utc)
        vehiculo.usuario_baja = usuario_id
        self.db.add(AuditoriaSistema(
            usuario_id=usuario_id, entidad="vehiculo", registro_id=vehiculo.id,
            accion="baja_logica", valores_anteriores={"estado": estado_anterior},
            valores_nuevos={"estado": "inactivo"}, motivo="Baja lógica solicitada por administrador.",
        ))
        self.db.commit()
        return {"detail": "Vehículo marcado como inactivo correctamente."}

    def corregir_kilometraje(self, vehiculo_id: int, kilometraje: float, motivo: str, usuario_id: int) -> Vehiculo:
        vehiculo = self.get_vehiculo_by_id(vehiculo_id)
        ultima = self.db.query(JornadaTransporte).filter(
            JornadaTransporte.vehiculo_id == vehiculo_id,
            JornadaTransporte.fecha_fin.isnot(None),
        ).order_by(JornadaTransporte.fecha_fin.desc()).first()
        activa = self.db.query(JornadaTransporte).filter(JornadaTransporte.vehiculo_id == vehiculo_id,
            JornadaTransporte.estado.in_(['pendiente', 'en_curso', 'pendiente_de_cierre'])).first()
        if activa:
            raise HTTPException(409, 'Cierre las jornadas activas antes de corregir el odómetro.')
        if ultima and datetime.now(timezone.utc) - ultima.fecha_fin.replace(tzinfo=ultima.fecha_fin.tzinfo or timezone.utc) > timedelta(hours=72):
            raise HTTPException(409, "El plazo de 72 horas para corregir el kilometraje venció.")
        anterior = vehiculo.kilometraje_actual
        vehiculo.kilometraje_actual = kilometraje
        self.db.add(AuditoriaSistema(
            usuario_id=usuario_id, entidad="vehiculo", registro_id=vehiculo.id,
            accion="correccion_kilometraje", valores_anteriores={"kilometraje_actual": anterior},
            valores_nuevos={"kilometraje_actual": kilometraje}, motivo=motivo.strip(),
        ))
        self.db.commit()
        self.db.refresh(vehiculo)
        return vehiculo
