import os
<<<<<<< HEAD
from typing import Annotated  # Importar Annotated

=======
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
<<<<<<< HEAD
from app.schemas.almacen_prestamo import (
    ArticuloPrestamoSchema, 
    PrestamoQRData, 
    PrestamoResponse, 
    PrestamoSchema
)
from app.services.almacen_prestamo_service import AlmacenPrestamoService
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/almacen", tags=["Almacén"])

# Definir tipos de dependencia para S8410
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[dict, Depends(get_current_user)]

@router.post(
    "/registrar-prestamo-qr", 
    response_model=PrestamoResponse,
    responses={400: {"description": "Error de validación"}, 403: {"description": "No autorizado"}}
)
def registrar_prestamo_qr(
    data: PrestamoQRData,
    db: DbDep,
    user: UserDep
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="Solo almacenero o admin puede registrar préstamos")
=======
from app.schemas.almacen_prestamo import ArticuloPrestamoSchema, PrestamoQRData, PrestamoResponse, PrestamoSchema
from app.services.almacen_prestamo_service import AlmacenPrestamoService
from app.dependencies.auth_dependencies import get_current_user

# Usamos una etiqueta descriptiva para el proceso de negocio
router = APIRouter(prefix="/almacen", tags=["Operaciones: Préstamos"])

@router.post(
    "/registrar-prestamo-qr", 
    response_model=PrestamoResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Registrar salida de activos vía QR"
)
def registrar_prestamo_qr(
    data: PrestamoQRData,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Inicia y formaliza la salida de herramientas del almacén central de **Ramis SAC**.
    
    - **Validación Bi-direccional**: Verifica la identidad del trabajador y el stock del activo mediante el código QR.
    - **Control de Inventario**: Al procesar, el sistema descuenta automáticamente las unidades solicitadas del stock operativo.
    - **Seguridad**: Solo accesible por el personal de almacén o administradores para evitar registros fraudulentos.
    """
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado: Solo el personal de almacén puede autorizar salidas físicas."
        )
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a

    service = AlmacenPrestamoService(db)
    try:
        prestamo = service.registrar_prestamo_desde_qr(data, user.id)
        return PrestamoResponse(
            id=prestamo.id,
            codigo_unico=prestamo.codigo_unico,
            estado=prestamo.estado
        )
    except ValueError as e:
<<<<<<< HEAD
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/prestamo/{prestamo_id}/pdf",
    responses={404: {"description": "PDF no encontrado"}}
)
def descargar_pdf(prestamo_id: int):
    pdf_path = f"static/prestamos/prestamo_{prestamo_id}.pdf"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF no encontrado")
=======
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get(
    "/prestamo/{prestamo_id}/pdf", 
    summary="Generar/Descargar comprobante PDF",
    response_description="El archivo binario del comprobante PDF"
)
def descargar_pdf(prestamo_id: int):
    """
    Recupera el comprobante digital de préstamo generado por el sistema.
    
    - **Documentación Legal**: Este PDF incluye la relación de herramientas, fecha y firma digital capturada.
    - **Almacenamiento**: Los archivos se sirven desde el directorio estático seguro del servidor.
    """
    pdf_path = f"static/prestamos/prestamo_{prestamo_id}.pdf"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="El comprobante PDF solicitado no existe o aún no ha sido generado."
        )
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
    
    return FileResponse(pdf_path, filename=f"prestamo_{prestamo_id}.pdf")

@router.get(
    "/trabajador/{trabajador_id}/prestamos", 
<<<<<<< HEAD
    response_model=list[PrestamoSchema],
    responses={403: {"description": "No autorizado"}}
)
def obtener_prestamos_trabajador(
    trabajador_id: int,
    db: DbDep,
    user: UserDep
):
    if user.role not in ["almacenero", "admin"] and user.id != trabajador_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver préstamos ajenos")

    service = AlmacenPrestamoService(db)
    return service.obtener_prestamos_trabajador(trabajador_id)

@router.get(
    "/articulo/{articulo_id}/prestamos", 
    response_model=list[ArticuloPrestamoSchema],
    responses={403: {"description": "No autorizado"}}
)
def obtener_prestamos_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="No autorizado")

    service = AlmacenPrestamoService(db)
    return service.obtener_prestamos_articulo(articulo_id)
=======
    response_model=list[PrestamoSchema], 
    summary="Consultar historial por trabajador"
)
def obtener_prestamos_trabajador(
    trabajador_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Muestra todos los préstamos asociados a un trabajador específico.
    
    - **Privacidad**: Un trabajador solo puede ver su propio historial. Almaceneros y Admins pueden ver el de cualquier empleado.
    - **Utilidad**: Ideal para auditorías rápidas de activos pendientes de devolución.
    """
    if user.role not in ["almacenero", "admin"] and user.id != trabajador_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso restringido: No puede consultar historiales de terceros."
        )

    service = AlmacenPrestamoService(db)
    prestamos = service.obtener_prestamos_trabajador(trabajador_id)
    return prestamos

@router.get(
    "/articulo/{articulo_id}/prestamos", 
    response_model=list[ArticuloPrestamoSchema], 
    summary="Rastrear préstamos de un artículo"
)
def obtener_prestamos_articulo(
    articulo_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Permite auditar la rotación de una herramienta específica.
    
    - **Trazabilidad**: Muestra quién tiene o ha tenido prestado el artículo seleccionado.
    - **Uso**: Exclusivo para gestión de activos (Almaceneros/Admin).
    """
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso denegado: Se requieren permisos de gestión de activos."
        )

    service = AlmacenPrestamoService(db)
    prestamos = service.obtener_prestamos_articulo(articulo_id)
    return prestamos
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
