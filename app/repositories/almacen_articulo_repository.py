from datetime import datetime

from sqlalchemy.orm import Session

from app.models.almacen_articulos import (
    AlmacenArticulo
)


class AlmacenArticuloRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_all_disponibles(self):

        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.stock_actual > 0,
                AlmacenArticulo.activo.is_(True)
            )
            .all()
        )

    def get_articulo_by_id(
        self,
        articulo_id: int
    ):

        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.id == articulo_id
            )
            .first()
        )

    def upsert_articulo(
        self,
        data: dict
    ):

        articulo = (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.codigo_excel ==
                data["codigo_excel"]
            )
            .first()
        )

        if articulo:

            for key, value in data.items():
                setattr(
                    articulo,
                    key,
                    value
                )

        else:

            articulo = AlmacenArticulo(
                **data
            )

            self.db.add(
                articulo
            )

        self.db.commit()

    def search_articulos(
        self,
        query: str
    ):

        search = f"%{query}%"

        return (
            self.db.query(AlmacenArticulo)
            .filter(
                (
                    AlmacenArticulo.nombre.ilike(
                        search
                    )
                )
                |
                (
                    AlmacenArticulo.codigo_excel.ilike(
                        search
                    )
                )
            )
            .filter(
                AlmacenArticulo.stock_actual > 0,
                AlmacenArticulo.activo.is_(True)
            )
            .all()
        )

    def desactivar_articulo(
        self,
        articulo_id: int
    ):

        articulo = (
            self.db.query(
                AlmacenArticulo
            )
            .filter(
                AlmacenArticulo.id ==
                articulo_id,
                AlmacenArticulo.activo.is_(True)
            )
            .first()
        )

        if not articulo:
            return None

        articulo.activo = False
        articulo.fecha_baja = datetime.utcnow()

        self.db.commit()
        self.db.refresh(articulo)

        return articulo
    
    def activar_articulo(
        self,
        articulo_id: int
    ):

        articulo = (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.id == articulo_id,
                AlmacenArticulo.activo.is_(False)
            )
            .first()
        )

        if not articulo:
            return None

        articulo.activo = True
        articulo.fecha_baja = None

        self.db.commit()
        self.db.refresh(articulo)

        return articulo