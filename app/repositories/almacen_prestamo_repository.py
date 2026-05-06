from sqlalchemy.orm import Session
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle
from app.models.almacen_articulos import AlmacenArticulo

class AlmacenPrestamoRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear_prestamo(self, prestamo: AlmacenPrestamo, detalles: list[AlmacenPrestamoDetalle]):
        self.db.add(prestamo)
        self.db.flush()  # Obtiene ID del prestamo
        for detalle in detalles:
            detalle.prestamo_id = prestamo.id
            self.db.add(detalle)
        self.db.commit()
        self.db.refresh(prestamo)
        return prestamo

    def update_stock(self, articulo_id: int, cantidad: int):
        articulo = self.db.query(AlmacenArticulo).filter(AlmacenArticulo.id == articulo_id).first()
        if articulo:
            if articulo.stock_actual < cantidad:
                raise ValueError(f"Stock insuficiente para artículo {articulo.nombre}")
            articulo.stock_actual -= cantidad
            self.db.commit()