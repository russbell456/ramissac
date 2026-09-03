from sqlalchemy.orm import Session

from app.models.almacen_articulos import AlmacenArticulo
from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
)


class AlmacenPrestamoRepository:

    def __init__(self, db: Session):
        self.db = db

    def crear_prestamo(
        self,
        prestamo: AlmacenPrestamo,
        detalles: list[AlmacenPrestamoDetalle],
    ) -> AlmacenPrestamo:

        self.db.add(prestamo)
        self.db.flush()

        for detalle in detalles:
            detalle.prestamo_id = prestamo.id
            self.db.add(detalle)

        self.db.flush()

        return prestamo

    def obtener_articulo(
        self,
        articulo_id: int,
        bloquear: bool = False,
    ) -> AlmacenArticulo | None:

        query = (
            self.db.query(AlmacenArticulo)
            .filter(
                AlmacenArticulo.id == articulo_id
            )
        )

        if bloquear:
            query = query.with_for_update()

        return query.first()

    def descontar_stock(
        self,
        articulo: AlmacenArticulo,
        cantidad: int,
        requiere_devolucion: bool,
    ) -> None:

        if cantidad <= 0:
            raise ValueError(
                "La cantidad debe ser mayor que cero"
            )

        if articulo.stock_actual < cantidad:
            raise ValueError(
                f"Stock insuficiente para "
                f"{articulo.nombre}. "
                f"Disponible: {articulo.stock_actual}, "
                f"solicitado: {cantidad}"
            )

        articulo.stock_actual -= cantidad

        if requiere_devolucion:
            articulo.en_prestamo += cantidad

        self.db.flush()

    def obtener_prestamo(
        self,
        prestamo_id: int,
    ) -> AlmacenPrestamo | None:

        return (
            self.db.query(AlmacenPrestamo)
            .filter(
                AlmacenPrestamo.id == prestamo_id
            )
            .first()
        )