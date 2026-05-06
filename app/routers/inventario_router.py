from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.services.inventario_service import InventarioService
from app.database.connection import get_db
from app.schemas.inventario_schema import InventarioEntity

# 🔐 SEGURIDAD
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(
    prefix="/inventario",
    tags=["Inventario"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)


@router.get("/", response_model=List[InventarioEntity])
def get_inventario_completo(
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista completa de todos los ítems en stock, agrupados por código.
    """
    service = InventarioService(db)
    try:
        return service.listar_inventario()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar inventario: {str(e)}"
        )
