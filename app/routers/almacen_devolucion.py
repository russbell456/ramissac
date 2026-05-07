from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.almacen_devolucion import DevolucionQRData, DevolucionResponse
from app.services.almacen_devolucion_service import AlmacenDevolucionService
from app.dependencies.auth_dependencies import get_current_user

# Agrupamos bajo una etiqueta de operación clara
router = APIRouter(prefix="/almacen", tags=["Operaciones: Devoluciones"])

@router.post(
    "/registrar-devolucion-qr", 
    response_model=DevolucionResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Registrar retorno de activos vía QR"
)
def registrar_devolucion_qr(
    data: DevolucionQRData,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Finaliza el ciclo de vida del préstamo procesando el retorno físico de las herramientas.
    
    - **Validación de Identidad**: El sistema decodifica el código QR presentado por el trabajador para asegurar la trazabilidad.
    - **Actualización de Stock**: Al confirmar la devolución, el sistema reintegra automáticamente las cantidades al inventario disponible.
    - **Restricción de Seguridad**: Operación exclusiva para usuarios con rol **almacenero** o **admin**.
    - **Manejo de Errores**: Retorna un error 400 si el QR es inválido o si el préstamo ya fue cerrado previamente.
    """
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operación no permitida: Se requieren privilegios de Almacenero o Administrador para cerrar préstamos."
        )

    service = AlmacenDevolucionService(db)
    try:
        devolucion = service.registrar_devolucion_desde_qr(data, user.id)
        return DevolucionResponse(
            id=devolucion.id,
            codigo_unico=devolucion.codigo_unico,
            estado=devolucion.estado.value
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )