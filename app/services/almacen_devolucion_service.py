from sqlalchemy.orm import Session
from app.models.almacen_devolucion import AlmacenDevolucion, AlmacenDevolucionDetalle, EstadoDevolucion
from app.models.almacen_prestamo import AlmacenPrestamoDetalle
from app.models.user import User
from app.repositories.almacen_devolucion_repository import AlmacenDevolucionRepository
from app.schemas.almacen_devolucion import DevolucionQRData

class AlmacenDevolucionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AlmacenDevolucionRepository(db)

    def registrar_devolucion_desde_qr(self, data: DevolucionQRData, almacenero_id: int):
        # Validar trabajador
        trabajador = self.db.query(User).filter(User.id == data.trabajador_id, User.role == "trabajador").first()
        if not trabajador:
            raise ValueError("Trabajador no encontrado o rol inválido")

        # Crear devolución real
        devolucion = AlmacenDevolucion(
            trabajador_id=data.trabajador_id,
            almacenero_id=almacenero_id,
            codigo_unico=data.codigo_unico,
            prestamo_id=data.prestamo_id,
            fecha_devolucion=data.fecha_devolucion,
            firma_base64=data.firma_base64,
            estado=EstadoDevolucion.CONFIRMADA,  # ← CORRECCIÓN CLAVE: usa el enum
            registrado_por="almacenero"
        )

        detalles = []
        for item in data.items:
            # Validar cantidad pendiente
            p_det = self.db.query(AlmacenPrestamoDetalle).filter(AlmacenPrestamoDetalle.id == item.prestamo_detalle_id).first()
            if not p_det:
                raise ValueError(f"Detalle no encontrado: {item.prestamo_detalle_id}")
            pendiente = p_det.cantidad_prestada - p_det.cantidad_devuelta
            if item.cantidad > pendiente:
                raise ValueError("Cantidad excede lo pendiente")

            # Sumar stock y actualizar detalle de préstamo
            self.repo.update_stock(p_det.articulo_id, item.cantidad)
            self.repo.actualizar_prestamo_detalle(item.prestamo_detalle_id, item.cantidad)

            detalles.append(AlmacenDevolucionDetalle(
                prestamo_detalle_id=item.prestamo_detalle_id,
                cantidad_devuelta=item.cantidad
            ))

        return self.repo.crear_devolucion(devolucion, detalles)