from sqlalchemy.orm import Session, joinedload
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle, EstadoPrestamo
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

    def registrar_prestamo_desde_qr(self, data: PrestamoQRData, almacenero_id: int):
        # Validar que el trabajador_id exista y sea trabajador
        trabajador = self.db.query(User).filter(User.id == data.trabajador_id, User.role == "trabajador").first()
        if not trabajador:
            raise ValueError("Trabajador no encontrado o rol inválido")

        # Validar stock
        for item in data.items:
            art = self.db.query(AlmacenArticulo).filter(AlmacenArticulo.id == item.articulo_id).first()
            if not art:
                raise ValueError(f"Artículo no encontrado: {item.articulo_id}")
            if art.stock_actual < item.cantidad:
                raise ValueError(f"Sin stock suficiente para {art.nombre}")

        # Crear préstamo real
        prestamo = AlmacenPrestamo(
            trabajador_id=data.trabajador_id,
            almacenero_id=almacenero_id,
            codigo_unico=data.codigo_unico,
            fecha_prestamo=data.fecha_prestamo,
            fecha_devolucion_prevista=data.fecha_devolucion_prevista,
            firma_base64=data.firma_base64,
            estado=EstadoPrestamo.ABIERTO,
            registrado_por="almacenero"
        )

        detalles = []
        for item in data.items:
            self.repo.update_stock(item.articulo_id, item.cantidad)
            detalles.append(AlmacenPrestamoDetalle(
                articulo_id=item.articulo_id,
                cantidad_prestada=item.cantidad
            ))

        # Guardar préstamo y detalles en DB
        prestamo = self.repo.crear_prestamo(prestamo, detalles)

        # 🔷 Construir esquema enriquecido para PDF
        detalles_schema = []
        for det in prestamo.detalles:
            articulo = self.db.query(AlmacenArticulo).get(det.articulo_id)
            detalles_schema.append(PrestamoDetalleSchema(
                id=det.id,
                articulo_id=det.articulo_id,
                cantidad_prestada=det.cantidad_prestada,
                cantidad_devuelta=det.cantidad_devuelta,
                esta_devuelto=det.esta_devuelto,
                articulo_nombre=articulo.nombre if articulo else "Desconocido",
                articulo_tipo=articulo.tipo.value if articulo else "unknown",
                articulo_unidad=articulo.unidad_medida if articulo else ""
            ))

        prestamo_schema = PrestamoSchema(
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

        # 🔷 Generar PDF
        pdf_path = generar_pdf_prestamo(prestamo_schema)
        prestamo.pdf_url = pdf_path  # opcional, si quieres guardar en DB

        return prestamo

    # =========================
    # Obtener préstamos de un trabajador
    # =========================
    def obtener_prestamos_trabajador(self, trabajador_id: int):
        prestamos = self.db.query(AlmacenPrestamo).options(
            joinedload(AlmacenPrestamo.detalles).joinedload(AlmacenPrestamoDetalle.articulo),
            joinedload(AlmacenPrestamo.trabajador)
        ).filter(
            AlmacenPrestamo.trabajador_id == trabajador_id
        ).all()

        result = []
        for p in prestamos:
            trabajador = p.trabajador
            detalles_enriquecidos = []
            for det in p.detalles:
                art = det.articulo
                detalles_enriquecidos.append(PrestamoDetalleSchema(
                    id=det.id,
                    articulo_id=det.articulo_id,
                    cantidad_prestada=det.cantidad_prestada,
                    cantidad_devuelta=det.cantidad_devuelta,
                    esta_devuelto=det.esta_devuelto,
                    articulo_nombre=art.nombre if art else "Desconocido",
                    articulo_tipo=art.tipo.value if art else "unknown",
                    articulo_unidad=art.unidad_medida if art else ""
                ))

            result.append(PrestamoSchema(
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
                detalles=detalles_enriquecidos
            ))
        return result

    # =========================
    # Obtener préstamos pendientes de un artículo
    # =========================
    def obtener_prestamos_articulo(self, articulo_id: int):
        detalles = self.db.query(AlmacenPrestamoDetalle).options(
            joinedload(AlmacenPrestamoDetalle.prestamo).joinedload(AlmacenPrestamo.trabajador)
        ).filter(
            AlmacenPrestamoDetalle.articulo_id == articulo_id,
            AlmacenPrestamoDetalle.esta_devuelto == False,
            AlmacenPrestamoDetalle.cantidad_devuelta < AlmacenPrestamoDetalle.cantidad_prestada
        ).all()

        result = []
        for det in detalles:
            p = det.prestamo
            t = p.trabajador
            result.append(ArticuloPrestamoSchema(
                trabajador_id=t.id,
                nombres_completos=f"{t.nombre} {t.apellidos}" if t else "Desconocido",
                dni=t.dni if t else "",
                cargo=t.cargo if t else "",
                fecha_prestamo=p.fecha_prestamo,
                cantidad_pendiente=det.cantidad_prestada - det.cantidad_devuelta
            ))
        return result