import pandas as pd

from sqlalchemy.orm import Session

from app.models.almacen_articulos import (
    TipoArticulo
)
from app.services.auditoria_service import (
    AuditoriaService
)

from app.repositories.almacen_articulo_repository import (
    AlmacenArticuloRepository
)


class AlmacenArticuloService:

    def __init__(
        self,
        db: Session
    ):
        self.db = db
        self.repo = AlmacenArticuloRepository(db)

    def desactivar_articulo(
        self,
        articulo_id: int,
        usuario_id: int
    ):

        articulo = (
            self.repo.get_articulo_by_id(
                articulo_id
            )
        )

        if not articulo:
            raise ValueError(
                "Artículo no encontrado"
            )

        if not articulo.activo:
            raise ValueError(
                "El artículo ya está inactivo"
            )

        articulo = (
            self.repo.desactivar_articulo(
                articulo_id
            )
        )

        AuditoriaService(
            self.db
        ).registrar(
            usuario_id=usuario_id,
            accion="DESACTIVAR",
            entidad="ARTICULO",
            entidad_id=articulo.id,
            descripcion=(
                f"Artículo "
                f"{articulo.nombre} "
                f"desactivado"
            )
        )

        return articulo
    async def procesar_inventario_excel(
        self,
        file
    ):

        df = pd.read_excel(
            file.file,
            skiprows=3
        )

        df.columns = (
            df.columns.str.strip()
        )

        for _, row in df.iterrows():

            if (
                pd.isna(row["Producto"])
                or
                pd.isna(row["Codigo"])
            ):
                continue

            nombre_prod = str(
                row["Producto"]
            ).upper()

            herramientas = [
                "ROTOMARTILLO",
                "TALADRO",
                "AMOLADORA",
                "ESMERIL",
                "MOTOSIERRA",
                "ARNES",
                "BOMBA",
                "SOLDAR",
                "MAQUINA",
                "EQUIPO",
                "MARTILLO",
                "CINCEL",
                "APLICADOR",
                "LLAVE"
            ]

            es_equipo = any(
                h in nombre_prod
                for h in herramientas
            )

            self.repo.upsert_articulo({
                "nombre": row["Producto"],
                "unidad_medida": row["Unidad Medida"],
                "tipo": (
                    TipoArticulo.EQUIPO
                    if es_equipo
                    else TipoArticulo.CONSUMIBLE
                ),
                "stock_actual": 5,
                "codigo_excel": str(
                    row["Codigo"]
                )
            })

        return len(df)

    def buscar_articulos(
        self,
        termino: str
    ):

        if len(termino) < 2:
            return (
                self.repo.get_all_disponibles()
            )

        return (
            self.repo.search_articulos(
                termino
            )
        )
    def activar_articulo(
        self,
        articulo_id: int,
        usuario_id: int
    ):

        articulo = (
            self.repo.get_articulo_by_id(
                articulo_id
            )
        )

        if not articulo:
            raise ValueError(
                "Artículo no encontrado"
            )

        if articulo.activo:
            raise ValueError(
                "El artículo ya está activo"
            )

        articulo = (
            self.repo.activar_articulo(
                articulo_id
            )
        )

        AuditoriaService(
            self.db
        ).registrar(
            usuario_id=usuario_id,
            accion="ACTIVAR",
            entidad="ARTICULO",
            entidad_id=articulo.id,
            descripcion=(
                f"Artículo "
                f"{articulo.nombre} "
                f"activado"
            )
        )

        return articulo