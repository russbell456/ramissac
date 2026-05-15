from __future__ import annotations

from sqlalchemy.orm import Session, selectinload # 💡 Importación de selectinload
from app.models.rq_model import Requerimiento
from app.models.rq_item_model import RQItem # 💡 Necesario para la carga anticipada



class RQRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, rq: Requerimiento):
        self.db.add(rq)
        self.db.commit()
        self.db.refresh(rq)
        return rq
    
    def get_all(self):
        """
        Obtiene todos los RQs con Eager Loading.
        """
        return self.db.query(Requerimiento).options(
            selectinload(Requerimiento.items).selectinload(
                RQItem.ordenes_compra_items
            )
        ).all()

    def get_by_id(self, rq_id: int):
        """
        MÉTODO CORREGIDO: Implementa Eager Loading (selectinload) 
        para cargar los items y las órdenes de compra asociadas 
        en la misma consulta. Esto previene el error.
        """
        return self.db.query(Requerimiento).options(
            # Carga el nivel 1: Requerimiento.items
            selectinload(Requerimiento.items).selectinload(
                # Carga el nivel 2: RQItem.ordenes_compra_items
                RQItem.ordenes_compra_items 
            )
        ).filter(Requerimiento.id == rq_id).first()

    def update_estado(self, rq_id: int, estado: str):
        # Es recomendable usar el método con Eager Loading aquí también
        rq = self.get_by_id(rq_id) 
        if not rq:
            return None
        rq.estado = estado
        self.db.commit()
        self.db.refresh(rq)
        return rq

    def delete(self, rq_id: int):
        # Es recomendable usar el método con Eager Loading aquí también
        rq = self.get_by_id(rq_id)
        if not rq:
            return None
        self.db.delete(rq)
        self.db.commit()
        return rq