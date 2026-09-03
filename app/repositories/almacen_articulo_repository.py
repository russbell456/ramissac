from datetime import datetime

from sqlalchemy.orm import Session

from app.models.almacen_articulos import (
    AlmacenArticulo,
)
from app.models.almacen_articulo_imagen import (
    AlmacenArticuloImagen,
)


class AlmacenArticuloRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.activo.is_(True)
            )
            .order_by(
                AlmacenArticulo.id.desc()
            )
            .all()
        )

    def get_all_disponibles(self):
        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.stock_actual > 0,
                AlmacenArticulo.activo.is_(True),
            )
            .order_by(
                AlmacenArticulo.nombre.asc()
            )
            .all()
        )

    def get_by_id(
        self,
        articulo_id: int,
    ):
        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.id == articulo_id
            )
            .first()
        )

    def get_by_codigo(
        self,
        codigo: str,
    ):
        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.codigo_excel == codigo
            )
            .first()
        )

    def get_by_serie(
        self,
        serie: str,
    ):
        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.serie == serie
            )
            .first()
        )

    def create(
        self,
        data: dict,
    ):
        articulo = AlmacenArticulo(
            **data
        )

        self.db.add(articulo)
        self.db.commit()
        self.db.refresh(articulo)

        return articulo

    def update(
        self,
        articulo: AlmacenArticulo,
        data: dict,
    ):
        for key, value in data.items():
            setattr(
                articulo,
                key,
                value,
            )

        self.db.commit()
        self.db.refresh(articulo)

        return articulo

    def deactivate(
        self,
        articulo: AlmacenArticulo,
    ):
        articulo.activo = False
        articulo.fecha_baja = datetime.utcnow()

        self.db.commit()
        self.db.refresh(articulo)

        return articulo

    def activate(
        self,
        articulo: AlmacenArticulo,
    ):
        articulo.activo = True
        articulo.fecha_baja = None

        self.db.commit()
        self.db.refresh(articulo)

        return articulo

    def search(
        self,
        query: str,
    ):
        search = f"%{query}%"

        return (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.activo.is_(True)
            )
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
                |
                (
                    AlmacenArticulo.serie.ilike(
                        search
                    )
                )
                |
                (
                    AlmacenArticulo.marca.ilike(
                        search
                    )
                )
                |
                (
                    AlmacenArticulo.modelo.ilike(
                        search
                    )
                )
            )
            .order_by(
                AlmacenArticulo.nombre.asc()
            )
            .all()
        )

    def add_image(
        self,
        articulo_id: int,
        data: dict,
    ):
        imagen = AlmacenArticuloImagen(
            articulo_id=articulo_id,
            **data,
        )

        self.db.add(imagen)
        self.db.commit()
        self.db.refresh(imagen)

        return imagen

    def get_image(
        self,
        imagen_id: int,
    ):
        return (
            self.db.query(AlmacenArticuloImagen)
            .filter(
                AlmacenArticuloImagen.id == imagen_id
            )
            .first()
        )

    def delete_image(
        self,
        imagen: AlmacenArticuloImagen,
    ):
        self.db.delete(imagen)
        self.db.commit()