<<<<<<< HEAD
from typing import Annotated

=======
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
from app.dependencies.auth_dependencies import get_current_user
from app.services.almacen_articulo_service import AlmacenArticuloService
from app.schemas.almacen_articulo_schema import ArticuloSchema

<<<<<<< HEAD
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
=======
# Definimos el router con tags claros para organizar el Swagger UI
router = APIRouter(prefix="/articulo", tags=["Gestión de Inventario"])

@router.post("/importar-excel", status_code=status.HTTP_201_CREATED, summary="Importación masiva de artículos")
async def importar_excel(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Permite la carga masiva de activos mediante un archivo Excel (.xlsx).
    
    - **Restricción de Seguridad**: Solo usuarios con rol **almacenero** o **admin**.
    - **Proceso**: El sistema valida las columnas, crea nuevos registros o actualiza el stock existente.
    - **Respuesta**: Retorna la cantidad total de artículos procesados con éxito.
    """
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso denegado: Se requieren privilegios de Almacenero o Administrador."
        )
    service = AlmacenArticuloService(db)
    cantidad = await service.procesar_inventario_excel(file)
    return {"message": f"Operación exitosa: Se cargaron {cantidad} artículos correctamente."}

@router.get("/articulos", response_model=list[ArticuloSchema], summary="Obtener catálogo disponible")
def obtener_catalogo(db: Session = Depends(get_db)):
    """
    Retorna la lista completa de artículos que cuentan con stock disponible para préstamo.
    Utiliza el repositorio de Almacén para filtrar los activos operativos.
    """
    return AlmacenArticuloRepository(db).get_all_disponibles()

@router.get("/buscar", response_model=list[ArticuloSchema], summary="Búsqueda avanzada de artículos")
def buscar_articulos(
    q: str = "", 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Filtro dinámico de artículos por coincidencia de nombre o categoría.
    - **Parámetro 'q'**: Palabra clave para la búsqueda (ej. 'amoladora', 'eléctrica').
    - **Seguridad**: Requiere sesión activa.
    """
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    service = AlmacenArticuloService(db)
    return service.buscar_articulos(q)