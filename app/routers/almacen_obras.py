from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.services.almacen_obras_service import AlmacenObrasService


router = APIRouter(
    prefix="/almacen/obra",
    tags=["Obras"]
)


DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[dict, Depends(get_current_user)]


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_obra(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    service = AlmacenObrasService(db)
    obra = service.crear_obra(
        nombre=payload.get("nombre"),
        descripcion=payload.get("descripcion"),
        cliente=payload.get("cliente"),
        ubicacion=payload.get("ubicacion")
    )

    return {"id": obra.id, "nombre": obra.nombre}


@router.get("/", status_code=status.HTTP_200_OK)
def listar_obras(db: Session = Depends(get_db)):
    service = AlmacenObrasService(db)
    return service.listar_obras()


@router.get("/{obra_id}", status_code=status.HTTP_200_OK)
def obtener_obra(obra_id: int, db: Session = Depends(get_db)):
    service = AlmacenObrasService(db)
    obra = service.obtener_obra(obra_id)
    if not obra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")
    return obra
