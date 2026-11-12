import os

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.dependencies.auth_dependencies import (
    get_current_user,
)

from app.schemas.almacen_prestamo import (
    ArticuloPrestamoSchema,
    PrestamoQRData,
    PrestamoResponse,
    PrestamoSchema,
)

from app.models.almacen_articulos import AlmacenArticulo
from app.models.almacen_prestamo import AlmacenPrestamo, EstadoPrestamo
from app.services.almacen_prestamo_service import (
    AlmacenPrestamoService,
)


router = APIRouter(
    prefix="/almacen",
    tags=["Almacén"],
)

prestamos_compat_router = APIRouter(
    prefix="/prestamos",
    tags=["Préstamos Compat"],
)


DbDep = Annotated[
    Session,
    Depends(get_db),
]


UserDep = Annotated[
    dict,
    Depends(get_current_user),
]


@router.post(
    "/registrar-prestamo-qr",
    response_model=PrestamoResponse,
    status_code=status.HTTP_200_OK,
)
def registrar_prestamo_qr(
    data: PrestamoQRData,
    db: DbDep,
    user: UserDep,
):

    if user.role not in [
        "almacenero",
        "admin",
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Solo almacenero o admin "
                "puede registrar préstamos"
            ),
        )

    service = AlmacenPrestamoService(
        db
    )

    try:

        prestamo = (
            service.registrar_prestamo_desde_qr(
                data,
                user.id,
            )
        )

        return PrestamoResponse(
            id=prestamo.id,
            codigo_unico=(
                prestamo.codigo_unico
            ),
            estado=(
                prestamo.estado.value
                if hasattr(prestamo.estado, "value")
                else str(prestamo.estado)
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/prestamo/{prestamo_id}/pdf",
)
def descargar_pdf(
    prestamo_id: int,
):

    pdf_path = (
        f"static/prestamos/"
        f"prestamo_{prestamo_id}.pdf"
    )

    if not os.path.exists(pdf_path):

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF no encontrado",
        )

    return FileResponse(
        pdf_path,
        filename=(
            f"prestamo_{prestamo_id}.pdf"
        ),
    )


@router.get(
    "/trabajador/{trabajador_id}/prestamos",
    response_model=list[PrestamoSchema],
)
def obtener_prestamos_trabajador(
    trabajador_id: int,
    db: DbDep,
    user: UserDep,
):

    if (
        user.role
        not in [
            "almacenero",
            "admin",
        ]
        and user.id != trabajador_id
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No autorizado para "
                "ver préstamos ajenos"
            ),
        )

    service = AlmacenPrestamoService(
        db
    )

    return (
        service.obtener_prestamos_trabajador(
            trabajador_id
        )
    )


@router.get(
    "/articulo/{articulo_id}/prestamos",
    response_model=list[
        ArticuloPrestamoSchema
    ],
)
def obtener_prestamos_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep,
):

    if user.role not in [
        "almacenero",
        "admin",
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )

    service = AlmacenPrestamoService(
        db
    )

    return (
        service.obtener_prestamos_articulo(
            articulo_id
        )
    )


@prestamos_compat_router.patch("/{prestamo_id}/devolver")
@router.patch("/prestamos/{prestamo_id}/devolver")
def devolver_prestamo_directo(
    prestamo_id: int,
    db: DbDep,
    user: UserDep,
):
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para devolver préstamos",
        )

    prestamo = db.query(AlmacenPrestamo).filter(AlmacenPrestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    for detalle in prestamo.detalles:
        if not detalle.esta_devuelto and detalle.cantidad_pendiente > 0:
            articulo = db.query(AlmacenArticulo).filter(AlmacenArticulo.id == detalle.articulo_id).first()
            if articulo:
                articulo.stock_actual += detalle.cantidad_pendiente
                if articulo.en_prestamo is not None:
                    articulo.en_prestamo = max(0, articulo.en_prestamo - detalle.cantidad_pendiente)
            detalle.cantidad_devuelta = detalle.cantidad_prestada
            detalle.cantidad_pendiente = 0
            detalle.esta_devuelto = True

    prestamo.estado = EstadoPrestamo.CERRADO
    db.commit()

    return {
        "message": "Préstamo devuelto correctamente",
        "prestamo_id": prestamo_id,
        "estado": prestamo.estado.value if hasattr(prestamo.estado, "value") else str(prestamo.estado),
    }