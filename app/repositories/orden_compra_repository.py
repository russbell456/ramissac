from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.orden_compra_model import OrdenCompra, OrdenCompraComprobante, OrdenCompraItem # Importar nuevos modelos
from app.models.rq_item_model import RQItem
from datetime import datetime
from sqlalchemy.orm import joinedload
from app.schemas.orden_compra_schema import OrdenCompraCreate
from typing import Optional, List, Dict, Any
from app.services.rq_service import RQService
from fastapi import HTTPException
from app.repositories.rq_item_repository import RQItemRepository
# Asegúrate de importar HTTPException, RQService, y los repositorios/modelos necesarios. # Para tipado

# --- REPOSITORIO DE CABECERA (Adaptación de OrdenCompraParcial) ---
class OrdenCompraRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, orden: OrdenCompra) -> OrdenCompra:
        """Crea la cabecera de la orden."""
        self.db.add(orden)
        self.db.flush() # Importante para obtener el ID antes del commit final
        self.db.refresh(orden)
        return orden

    def get_by_id(self, orden_id: int) -> Optional[OrdenCompra]:
        # Carga las relaciones necesarias para la entidad
        return self.db.query(OrdenCompra).options(
            joinedload(OrdenCompra.comprobantes),
            joinedload(OrdenCompra.items_comprados)
        ).filter(OrdenCompra.id == orden_id).first()
    
    def get_by_item(self, rq_item_id: int):
        """Busca órdenes por item usando la nueva tabla de detalle."""
        return self.db.query(OrdenCompra).join(OrdenCompraItem).filter(
            OrdenCompraItem.rq_item_id == rq_item_id
        ).all()


    def update(self, orden_id: int, **kwargs):
        orden = self.get_by_id(orden_id)
        if not orden:
            return None
        for key, value in kwargs.items():
            setattr(orden, key, value)
        self.db.commit()
        self.db.refresh(orden)
        return orden

    def delete(self, orden_id: int):
        orden = self.get_by_id(orden_id)
        if not orden:
            return None
        self.db.delete(orden)
        self.db.commit()
        return orden
    
    def listar_ordenes_resumen(self, estado=None, fecha_inicio=None, fecha_fin=None):
            """
            Lista órdenes, uniendo las tablas para obtener la información del RQItem.
            CLAVE: Uso de select_from() y cláusulas ON explícitas.
            """
            # Usamos .select_from(OrdenCompra) para establecer el inicio de la consulta.
            query = self.db.query(OrdenCompra, OrdenCompraItem, RQItem).select_from(OrdenCompra).join(
                # JOIN explícito de OrdenCompra a OrdenCompraItem
                OrdenCompraItem, 
                OrdenCompra.id == OrdenCompraItem.orden_compra_id 
            ).join(
                # JOIN explícito de OrdenCompraItem a RQItem
                RQItem,
                OrdenCompraItem.rq_item_id == RQItem.id 
            )

            # El resto de filtros se aplica a OrdenCompra
            if estado:
                query = query.filter(OrdenCompra.estado == estado)
            
            # Lógica de filtros de fecha
            # Asumo que las fechas están en formato YYYY-MM-DD
            if fecha_inicio:
                query = query.filter(OrdenCompra.fecha >= fecha_inicio)
            if fecha_fin:
                query = query.filter(OrdenCompra.fecha <= fecha_fin)
                
            return query.all()
    
# --- NUEVO REPOSITORIO DE DETALLE ---
class OrdenCompraItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, item: OrdenCompraItem) -> OrdenCompraItem:
        self.db.add(item)
        # El commit lo hace el service al final.
        self.db.flush() 
        return item
    def get_by_id(self, item_id: int) -> Optional[OrdenCompraItem]:
        """Obtiene un detalle de ítem de Orden de Compra por su ID."""
        return self.db.query(OrdenCompraItem).filter(OrdenCompraItem.id == item_id).first()
    def delete_by_orden_id(self, orden_id: int):
        """Elimina todos los ítems asociados a una Orden de Compra."""
        self.db.query(OrdenCompraItem).filter(
            OrdenCompraItem.orden_compra_id == orden_id
        ).delete(synchronize_session="auto")
        
# --- REPOSITORIO DE COMPROBANTE (Ajustado) ---
class OrdenCompraComprobanteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, comprobante: OrdenCompraComprobante):
        # ⚠️ Ya no usa orden_parcial_id, ahora usa orden_compra_id
        self.db.add(comprobante)
        self.db.flush() # Flush temporal
        return comprobante
        
    # ... (get_by_orden y delete_by_orden se ajustan internamente) ...
    def delete_by_orden(self, orden_compra_id: int):
        self.db.query(OrdenCompraComprobante).filter(
            OrdenCompraComprobante.orden_compra_id == orden_compra_id
        ).delete()
        self.db.flush()
        return True