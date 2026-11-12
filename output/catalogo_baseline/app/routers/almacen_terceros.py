from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.services.almacen_terceros_service import AlmacenTercerosService


router = APIRouter(
    prefix="/almacen/tercero",
    tags=["Terceros"]
)


DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[dict, Depends(get_current_user)]


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_tercero(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    service = AlmacenTercerosService(db)
    tercero = service.crear_tercero(payload)
    return {"id": tercero.id, "nombres": tercero.nombres or tercero.empresa_nombre}


@router.get("/", status_code=status.HTTP_200_OK)
def listar_terceros(db: Session = Depends(get_db)):
    service = AlmacenTercerosService(db)
    return service.listar()


@router.get("/{tercero_id}", status_code=status.HTTP_200_OK)
def obtener_tercero(tercero_id: int, db: Session = Depends(get_db)):
    service = AlmacenTercerosService(db)
    tercero = service.obtener(tercero_id)
    if not tercero:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tercero no encontrado")
    return tercero
