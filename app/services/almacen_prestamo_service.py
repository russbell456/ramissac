from sqlalchemy.orm import Session, joinedload
from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
    EstadoPrestamo
)
from app.models.user import User
from app.models.almacen_articulos import AlmacenArticulo
from app.repositories.almacen_prestamo_repository import AlmacenPrestamoRepository
from app.schemas.almacen_prestamo import (
    ArticuloPrestamoSchema,
    PrestamoDetalleSchema,
    PrestamoQRData,
    PrestamoSchema
)
from app.utils.pdf_prestamo import generar_pdf_prestamo


class AlmacenPrestamoService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = AlmacenPrestamoRepository(db)

    # =========================
    # MÉTODO PRINCIPAL (REFactorizado)
    # =========================
    def registrar_prestamo_desde_qr(self, data: PrestamoQRData, almacenero_id: int):
        trabajador = self._validar_trabajador(data.trabajador_id)
        self._validar_stock(data.items)

        prestamo = self._crear_prestamo(data, almacenero_id)
        detalles = self._crear_detalles(data.items)

        prestamo = self.repo.crear_prestamo(prestamo, detalles)

        prestamo_schema = self._build_prestamo_schema(prestamo, trabajador)

        pdf_path = generar_pdf_prestamo(prestamo_schema)
        prestamo.pdf_url = pdf_path

        return prestamo

    # =========================
    # VALIDACIONES
    # =========================
    def _validar_trabajador(self, trabajador_id: int) -> User:
        trabajador = self.db.query(User).filter(
            User.id == trabajador_id,
            User.role == "trabajador"
        ).first()

        if not trabajador:
            raise ValueError("Trabajador no encontrado o rol inválido")

        return trabajador

    def _validar_stock(self, items):
        for item in items:
            art = self.db.query(AlmacenArticulo).filter(
                AlmacenArticulo.id == item.articulo_id
            ).first()

            if not art:
                raise ValueError(f"Artículo no encontrado: {item.articulo_id}")

            if art.stock_actual < item.cantidad:
                raise ValueError(f"Sin stock suficiente para {art.nombre}")

    # =========================
    # CREACIÓN DE ENTIDADES
    # =========================
    def _crear_prestamo(self, data: PrestamoQRData, almacenero_id: int) -> AlmacenPrestamo:
        return AlmacenPrestamo(
            trabajador_id=data.trabajador_id,
            almacenero_id=almacenero_id,
            codigo_unico=data.codigo_unico,
            fecha_prestamo=data.fecha_prestamo,
            fecha_devolucion_prevista=data.fecha_devolucion_prevista,
            firma_base64=data.firma_base64,
            estado=EstadoPrestamo.ABIERTO,
            registrado_por="almacenero"
        )

    def _crear_detalles(self, items):
        detalles = []
        for item in items:
            self.repo.update_stock(item.articulo_id, item.cantidad)
            detalles.append(
                AlmacenPrestamoDetalle(
                    articulo_id=item.articulo_id,
                    cantidad_prestada=item.cantidad
                )
            )
        return detalles

    # =========================
    # TRANSFORMACIÓN A SCHEMA
    # =========================
    def _build_detalle_schema(self, det: AlmacenPrestamoDetalle) -> PrestamoDetalleSchema:
        articulo = self.db.query(AlmacenArticulo).get(det.articulo_id)

        return PrestamoDetalleSchema(
            id=det.id,
            articulo_id=det.articulo_id,
            cantidad_prestada=det.cantidad_prestada,
            cantidad_devuelta=det.cantidad_devuelta,
            esta_devuelto=det.esta_devuelto,
            articulo_nombre=articulo.nombre if articulo else "Desconocido",
            articulo_tipo=articulo.tipo.value if articulo else "unknown",
            articulo_unidad=articulo.unidad_medida if articulo else ""
        )

    def _build_prestamo_schema(self, prestamo: AlmacenPrestamo, trabajador: User) -> PrestamoSchema:
        detalles_schema = [
            self._build_detalle_schema(det)
            for det in prestamo.detalles
        ]

        return PrestamoSchema(
            id=prestamo.id,
            trabajador_id=trabajador.id,
            nombres_completos=f"{trabajador.nombre} {trabajador.apellidos}",
            dni=trabajador.dni,
            cargo=trabajador.cargo,
            codigo_unico=prestamo.codigo_unico,
            fecha_prestamo=prestamo.fecha_prestamo,
            fecha_devolucion_prevista=prestamo.fecha_devolucion_prevista,
            firma_base64=prestamo.firma_base64,
            estado=prestamo.estado.value,
            registrado_por=prestamo.registrado_por,
            fecha_registro=prestamo.fecha_registro,
            detalles=detalles_schema
        )

    # =========================
    # OBTENER PRÉSTAMOS POR TRABAJADOR
    # =========================
    def obtener_prestamos_trabajador(self, trabajador_id: int):
        prestamos = self.db.query(AlmacenPrestamo).options(
            joinedload(AlmacenPrestamo.detalles).joinedload(AlmacenPrestamoDetalle.articulo),
            joinedload(AlmacenPrestamo.trabajador)
        ).filter(
            AlmacenPrestamo.trabajador_id == trabajador_id
        ).all()

        return [
            self._map_prestamo_to_schema(p)
            for p in prestamos
        ]

    def _map_prestamo_to_schema(self, p: AlmacenPrestamo) -> PrestamoSchema:
        trabajador = p.trabajador

        detalles = [
            PrestamoDetalleSchema(
                id=det.id,
                articulo_id=det.articulo_id,
                cantidad_prestada=det.cantidad_prestada,
                cantidad_devuelta=det.cantidad_devuelta,
                esta_devuelto=det.esta_devuelto,
                articulo_nombre=det.articulo.nombre if det.articulo else "Desconocido",
                articulo_tipo=det.articulo.tipo.value if det.articulo else "unknown",
                articulo_unidad=det.articulo.unidad_medida if det.articulo else ""
            )
            for det in p.detalles
        ]

        return PrestamoSchema(
            id=p.id,
            trabajador_id=p.trabajador_id,
            nombres_completos=f"{trabajador.nombre} {trabajador.apellidos}" if trabajador else "Desconocido",
            dni=trabajador.dni if trabajador else "",
            cargo=trabajador.cargo if trabajador else "",
            codigo_unico=p.codigo_unico,
            fecha_prestamo=p.fecha_prestamo,
            fecha_devolucion_prevista=p.fecha_devolucion_prevista,
            firma_base64=p.firma_base64,
            estado=p.estado.value,
            registrado_por=p.registrado_por,
            fecha_registro=p.fecha_registro,
            detalles=detalles
        )

    # =========================
    # PRÉSTAMOS PENDIENTES POR ARTÍCULO
    # =========================
    def obtener_prestamos_articulo(self, articulo_id: int):
        detalles = self.db.query(AlmacenPrestamoDetalle).options(
            joinedload(AlmacenPrestamoDetalle.prestamo).joinedload(AlmacenPrestamo.trabajador)
        ).filter(
            AlmacenPrestamoDetalle.articulo_id == articulo_id,
            AlmacenPrestamoDetalle.esta_devuelto == False,
            AlmacenPrestamoDetalle.cantidad_devuelta < AlmacenPrestamoDetalle.cantidad_prestada
        ).all()

        return [
            self._map_articulo_prestamo(det)
            for det in detalles
        ]

    def _map_articulo_prestamo(self, det: AlmacenPrestamoDetalle) -> ArticuloPrestamoSchema:
        p = det.prestamo
        t = p.trabajador

        return ArticuloPrestamoSchema(
            trabajador_id=t.id,
            nombres_completos=f"{t.nombre} {t.apellidos}" if t else "Desconocido",
            dni=t.dni if t else "",
            cargo=t.cargo if t else "",
            fecha_prestamo=p.fecha_prestamo,
            cantidad_pendiente=det.cantidad_prestada - det.cantidad_devuelta
        )