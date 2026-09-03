from sqlalchemy.orm import Session

from app.models.almacen_articulos import (
    AlmacenArticulo,
)

from app.models.almacen_devolucion import (
    AlmacenDevolucion,
    AlmacenDevolucionDetalle,
    EstadoDevolucion,
)

from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
    EstadoPrestamo,
)

from app.models.user import User

from app.repositories.almacen_devolucion_repository import (
    AlmacenDevolucionRepository,
)

from app.schemas.almacen_devolucion import (
    DevolucionQRData,
)

from app.services.auditoria_service import (
    AuditoriaService,
)


class AlmacenDevolucionService:

    def __init__(self, db: Session):

        self.db = db

        self.repo = (
            AlmacenDevolucionRepository(
                db
            )
        )

    # ==================================================
    # REGISTRAR DEVOLUCIÓN
    # ==================================================

    def registrar_devolucion_desde_qr(
        self,
        data: DevolucionQRData,
        almacenero_id: int,
    ):

        try:

            # ==========================================
            # 1. VALIDAR TRABAJADOR
            # ==========================================

            trabajador = (
                self.db.query(User)
                .filter(
                    User.id
                    == data.trabajador_id,

                    User.role
                    == "trabajador",
                )
                .first()
            )

            if not trabajador:

                raise ValueError(
                    "Trabajador no encontrado "
                    "o rol inválido"
                )

            # ==========================================
            # 2. VALIDAR DNI
            # ==========================================

            if trabajador.dni != data.dni:

                raise ValueError(
                    "El DNI no coincide con "
                    "el trabajador"
                )

            # ==========================================
            # 3. VALIDAR NOMBRES
            # ==========================================

            nombres_bd = (
                f"{trabajador.nombre} "
                f"{trabajador.apellidos}"
            ).strip().lower()

            nombres_qr = (
                data.nombres_completos
                .strip()
                .lower()
            )

            if nombres_bd != nombres_qr:

                raise ValueError(
                    "Los nombres no coinciden "
                    "con el trabajador"
                )

            # ==========================================
            # 4. VALIDAR CARGO
            # ==========================================

            if (
                trabajador.cargo
                and trabajador.cargo.strip().lower()
                != data.cargo.strip().lower()
            ):

                raise ValueError(
                    "El cargo no coincide "
                    "con el trabajador"
                )

            # ==========================================
            # 5. VALIDAR CÓDIGO ÚNICO
            # ==========================================

            self._validar_codigo_unico(
                data.codigo_unico
            )

            # ==========================================
            # 6. OBTENER PRÉSTAMO BLOQUEADO
            # ==========================================

            prestamo = (
                self.repo.obtener_prestamo(
                    data.prestamo_id
                )
            )

            if not prestamo:

                raise ValueError(
                    "Préstamo no encontrado"
                )

            # ==========================================
            # 7. VALIDAR ESTADO
            # ==========================================

            if (
                prestamo.estado
                != EstadoPrestamo.ABIERTO
            ):

                raise ValueError(
                    "El préstamo ya está cerrado "
                    "y no admite devoluciones"
                )

            # ==========================================
            # 8. VALIDAR TRABAJADOR DEL PRÉSTAMO
            # ==========================================

            if (
                prestamo.trabajador_id
                != data.trabajador_id
            ):

                raise ValueError(
                    "El trabajador no corresponde "
                    "al préstamo"
                )

            # ==========================================
            # 9. PROCESAR ITEMS
            # ==========================================

            detalles_devolucion = []

            for item in data.items:

                detalle = (
                    self.repo.obtener_detalle_prestamo(
                        item.prestamo_detalle_id
                    )
                )

                if not detalle:

                    raise ValueError(
                        "Detalle de préstamo "
                        f"no encontrado: "
                        f"{item.prestamo_detalle_id}"
                    )

                # ======================================
                # VALIDAR PERTENENCIA AL PRÉSTAMO
                # ======================================

                if (
                    detalle.prestamo_id
                    != prestamo.id
                ):

                    raise ValueError(
                        "El detalle "
                        f"{item.prestamo_detalle_id} "
                        "no pertenece al préstamo "
                        f"{prestamo.id}"
                    )

                # ======================================
                # OBTENER ARTÍCULO
                # ======================================

                articulo = (
                    self.repo.obtener_articulo(
                        detalle.articulo_id
                    )
                )

                if not articulo:

                    raise ValueError(
                        "Artículo no encontrado"
                    )

                # ======================================
                # VALIDAR TIPO
                # ======================================

                tipo = (
                    articulo.tipo.value.upper()
                )

                if tipo not in [
                    "EQUIPO",
                    "HERRAMIENTA",
                ]:

                    raise ValueError(
                        f"El artículo "
                        f"{articulo.nombre} "
                        "no requiere devolución"
                    )

                # ======================================
                # CANTIDAD PENDIENTE
                # ======================================

                pendiente = (
                    detalle.cantidad_prestada
                    - detalle.cantidad_devuelta
                )

                if pendiente <= 0:

                    raise ValueError(
                        f"El artículo "
                        f"{articulo.nombre} "
                        "ya fue completamente "
                        "devuelto"
                    )

                if item.cantidad > pendiente:

                    raise ValueError(
                        f"La cantidad devuelta "
                        f"para {articulo.nombre} "
                        f"excede lo pendiente. "
                        f"Pendiente: {pendiente}"
                    )

                # ======================================
                # FOTOGRAFÍA
                # ======================================

                requiere_foto = (
                    getattr(
                        articulo,
                        "requiere_foto_devolucion",
                        False,
                    )
                    or articulo.es_activo_alto_valor
                )

                if (
                    requiere_foto
                    and not data.foto_estado_devuelto
                ):

                    raise ValueError(
                        "La foto del estado de "
                        "devolución es obligatoria "
                        f"para {articulo.nombre}"
                    )

                # ======================================
                # ACTUALIZAR STOCK
                # ======================================

                self.repo.devolver_stock(
                    articulo=articulo,
                    cantidad=item.cantidad,
                )

                # ======================================
                # ACTUALIZAR DETALLE
                # ======================================

                self.repo.actualizar_detalle(
                    detalle=detalle,
                    cantidad=item.cantidad,
                )

                # ======================================
                # CREAR DETALLE DEVOLUCIÓN
                # ======================================

                detalles_devolucion.append(
                    AlmacenDevolucionDetalle(
                        prestamo_detalle_id=(
                            detalle.id
                        ),
                        cantidad_devuelta=(
                            item.cantidad
                        ),
                    )
                )

            # ==========================================
            # 10. CREAR DEVOLUCIÓN
            # ==========================================

            devolucion = AlmacenDevolucion(

                trabajador_id=(
                    data.trabajador_id
                ),

                almacenero_id=(
                    almacenero_id
                ),

                codigo_unico=(
                    data.codigo_unico
                ),

                prestamo_id=(
                    prestamo.id
                ),

                fecha_devolucion=(
                    data.fecha_devolucion
                ),

                firma_base64=(
                    data.firma_base64
                ),

                estado=(
                    EstadoDevolucion.CONFIRMADA
                ),

                registrado_por="almacenero",

                foto_estado_devuelto=(
                    data.foto_estado_devuelto
                ),

                observacion_estado=(
                    data.observacion_estado
                ),
            )

            devolucion = (
                self.repo.crear_devolucion(
                    devolucion,
                    detalles_devolucion,
                )
            )

            # ==========================================
            # 11. CERRAR PRÉSTAMO SI CORRESPONDE
            # ==========================================

            pendientes = (
                self.db.query(
                    AlmacenPrestamoDetalle
                )
                .filter(
                    AlmacenPrestamoDetalle.prestamo_id
                    == prestamo.id,

                    AlmacenPrestamoDetalle.esta_devuelto
                    == False,
                )
                .count()
            )

            if pendientes == 0:

                prestamo.estado = (
                    EstadoPrestamo.CERRADO
                )

                self.db.flush()

            # ==========================================
            # 12. AUDITORÍA
            # ==========================================

            AuditoriaService(
                self.db
            ).registrar(

                usuario_id=almacenero_id,

                accion="CREAR_DEVOLUCION",

                entidad="DEVOLUCION",

                entidad_id=devolucion.id,

                descripcion=(
                    f"Devolución "
                    f"{devolucion.codigo_unico} "
                    f"registrada para "
                    f"{trabajador.nombre} "
                    f"{trabajador.apellidos}"
                ),
            )

            # ==========================================
            # 13. COMMIT ÚNICO
            # ==========================================

            self.db.commit()

            self.db.refresh(
                devolucion
            )

            return devolucion

        except Exception:

            self.db.rollback()

            raise

    # ==================================================
    # VALIDAR CÓDIGO ÚNICO
    # ==================================================

    def _validar_codigo_unico(
        self,
        codigo_unico: str,
    ):

        existente = (
            self.db.query(
                AlmacenDevolucion
            )
            .filter(
                AlmacenDevolucion.codigo_unico
                == codigo_unico
            )
            .first()
        )

        if existente:

            raise ValueError(
                f"El código único "
                f"{codigo_unico} "
                "ya está registrado"
            )