from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.almacen_articulos import (
    AlmacenArticulo,
)
from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
    EstadoPrestamo,
    TipoPrestamo,
)
from app.models.user import User

from app.repositories.almacen_prestamo_repository import (
    AlmacenPrestamoRepository,
)

from app.schemas.almacen_prestamo import (
    ArticuloPrestamoSchema,
    PrestamoDetalleSchema,
    PrestamoQRData,
    PrestamoSchema,
    TipoPrestamoSchema,
)

from app.services.auditoria_service import (
    AuditoriaService,
)


class AlmacenPrestamoService:

    def __init__(self, db: Session):

        self.db = db

        self.repo = AlmacenPrestamoRepository(
            db
        )

    # ==================================================
    # REGISTRAR PRÉSTAMO
    # ==================================================

    def registrar_prestamo_desde_qr(
        self,
        data: PrestamoQRData,
        almacenero_id: int,
    ):

        try:

            # ------------------------------------------
            # 1. VALIDAR TRABAJADOR
            # ------------------------------------------

            trabajador = (
                self.db.query(User)
                .filter(
                    User.id == data.trabajador_id,
                    User.role == "trabajador",
                )
                .first()
            )

            if not trabajador:

                raise ValueError(
                    "Trabajador no encontrado "
                    "o rol inválido"
                )

            # ------------------------------------------
            # 2. VALIDAR DATOS DEL TRABAJADOR
            # ------------------------------------------

            if trabajador.dni != data.dni:

                raise ValueError(
                    "El DNI no coincide con "
                    "el trabajador"
                )

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

            if (
                trabajador.cargo
                and trabajador.cargo.strip().lower()
                != data.cargo.strip().lower()
            ):

                raise ValueError(
                    "El cargo no coincide "
                    "con el trabajador"
                )

            # ------------------------------------------
            # 3. VALIDAR CÓDIGO ÚNICO
            # ------------------------------------------

            self._validar_codigo_unico(
                data.codigo_unico
            )

            # ------------------------------------------
            # 4. VALIDAR TIPO DE PRÉSTAMO
            # ------------------------------------------

            self._validar_tipo_prestamo(
                data
            )

            # ------------------------------------------
            # 5. AGRUPAR ARTÍCULOS
            # ------------------------------------------

            items = self._agrupar_items(
                data.items
            )

            detalles = []

            # ------------------------------------------
            # 6. PROCESAR ARTÍCULOS
            # ------------------------------------------

            for articulo_id, cantidad in items.items():

                articulo = (
                    self.repo.obtener_articulo(
                        articulo_id,
                        bloquear=True,
                    )
                )

                if not articulo:

                    raise ValueError(
                        f"Artículo no encontrado: "
                        f"{articulo_id}"
                    )

                # --------------------------------------
                # ARTÍCULO ACTIVO
                # --------------------------------------

                if not articulo.activo:

                    raise ValueError(
                        f"El artículo "
                        f"{articulo.nombre} "
                        f"está inactivo"
                    )

                # --------------------------------------
                # TIPO
                # --------------------------------------

                tipo = (
                    articulo.tipo.value.upper()
                )

                if tipo not in [
                    "EQUIPO",
                    "HERRAMIENTA",
                    "CONSUMIBLE",
                ]:

                    raise ValueError(
                        f"Tipo de artículo inválido "
                        f"para {articulo.nombre}"
                    )

                requiere_devolucion = (
                    tipo in [
                        "EQUIPO",
                        "HERRAMIENTA",
                    ]
                )

                # --------------------------------------
                # ACTIVO DE ALTO VALOR
                # --------------------------------------

                if (
                    articulo.es_activo_alto_valor
                    and cantidad != 1
                ):

                    raise ValueError(
                        f"El artículo "
                        f"{articulo.nombre} "
                        f"es un activo de alto valor "
                        f"y solo puede prestarse "
                        f"de uno en uno"
                    )

                # --------------------------------------
                # FOTOGRAFÍA
                # --------------------------------------

                requiere_foto = (
                    getattr(
                        articulo,
                        "requiere_foto_prestamo",
                        False,
                    )
                    or articulo.es_activo_alto_valor
                )

                if (
                    requiere_foto
                    and not data.foto_estado_inicio
                ):

                    raise ValueError(
                        "La foto del estado inicial "
                        "es obligatoria para "
                        f"{articulo.nombre}"
                    )

                # --------------------------------------
                # STOCK
                # --------------------------------------

                if (
                    articulo.stock_actual
                    < cantidad
                ):

                    raise ValueError(
                        f"Stock insuficiente para "
                        f"{articulo.nombre}. "
                        f"Disponible: "
                        f"{articulo.stock_actual}, "
                        f"solicitado: {cantidad}"
                    )

                # --------------------------------------
                # DESCONTAR STOCK
                # --------------------------------------

                self.repo.descontar_stock(
                    articulo=articulo,
                    cantidad=cantidad,
                    requiere_devolucion=(
                        requiere_devolucion
                    ),
                )

                # --------------------------------------
                # CREAR DETALLE
                # --------------------------------------

                detalles.append(
                    AlmacenPrestamoDetalle(
                        articulo_id=articulo_id,
                        cantidad_prestada=cantidad,
                        cantidad_devuelta=0,

                        # Los consumibles no se devuelven.
                        esta_devuelto=(
                            not requiere_devolucion
                        ),
                    )
                )

            # ------------------------------------------
            # 7. CREAR PRÉSTAMO
            # ------------------------------------------

            prestamo = AlmacenPrestamo(

                trabajador_id=(
                    data.trabajador_id
                ),

                almacenero_id=(
                    almacenero_id
                ),

                obra_id=data.obra_id,

                codigo_unico=(
                    data.codigo_unico
                ),

                fecha_prestamo=(
                    data.fecha_prestamo
                ),

                fecha_devolucion_prevista=(
                    data.fecha_devolucion_prevista
                ),

                firma_base64=(
                    data.firma_base64
                ),

                estado=(
                    EstadoPrestamo.ABIERTO
                ),

                registrado_por="almacenero",

                tipo_prestamo=TipoPrestamo(
                    data.tipo_prestamo.value
                ),

                empresa_ruc=(
                    data.empresa_ruc
                ),

                empresa_nombre=(
                    data.empresa_nombre
                ),

                persona_dni=(
                    data.persona_dni
                ),

                persona_nombres=(
                    data.persona_nombres
                ),

                persona_telefono=(
                    data.persona_telefono
                ),

                foto_estado_inicio=(
                    data.foto_estado_inicio
                ),
            )

            prestamo = (
                self.repo.crear_prestamo(
                    prestamo,
                    detalles,
                )
            )

            # ------------------------------------------
            # 8. AUDITORÍA
            # ------------------------------------------

            AuditoriaService(
                self.db
            ).registrar(

                usuario_id=almacenero_id,

                accion="CREAR_PRESTAMO",

                entidad="PRESTAMO",

                entidad_id=prestamo.id,

                descripcion=(
                    f"Préstamo "
                    f"{prestamo.codigo_unico} "
                    f"registrado para "
                    f"{trabajador.nombre} "
                    f"{trabajador.apellidos}"
                ),
            )

            # ------------------------------------------
            # 9. COMMIT ÚNICO
            # ------------------------------------------

            self.db.commit()

            self.db.refresh(
                prestamo
            )

            return prestamo

        except Exception:

            self.db.rollback()

            raise

    # ==================================================
    # AGRUPAR ITEMS
    # ==================================================

    @staticmethod
    def _agrupar_items(items):

        resultado = {}

        for item in items:

            if item.articulo_id not in resultado:

                resultado[item.articulo_id] = 0

            resultado[item.articulo_id] += (
                item.cantidad
            )

        return resultado

    # ==================================================
    # VALIDAR CÓDIGO
    # ==================================================

    def _validar_codigo_unico(
        self,
        codigo_unico: str,
    ):

        existente = (
            self.db.query(AlmacenPrestamo)
            .filter(
                AlmacenPrestamo.codigo_unico
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

    # ==================================================
    # VALIDAR TIPO DE PRÉSTAMO
    # ==================================================

    @staticmethod
    def _validar_tipo_prestamo(
        data: PrestamoQRData,
    ):

        if (
            data.tipo_prestamo
            == TipoPrestamoSchema.INTERNO
        ):

            if data.obra_id is None:

                raise ValueError(
                    "Un préstamo interno "
                    "debe tener una obra"
                )

            if any([
                data.empresa_ruc,
                data.empresa_nombre,
                data.persona_dni,
                data.persona_nombres,
                data.persona_telefono,
            ]):

                raise ValueError(
                    "Un préstamo interno "
                    "no puede contener datos "
                    "externos"
                )

        elif (
            data.tipo_prestamo
            == TipoPrestamoSchema.EXTERNO
        ):

            if data.obra_id is not None:

                raise ValueError(
                    "Un préstamo externo "
                    "no puede tener una obra"
                )

            if not data.empresa_ruc:

                raise ValueError(
                    "El RUC es obligatorio"
                )

            if not data.empresa_nombre:

                raise ValueError(
                    "El nombre de la empresa "
                    "es obligatorio"
                )

            if not data.persona_dni:

                raise ValueError(
                    "El DNI del responsable "
                    "es obligatorio"
                )

            if not data.persona_nombres:

                raise ValueError(
                    "El nombre del responsable "
                    "es obligatorio"
                )

            if not data.persona_telefono:

                raise ValueError(
                    "El teléfono del responsable "
                    "es obligatorio"
                )

    # ==================================================
    # OBTENER PRÉSTAMOS DE TRABAJADOR
    # ==================================================

    def obtener_prestamos_trabajador(
        self,
        trabajador_id: int,
    ):

        prestamos = (
            self.db.query(
                AlmacenPrestamo
            )
            .options(
                joinedload(
                    AlmacenPrestamo.detalles
                ).joinedload(
                    AlmacenPrestamoDetalle.articulo
                ),

                joinedload(
                    AlmacenPrestamo.trabajador
                ),
            )
            .filter(
                AlmacenPrestamo.trabajador_id
                == trabajador_id
            )
            .all()
        )

        return [
            self._map_prestamo_to_schema(
                prestamo
            )
            for prestamo in prestamos
        ]

    # ==================================================
    # MAPEAR PRÉSTAMO
    # ==================================================

    def _map_prestamo_to_schema(
        self,
        prestamo: AlmacenPrestamo,
    ) -> PrestamoSchema:

        trabajador = (
            prestamo.trabajador
        )

        detalles = []

        for detalle in prestamo.detalles:

            articulo = detalle.articulo

            if articulo:

                tipo = (
                    articulo.tipo.value.upper()
                )

            else:

                tipo = "DESCONOCIDO"

            requiere_devolucion = (
                tipo in [
                    "EQUIPO",
                    "HERRAMIENTA",
                ]
            )

            cantidad_pendiente = max(
                detalle.cantidad_prestada
                - detalle.cantidad_devuelta,
                0,
            )

            detalles.append(
                PrestamoDetalleSchema(

                    id=detalle.id,

                    articulo_id=(
                        detalle.articulo_id
                    ),

                    cantidad_prestada=(
                        detalle.cantidad_prestada
                    ),

                    cantidad_devuelta=(
                        detalle.cantidad_devuelta
                    ),

                    cantidad_pendiente=(
                        cantidad_pendiente
                        if requiere_devolucion
                        else 0
                    ),

                    esta_devuelto=(
                        detalle.esta_devuelto
                    ),

                    requiere_devolucion=(
                        requiere_devolucion
                    ),

                    articulo_nombre=(
                        articulo.nombre
                        if articulo
                        else "Desconocido"
                    ),

                    articulo_tipo=(
                        articulo.tipo.value
                        if articulo
                        else "desconocido"
                    ),

                    articulo_unidad=(
                        articulo.unidad_medida
                        if articulo
                        else ""
                    ),
                )
            )

        return PrestamoSchema(

            id=prestamo.id,

            trabajador_id=(
                prestamo.trabajador_id
            ),

            nombres_completos=(
                f"{trabajador.nombre} "
                f"{trabajador.apellidos}"
                if trabajador
                else "Desconocido"
            ),

            dni=(
                trabajador.dni
                if trabajador
                else ""
            ),

            cargo=(
                trabajador.cargo
                if trabajador
                else ""
            ),

            codigo_unico=(
                prestamo.codigo_unico
            ),

            fecha_prestamo=(
                prestamo.fecha_prestamo
            ),

            fecha_devolucion_prevista=(
                prestamo.fecha_devolucion_prevista
            ),

            firma_base64=(
                prestamo.firma_base64
            ),

            estado=(
                prestamo.estado.value
            ),

            registrado_por=(
                prestamo.registrado_por
            ),

            fecha_registro=(
                prestamo.fecha_registro
            ),

            tipo_prestamo=(
                prestamo.tipo_prestamo.value
            ),

            obra_id=(
                prestamo.obra_id
            ),

            empresa_ruc=(
                prestamo.empresa_ruc
            ),

            empresa_nombre=(
                prestamo.empresa_nombre
            ),

            persona_dni=(
                prestamo.persona_dni
            ),

            persona_nombres=(
                prestamo.persona_nombres
            ),

            persona_telefono=(
                prestamo.persona_telefono
            ),

            detalles=detalles,
        )

    # ==================================================
    # PRÉSTAMOS ABIERTOS DE UN ARTÍCULO
    # ==================================================

    def obtener_prestamos_articulo(
        self,
        articulo_id: int,
    ):

        detalles = (
            self.db.query(
                AlmacenPrestamoDetalle
            )
            .join(
                AlmacenPrestamo,
                AlmacenPrestamo.id
                == AlmacenPrestamoDetalle.prestamo_id,
            )
            .options(
                joinedload(
                    AlmacenPrestamoDetalle.prestamo
                ).joinedload(
                    AlmacenPrestamo.trabajador
                )
            )
            .filter(

                AlmacenPrestamoDetalle.articulo_id
                == articulo_id,

                AlmacenPrestamoDetalle.cantidad_devuelta
                <
                AlmacenPrestamoDetalle.cantidad_prestada,

                AlmacenPrestamoDetalle.esta_devuelto
                == False,

                AlmacenPrestamo.estado
                == EstadoPrestamo.ABIERTO,
            )
            .all()
        )

        return [
            self._map_articulo_prestamo(
                detalle
            )
            for detalle in detalles
        ]

    # ==================================================
    # MAPEAR ARTÍCULO PRESTADO
    # ==================================================

    @staticmethod
    def _map_articulo_prestamo(
        detalle: AlmacenPrestamoDetalle,
    ) -> ArticuloPrestamoSchema:

        prestamo = (
            detalle.prestamo
        )

        trabajador = (
            prestamo.trabajador
        )

        return ArticuloPrestamoSchema(

            trabajador_id=(
                trabajador.id
            ),

            nombres_completos=(
                f"{trabajador.nombre} "
                f"{trabajador.apellidos}"
                if trabajador
                else "Desconocido"
            ),

            dni=(
                trabajador.dni
                if trabajador
                else ""
            ),

            cargo=(
                trabajador.cargo
                if trabajador
                else ""
            ),

            fecha_prestamo=(
                prestamo.fecha_prestamo
            ),

            cantidad_pendiente=(
                detalle.cantidad_prestada
                - detalle.cantidad_devuelta
            ),
        )