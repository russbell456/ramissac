from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.repositories.almacen_articulo_repository import (
    AlmacenArticuloRepository
)

from app.dependencies.auth_dependencies import (
    get_current_user
)

from app.services.almacen_articulo_service import (
    AlmacenArticuloService
)

from app.schemas.almacen_articulo_schema import (
    ArticuloSchema
)


router = APIRouter(
    prefix="/articulo",
    tags=["Articulo"]
)

DbDep = Annotated[
    Session,
    Depends(get_db)
]

UserDep = Annotated[
    dict,
    Depends(get_current_user)
]


@router.post(
    "/importar-excel",
    status_code=status.HTTP_201_CREATED
)
async def importar_excel(
    file: UploadFile = File(...),
    db: DbDep = None,
    user: UserDep = None
):

    if user.role not in [
        "almacenero",
        "admin"
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )

    service = AlmacenArticuloService(db)

    cantidad = await service.procesar_inventario_excel(
        file
    )

    return {
        "message": (
            f"Se cargaron "
            f"{cantidad} artículos correctamente."
        )
    }


@router.get(
    "/articulos",
    response_model=list[ArticuloSchema]
)
def obtener_catalogo(
    db: DbDep
):

    return (
        AlmacenArticuloRepository(db)
        .get_all_disponibles()
    )


@router.get(
    "/buscar",
    response_model=list[ArticuloSchema]
)
def buscar_articulos(
    q: str = "",
    db: DbDep = None,
    user: UserDep = None
):

    service = AlmacenArticuloService(db)

    return service.buscar_articulos(q)
@router.patch(
    "/{articulo_id}/desactivar",
    status_code=status.HTTP_200_OK
)
def desactivar_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep
):

    if user.role not in [
        "admin",
        "almacenero"
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )

    service = (
        AlmacenArticuloService(
            db
        )
    )

    try:

        articulo = (
            service.desactivar_articulo(
                articulo_id,
                user.id
            )
        )

        return {
            "message":
                "Artículo desactivado correctamente",
            "articulo_id":
                articulo.id
        }

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
@router.patch(
    "/{articulo_id}/activar",
    status_code=status.HTTP_200_OK
)
def activar_articulo(
    articulo_id: int,
    db: DbDep,
    user: UserDep
):

    if user.role not in [
        "admin",
        "almacenero"
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )

    service = AlmacenArticuloService(db)

    try:

        articulo = (
            service.activar_articulo(
                articulo_id,
                user.id
            )
        )

        return {
            "message":
                "Artículo activado correctamente",
            "articulo_id":
                articulo.id
        }

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )