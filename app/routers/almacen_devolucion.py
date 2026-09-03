from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.database.connection import (
    get_db,
)

from app.dependencies.auth_dependencies import (
    get_current_user,
)

from app.schemas.almacen_devolucion import (
    DevolucionQRData,
    DevolucionResponse,
)

from app.services.almacen_devolucion_service import (
    AlmacenDevolucionService,
)


router = APIRouter(
    prefix="/almacen",
    tags=["Almacén Devolución"],
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
    "/registrar-devolucion-qr",
    response_model=DevolucionResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_devolucion_qr(
    data: DevolucionQRData,
    db: DbDep,
    user: UserDep,
):

    # ==========================================
    # AUTORIZACIÓN
    # ==========================================

    if user.role not in [
        "almacenero",
        "admin",
    ]:

        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Solo almacenero o admin "
                "puede registrar devoluciones"
            ),
        )

    service = (
        AlmacenDevolucionService(
            db
        )
    )

    try:

        devolucion = (
            service.registrar_devolucion_desde_qr(
                data,
                user.id,
            )
        )

        return DevolucionResponse(

            id=devolucion.id,

            codigo_unico=(
                devolucion.codigo_unico
            ),

            estado=(
                devolucion.estado.value
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc