from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.services.inventario_service import InventarioService
from app.database.connection import get_db
from app.schemas.inventario_schema import InventarioEntity

# 🔐 SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

# Mantenemos consistencia con el prefijo y etiquetas descriptivas
router = APIRouter(
    prefix="/inventario",
    tags=["Gestión de Inventario"]
)

@router.get(
    "/", 
    response_model=List[InventarioEntity],
    status_code=status.HTTP_200_OK,
    summary="Consultar stock consolidado"
)
def get_inventario_completo(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Proporciona una vista integral de las existencias físicas en el almacén de **Ramis SAC**.
    
    - **Agrupamiento**: Los ítems se presentan consolidados por su código identificador.
    - **Uso Crítico**: Permite al personal de almacén verificar la disponibilidad antes de autorizar un préstamo o generar una orden de compra.
    - **Trazabilidad**: Cruza los datos de ingresos (Excel/Compras) con las salidas (Préstamos) para mostrar el stock neto real.
    - **Seguridad**: Requiere autenticación de usuario.
    """
    service = InventarioService(db)
    try:
        return service.listar_inventario()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la consulta de inventario: Fallo al recuperar el consolidado de stock. ({str(e)})"
        )