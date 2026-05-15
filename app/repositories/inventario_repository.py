from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.inventario_model import Inventario 
from typing import Optional, Dict, Any

class InventarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_codigo(self, codigo: str) -> Optional[Inventario]:
        """Busca un producto en inventario por su código único."""
        return self.db.query(Inventario).filter(Inventario.codigo == codigo).first()

    def create(self, **kwargs) -> Inventario:
        """Crea una nueva entrada de producto en el inventario."""
        new_item = Inventario(**kwargs)
        self.db.add(new_item)
        self.db.flush() 
        self.db.refresh(new_item)
        return new_item

    def update_cantidad(self, item_id: int, nueva_cantidad: int) -> Optional[Inventario]:
        """Actualiza la cantidad disponible de un ítem de inventario."""
        item = self.db.query(Inventario).filter(Inventario.id == item_id).first()
        if item:
            item.cantidad_disponible = nueva_cantidad
            # No se hace commit aquí, el commit final lo hará el servicio de OrdenCompra.
            self.db.flush() 
        return item