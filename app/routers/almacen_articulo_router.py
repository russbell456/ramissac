from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
from app.dependencies.auth_dependencies import get_current_user
from app.services.almacen_articulo_service import AlmacenArticuloService
from app.schemas.almacen_articulo_schema import ArticuloSchema

router = APIRouter(prefix="/articulo", tags=["Articulo"])

# Definición de tipos para S8410
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[dict, Depends(get_current_user)]

@router.post(
    "/importar-excel",
    responses={
        403: {"description": "No autorizado"},
        400: {"description": "Error en el procesamiento del archivo"}
    }
)
async def importar_excel(
    file: UploadFile = File(...), 
    db: DbDep = None, # db se maneja a través de la inyección
    user: UserDep = None
):
    # Nota: Asegúrate de que tu inyección de dependencias soporte este estilo
    # Si 'db' y 'user' dan problemas al ser llamados, mantenlos como:
    # db: Session = Depends(get_db), user: dict = Depends(get_current_user)
    
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    service = AlmacenArticuloService(db)
    cantidad = await service.procesar_inventario_excel(file)
    return {"message": f"Se cargaron {cantidad} artículos correctamente."}

@router.get("/articulos", response_model=list[ArticuloSchema])
def obtener_catalogo(db: DbDep):
    return AlmacenArticuloRepository(db).get_all_disponibles()

@router.get(
    "/buscar", 
    response_model=list[ArticuloSchema],
    responses={401: {"description": "No autenticado"}}
)
def buscar_articulos(
    q: str = "", 
    db: DbDep = None,
    user: UserDep = None
):
    service = AlmacenArticuloService(db)
    return service.buscar_articulos(q)