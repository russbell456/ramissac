from __future__ import annotations

from sqlalchemy.orm import Session
from app.repositories.rq_repository import RQRepository
from app.repositories.rq_item_repository import RQItemRepository
from app.models.rq_model import Requerimiento
from app.models.rq_item_model import RQItem
from datetime import date

class RQService:
    def __init__(self, db: Session):
        self.db = db
        self.rq_repo = RQRepository(db)
        self.item_repo = RQItemRepository(db)

    def create_rq(self, rq_data: dict):
        rq = Requerimiento(
            nro_rq=rq_data["nro_rq"],
            proyecto=rq_data["proyecto"],
            solicitante=rq_data["solicitante"],
            fecha_emision=rq_data.get("fecha_emision", date.today()),
            estado=rq_data.get("estado", "pendiente")
        )
        self.rq_repo.create(rq)

        items = rq_data.get("items", [])
        for i in items:
            item = RQItem(
                codigo=i["codigo"],
                descripcion=i["descripcion"],
                cantidad=i["cantidad"],
                unidad=i["unidad"],
                rq_id=rq.id
            )
            self.item_repo.create(item)

        return rq

    def get_all_rqs(self):
        return self.rq_repo.get_all()

    def get_rq(self, rq_id: int):
        rq = self.rq_repo.get_by_id(rq_id)
        if not rq:
            raise ValueError("RQ no encontrada")
        return rq
    def listar_items_pendientes_compra(self, rq_id: int):
        rq = self.rq_repo.get_by_id(rq_id)
        if not rq:
            raise ValueError("RQ no encontrada")

        items_pendientes = []

        for item in rq.items:
            cantidad_total = item.cantidad

            # ya lo usas en otros métodos → correcto
            cantidad_comprada = sum(
                [op.cantidad_comprada for op in item.ordenes_compra_items]
            )

            cantidad_pendiente = max(0, cantidad_total - cantidad_comprada)

            # 🔑 ESTA ES LA CONDICIÓN CLAVE
            if cantidad_pendiente > 0:
                items_pendientes.append({
                    "rq_item_id": item.id,
                    "codigo": item.codigo,
                    "descripcion": item.descripcion,
                    "cantidad_requerida": cantidad_total,
                    "cantidad_comprada": cantidad_comprada,
                    "cantidad_pendiente": cantidad_pendiente
                })

        return items_pendientes

    def update_rq_estado(self, rq_id: int, estado: str):
        if estado not in ["pendiente", "aprobado", "rechazado"]:
            raise ValueError("Estado inválido")

        rq = self.rq_repo.update_estado(rq_id, estado)
        if not rq:
            raise ValueError("RQ no encontrada")
        return rq

    def delete_rq(self, rq_id: int):
        rq = self.rq_repo.delete(rq_id)
        if not rq:
            raise ValueError("RQ no encontrada")
        return rq
    
    def actualizar_estado_compra(self, rq_id: int):
        rq = self.rq_repo.get_by_id(rq_id)
        if not rq:
            return

        total_items = len(rq.items)
        if total_items == 0:
            rq.estado_compra = "sin_compras"
            rq.progreso_compra = 0
            self.db.commit()
            self.db.refresh(rq)
            return rq

        items_completados = 0
        suma_porcentajes_items = 0

        for item in rq.items:
            cantidad_total = item.cantidad
            compras = sum([op.cantidad_comprada for op in item.ordenes_compra_items])

            # Calcular % por ítem
            if cantidad_total > 0:
                porcentaje_item = min(100, (compras / cantidad_total) * 100)
            else:
                porcentaje_item = 0

            suma_porcentajes_items += porcentaje_item

            # ítem completado
            if compras >= cantidad_total:
                items_completados += 1

        # ---- Calcular progreso general de la RQ ----
        progreso_total = round(suma_porcentajes_items / total_items, 2)
        rq.progreso_compra = progreso_total

        # ---- Asignación del estado ----
        if progreso_total == 0:
            rq.estado_compra = "sin_compras"
        elif progreso_total < 100:
            rq.estado_compra = "parcial"
        else:
            rq.estado_compra = "completo"

        self.db.commit()
        self.db.refresh(rq)
        return rq
    
    def obtener_estado_compra(self, rq_id: int):
        rq = self.rq_repo.get_by_id(rq_id)
        if not rq:
            raise ValueError("Requerimiento no encontrado")

        items_respuesta = []
        suma_porcentajes = 0

        for item in rq.items:
            cantidad_total = item.cantidad
            # 💡 CORRECCIÓN APLICADA: Se usa 'ordenes_compra_items' en lugar de 'ordenes_parciales'
            cantidad_comprada = sum([op.cantidad_comprada for op in item.ordenes_compra_items])
            cantidad_faltante = max(0, cantidad_total - cantidad_comprada)

            if cantidad_total > 0:
                progreso = min(100, (cantidad_comprada / cantidad_total) * 100)
            else:
                progreso = 0

            suma_porcentajes += progreso

            items_respuesta.append({
                "item_id": item.id,
                "codigo": item.codigo,
                "descripcion": item.descripcion,
                "cantidad_pedida": cantidad_total,
                "cantidad_comprada": cantidad_comprada,
                "cantidad_faltante": cantidad_faltante,
                "progreso": round(progreso, 2)
            })

        if len(rq.items) > 0:
            progreso_general = round(suma_porcentajes / len(rq.items), 2)
        else:
            progreso_general = 0

        return {
            "rq_id": rq.id,
            "nro_rq": rq.nro_rq,
            "estado_compra": rq.estado_compra,
            "progreso_compra": progreso_general,
            "items": items_respuesta
        }