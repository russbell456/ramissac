from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.rq_item_model import RQItem
from app.models.orden_compra_model import OrdenCompraItem
from sqlalchemy import func


class RQItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, item: RQItem):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
    def get_items_pendientes_global(self):
        """
        Retorna todos los RQItems con cantidad pendiente > 0
        """

        resultados = (
            self.db.query(
                RQItem.id.label("rq_item_id"),
                RQItem.codigo,
                RQItem.descripcion,
                RQItem.cantidad.label("cantidad_requerida"),
                RQItem.rq_id,
                func.coalesce(func.sum(OrdenCompraItem.cantidad_comprada), 0).label("cantidad_comprada")
            )
            .outerjoin(OrdenCompraItem, OrdenCompraItem.rq_item_id == RQItem.id)
            .group_by(RQItem.id)
            .all()
        )

        items_pendientes = []

        for r in resultados:
            pendiente = r.cantidad_requerida - r.cantidad_comprada
            if pendiente > 0:
                items_pendientes.append({
                    "rq_item_id": r.rq_item_id,
                    "codigo": r.codigo,
                    "descripcion": r.descripcion,
                    "cantidad_requerida": float(r.cantidad_requerida),
                    "cantidad_comprada": float(r.cantidad_comprada),
                    "cantidad_pendiente": float(pendiente),
                    "rq_id": r.rq_id
                })

        return items_pendientes

    def get_by_rq(self, rq_id: int):
        return self.db.query(RQItem).filter(RQItem.rq_id == rq_id).all()

    def get_by_id(self, item_id: int):
        return self.db.query(RQItem).filter(RQItem.id == item_id).first()

    def update_estado(self, item_id: int, estado: str):
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.estado = estado
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item_id: int):
        item = self.get_by_id(item_id)
        if not item:
            return None
        self.db.delete(item)
        self.db.commit()
        return item
