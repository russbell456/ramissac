from sqlalchemy.orm import Session

from app.models.almacen_articulos import (
    AlmacenArticulo,
)

from app.models.almacen_devolucion import (
    AlmacenDevolucion,
    AlmacenDevolucionDetalle,
)

from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
)


class AlmacenDevolucionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ==================================================
    # OBTENER PRÉSTAMO CON BLOQUEO
    # ==================================================

    def obtener_prestamo(
        self,
        prestamo_id: int,
    ) -> AlmacenPrestamo | None:

        return (
            self.db.query(AlmacenPrestamo)
            .filter(
                AlmacenPrestamo.id
                == prestamo_id
            )
            .with_for_update()
            .first()
        )

    # ==================================================
    # OBTENER DETALLE DE PRÉSTAMO CON BLOQUEO
    # ==================================================

    def obtener_detalle_prestamo(
        self,
        detalle_id: int,
    ) -> AlmacenPrestamoDetalle | None:

        return (
            self.db.query(
                AlmacenPrestamoDetalle
            )
            .filter(
                AlmacenPrestamoDetalle.id
                == detalle_id
            )
            .with_for_update()
            .first()
        )

    # ==================================================
    # OBTENER ARTÍCULO CON BLOQUEO
    # ==================================================

    def obtener_articulo(
        self,
        articulo_id: int,
    ) -> AlmacenArticulo | None:

        return (
            self.db.query(
                AlmacenArticulo
            )
            .filter(
                AlmacenArticulo.id
                == articulo_id
            )
            .with_for_update()
            .first()
        )

    # ==================================================
    # CREAR DEVOLUCIÓN
    # ==================================================

    def crear_devolucion(
        self,
        devolucion: AlmacenDevolucion,
        detalles: list[
            AlmacenDevolucionDetalle
        ],
    ) -> AlmacenDevolucion:

        self.db.add(devolucion)

        self.db.flush()

        for detalle in detalles:

            detalle.devolucion_id = (
                devolucion.id
            )

            self.db.add(detalle)

        self.db.flush()

        return devolucion

    # ==================================================
    # ACTUALIZAR STOCK
    # ==================================================

    def devolver_stock(
        self,
        articulo: AlmacenArticulo,
        cantidad: int,
    ) -> None:

        if cantidad <= 0:

            raise ValueError(
                "La cantidad devuelta "
                "debe ser mayor que cero"
            )

        articulo.stock_actual += cantidad

        if articulo.en_prestamo < cantidad:

            raise ValueError(
                f"El artículo "
                f"{articulo.nombre} "
                "tiene inconsistencia en "
                "la cantidad prestada"
            )

        articulo.en_prestamo -= cantidad

        self.db.flush()

    # ==================================================
    # ACTUALIZAR DETALLE DEL PRÉSTAMO
    # ==================================================

    def actualizar_detalle(
        self,
        detalle: AlmacenPrestamoDetalle,
        cantidad: int,
    ) -> None:

        pendiente = (
            detalle.cantidad_prestada
            - detalle.cantidad_devuelta
        )

        if cantidad > pendiente:

            raise ValueError(
                "La cantidad devuelta "
                "excede la cantidad pendiente"
            )

        detalle.cantidad_devuelta += cantidad

        detalle.esta_devuelto = (
            detalle.cantidad_devuelta
            >= detalle.cantidad_prestada
        )

        self.db.flush()