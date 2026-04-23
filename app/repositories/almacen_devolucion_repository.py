from sqlalchemy.orm import Session
from app.models.almacen_devolucion import AlmacenDevolucion, AlmacenDevolucionDetalle
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle, EstadoPrestamo
from app.models.almacen_articulos import AlmacenArticulo

class AlmacenDevolucionRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear_devolucion(self, devolucion: AlmacenDevolucion, detalles: list[AlmacenDevolucionDetalle]):
        self.db.add(devolucion)
        self.db.flush()
        for detalle in detalles:
            detalle.devolucion_id = devolucion.id
            self.db.add(detalle)
        self.db.commit()
        self.db.refresh(devolucion)
        return devolucion

    def update_stock(self, articulo_id: int, cantidad: int):
        articulo = self.db.query(AlmacenArticulo).filter(AlmacenArticulo.id == articulo_id).first()
        if articulo:
            articulo.stock_actual += cantidad  # Suma para devolución
            self.db.commit()

    def actualizar_prestamo_detalle(self, prestamo_detalle_id: int, cantidad: int):
        detalle = self.db.query(AlmacenPrestamoDetalle).filter(AlmacenPrestamoDetalle.id == prestamo_detalle_id).first()
        if detalle:
            detalle.cantidad_devuelta += cantidad
            if detalle.cantidad_devuelta >= detalle.cantidad_prestada:
                detalle.esta_devuelto = True
            self.db.commit()
            # Cerrar préstamo si no hay pendientes
            prestamo_id = detalle.prestamo_id
            pendientes = self.db.query(AlmacenPrestamoDetalle).filter(
                AlmacenPrestamoDetalle.prestamo_id == prestamo_id,
                AlmacenPrestamoDetalle.esta_devuelto == False
            ).count()
            if pendientes == 0:
                prestamo = self.db.query(AlmacenPrestamo).filter(AlmacenPrestamo.id == prestamo_id).first()
                prestamo.estado = EstadoPrestamo.CERRADO
                self.db.commit()