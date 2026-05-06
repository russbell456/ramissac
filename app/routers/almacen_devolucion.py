from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.almacen_devolucion import DevolucionQRData, DevolucionResponse
from app.services.almacen_devolucion_service import AlmacenDevolucionService
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/almacen", tags=["Almacén Devolución"])

@router.post("/registrar-devolucion-qr", response_model=DevolucionResponse)
def registrar_devolucion_qr(
    data: DevolucionQRData,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="Solo almacenero o admin puede registrar devoluciones")

    service = AlmacenDevolucionService(db)
    try:
        devolucion = service.registrar_devolucion_desde_qr(data, user.id)
        return DevolucionResponse(
            id=devolucion.id,
            codigo_unico=devolucion.codigo_unico,
            estado=devolucion.estado.value
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))