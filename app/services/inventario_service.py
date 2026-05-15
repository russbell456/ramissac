from __future__ import annotations

from sqlalchemy.orm import Session
from app.repositories.inventario_repository import InventarioRepository
from app.models.inventario_model import Inventario
from typing import Optional, List # 💡 Asegúrate de importar List

class InventarioService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InventarioRepository(db) 

    # --- NUEVO MÉTODO PARA LEER EL INVENTARIO ---
    def listar_inventario(self) -> List[Inventario]:
        """Obtiene todos los ítems de la tabla Inventario."""
        return self.db.query(Inventario).all()
        
    # --- Métodos de escritura existentes (Entrada/Salida) ---
    def registrar_entrada_compra(self, codigo_producto: str, descripcion: str, cantidad_recibida: int, ubicacion: str = "N/A") -> Optional[Inventario]:
        """Aumenta el stock cuando se recibe una Orden de Compra."""
        if cantidad_recibida <= 0:
            return None
            
        inventario_item = self.repo.get_by_codigo(codigo_producto)
        
        if inventario_item:
            inventario_item.cantidad_disponible += cantidad_recibida
            self.repo.update_cantidad(inventario_item.id, inventario_item.cantidad_disponible)
        else:
            inventario_item = self.repo.create(
                codigo=codigo_producto,
                descripcion=descripcion,
                cantidad_disponible=cantidad_recibida,
                ubicacion=ubicacion
            )
        return inventario_item

    def revertir_salida_compra(self, codigo_producto: str, cantidad_a_revertir: int) -> bool:
        """Reduce el stock cuando una Orden de Compra es eliminada/cancelada."""
        if cantidad_a_revertir <= 0:
            return True

        inventario_item = self.repo.get_by_codigo(codigo_producto)
        
        if inventario_item:
            inventario_item.cantidad_disponible -= cantidad_a_revertir
            
            # Asegurar que el stock no sea negativo
            if inventario_item.cantidad_disponible < 0:
                print(f"Advertencia: El stock de {codigo_producto} iba a ser negativo. Ajustado a 0.")
                inventario_item.cantidad_disponible = 0
                
            self.repo.update_cantidad(inventario_item.id, inventario_item.cantidad_disponible)
            return True
        return False