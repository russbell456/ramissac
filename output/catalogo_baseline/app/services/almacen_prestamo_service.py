import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.almacen_articulos import (
    AlmacenArticulo,
)
from app.models.almacen_obras import AlmacenObra
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
    SolicitudPrestamoData,
    ConfirmacionSolicitudPrestamo,
    SolicitudPrestamoResumen,
    TipoPrestamoSchema,
)

from app.services.auditoria_service import (
    AuditoriaService,
)
from app.utils.pdf_generator import generar_pdf_prestamo
from app.utils.evidence_storage import public_asset_url, rename_stored_upload


class AlmacenPrestamoService:

    def __init__(self, db: Session):

        self.db = db

        self.repo = AlmacenPrestamoRepository(
            db
        )

    @staticmethod
    def _nombrar_evidencias(prestamo: AlmacenPrestamo) -> None:
        """Use traceable loan/detail names after database IDs are assigned."""
        if prestamo.firma_base64:
            prestamo.firma_base64 = rename_stored_upload(
                prestamo.firma_base64, f"firma_prestamo_{prestamo.id}.png"
            )
        for detalle in prestamo.detalles:
            if detalle.foto_estado_inicio:
                detalle.foto_estado_inicio = rename_stored_upload(
                    detalle.foto_estado_inicio,
                    f"prestamo_{prestamo.id}_detalle_{detalle.id}.png",
                )

    def crear_solicitud_trabajador(
        self,
        trabajador_id: int,
        data: SolicitudPrestamoData,
    ) -> AlmacenPrestamo:
        """Crea una solicitud QR pendiente sin reservar ni descontar stock."""
        try:
            trabajador = self.db.query(User).filter(
                User.id == trabajador_id,
                User.role == "trabajador",
            ).first()
            if not trabajador:
                raise ValueError("Trabajador no encontrado o rol inválido")

            ahora = datetime.utcnow()
            if data.tipo_prestamo == TipoPrestamoSchema.EXTERNO:
                raise ValueError(
                    "Las solicitudes externas deben registrarse manualmente por almacén"
                )
            fecha_prevista = data.fecha_devolucion_prevista
            if fecha_prevista.tzinfo is not None:
                fecha_prevista = fecha_prevista.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)
            if fecha_prevista <= ahora:
                raise ValueError(
                    "La fecha prevista debe ser posterior a la solicitud"
                )

            self._validar_tipo_prestamo(data)
            if data.tipo_prestamo == TipoPrestamoSchema.OBRA:
                obra = self.db.query(AlmacenObra).filter(
                    AlmacenObra.id == data.obra_id,
                    AlmacenObra.estado == "activo",
                ).first()
                if not obra:
                    raise ValueError("La obra indicada no existe o no está activa")

            detalles = []
            for item in data.items:
                articulo = self.repo.obtener_articulo(item.articulo_id)
                if not articulo or not articulo.activo:
                    raise ValueError(
                        f"Artículo no encontrado o inactivo: {item.articulo_id}"
                    )
                if articulo.stock_actual < item.cantidad:
                    raise ValueError(
                        f"Stock insuficiente para {articulo.nombre}. "
                        f"Disponible: {articulo.stock_actual}, solicitado: {item.cantidad}"
                    )
                if articulo.es_activo_alto_valor and item.cantidad != 1:
                    raise ValueError(
                        f"El artículo {articulo.nombre} es de alto valor "
                        "y solo puede solicitarse de uno en uno"
                    )
                requiere_devolucion = articulo.tipo.value.upper() in [
                    "EQUIPO", "HERRAMIENTA"
                ]
                detalles.append(AlmacenPrestamoDetalle(
                    articulo_id=articulo.id,
                    cantidad_prestada=item.cantidad,
                    cantidad_devuelta=0,
                    esta_devuelto=not requiere_devolucion,
                ))

            codigo = f"SOL-{secrets.token_urlsafe(18)}"
            prestamo = AlmacenPrestamo(
                trabajador_id=trabajador.id,
                almacenero_id=None,
                obra_id=data.obra_id,
                codigo_unico=codigo,
                fecha_prestamo=ahora,
                fecha_devolucion_prevista=fecha_prevista,
                firma_base64=None,
                estado=EstadoPrestamo.PENDIENTE,
                registrado_por="trabajador_qr",
                tipo_prestamo=TipoPrestamo(data.tipo_prestamo.value),
                empresa_ruc=data.empresa_ruc,
                empresa_nombre=data.empresa_nombre,
                persona_dni=data.persona_dni,
                persona_nombres=data.persona_nombres,
                persona_telefono=data.persona_telefono,
            )
            prestamo = self.repo.crear_prestamo(prestamo, detalles)
            self.db.commit()
            self.db.refresh(prestamo)
            return prestamo
        except Exception:
            self.db.rollback()
            raise

    def obtener_solicitud_qr(
        self,
        codigo_unico: str,
    ) -> SolicitudPrestamoResumen:
        prestamo = self.repo.obtener_por_codigo(codigo_unico)
        if not prestamo:
            raise ValueError("Solicitud de préstamo no encontrada")
        if prestamo.estado != EstadoPrestamo.PENDIENTE:
            raise ValueError("La solicitud ya fue confirmada o ya no está pendiente")

        schema = self._map_prestamo_to_schema(prestamo)
        return SolicitudPrestamoResumen(
            id=schema.id,
            trabajador_id=schema.trabajador_id,
            nombres_completos=schema.nombres_completos,
            dni=schema.dni,
            cargo=schema.cargo,
            codigo_unico=schema.codigo_unico,
            fecha_devolucion_prevista=schema.fecha_devolucion_prevista,
            estado=schema.estado,
            tipo_prestamo=schema.tipo_prestamo,
            obra_id=schema.obra_id,
            empresa_ruc=schema.empresa_ruc,
            empresa_nombre=schema.empresa_nombre,
            persona_dni=schema.persona_dni,
            persona_nombres=schema.persona_nombres,
            persona_telefono=schema.persona_telefono,
            detalles=schema.detalles,
        )

    def confirmar_solicitud_qr(
        self,
        prestamo_id: int,
        almacenero_id: int,
        data: ConfirmacionSolicitudPrestamo,
    ) -> AlmacenPrestamo:
        """Confirma entrega; valida stock y lo descuenta en la misma transacción."""
        try:
            prestamo = self.repo.obtener_prestamo_bloqueado(prestamo_id)
            if not prestamo:
                raise ValueError("Solicitud de préstamo no encontrada")
            if prestamo.estado != EstadoPrestamo.PENDIENTE:
                raise ValueError("La solicitud ya fue confirmada o ya no está pendiente")

            ahora = datetime.utcnow()
            if prestamo.fecha_devolucion_prevista <= ahora:
                raise ValueError(
                    "La fecha prevista de devolución ya venció; actualiza la solicitud"
                )

            fotos = {
                foto.articulo_id: foto.foto_estado_inicio
                for foto in data.fotos
            }
            ids_detalle = {detalle.articulo_id for detalle in prestamo.detalles}
            if not set(fotos).issubset(ids_detalle):
                raise ValueError("La foto enviada no pertenece a esta solicitud")

            for detalle in prestamo.detalles:
                articulo = self.repo.obtener_articulo(
                    detalle.articulo_id,
                    bloquear=True,
                )
                if not articulo or not articulo.activo:
                    raise ValueError(
                        f"Artículo no encontrado o inactivo: {detalle.articulo_id}"
                    )
                if articulo.stock_actual < detalle.cantidad_prestada:
                    raise ValueError(
                        f"Stock insuficiente para {articulo.nombre}. "
                        f"Disponible: {articulo.stock_actual}, "
                        f"solicitado: {detalle.cantidad_prestada}"
                    )
                if articulo.es_activo_alto_valor:
                    if detalle.cantidad_prestada != 1:
                        raise ValueError(
                            f"El artículo {articulo.nombre} es de alto valor "
                            "y solo puede entregarse de uno en uno"
                        )
                    if not fotos.get(articulo.id):
                        raise ValueError(
                            f"La foto del estado inicial es obligatoria para {articulo.nombre}"
                        )
                    detalle.foto_estado_inicio = fotos[articulo.id]

                requiere_devolucion = articulo.tipo.value.upper() in [
                    "EQUIPO", "HERRAMIENTA"
                ]
                self.repo.descontar_stock(
                    articulo=articulo,
                    cantidad=detalle.cantidad_prestada,
                    requiere_devolucion=requiere_devolucion,
                )

            prestamo.almacenero_id = almacenero_id
            prestamo.firma_base64 = data.firma_base64
            prestamo.fecha_prestamo = ahora
            prestamo.estado = EstadoPrestamo.ABIERTO
            AuditoriaService(self.db).registrar(
                usuario_id=almacenero_id,
                accion="CONFIRMAR_PRESTAMO_QR",
                entidad="PRESTAMO",
                entidad_id=prestamo.id,
                descripcion=f"Entrega confirmada para solicitud {prestamo.codigo_unico}",
            )
            self.db.flush()
            self._nombrar_evidencias(prestamo)
            generar_pdf_prestamo(prestamo)
            self.db.commit()
            self.db.refresh(prestamo)
            return prestamo
        except Exception:
            self.db.rollback()
            raise

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

            if (
                data.tipo_prestamo == TipoPrestamoSchema.OBRA
                and not self.db.query(AlmacenObra).filter(
                    AlmacenObra.id == data.obra_id,
                    AlmacenObra.estado == "activo",
                ).first()
            ):
                raise ValueError(
                    "La obra indicada no existe o no está activa"
                )

            fecha_prestamo_confirmacion = datetime.utcnow()
            fecha_prevista = data.fecha_devolucion_prevista
            if fecha_prevista.tzinfo is not None:
                fecha_prevista = fecha_prevista.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)
            if fecha_prevista <= fecha_prestamo_confirmacion:
                raise ValueError(
                    "La fecha prevista debe ser posterior a la confirmación de entrega"
                )

            # ------------------------------------------
            # 5. AGRUPAR ARTÍCULOS
            # ------------------------------------------

            # El schema impide artículos repetidos para mantener la foto
            # vinculada al detalle correcto.
            items = {
                item.articulo_id: item
                for item in data.items
            }

            detalles = []

            # ------------------------------------------
            # 6. PROCESAR ARTÍCULOS
            # ------------------------------------------

            for articulo_id, item_prestamo in items.items():

                cantidad = item_prestamo.cantidad

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

                requiere_foto = articulo.es_activo_alto_valor

                foto_estado_inicio = (
                    item_prestamo.foto_estado_inicio
                )

                # Compatibilidad con clientes antiguos: aceptar la foto
                # raíz únicamente para un préstamo de un artículo.
                if (
                    not foto_estado_inicio
                    and len(items) == 1
                    and data.foto_estado_inicio
                ):
                    foto_estado_inicio = data.foto_estado_inicio

                if (
                    requiere_foto
                    and not foto_estado_inicio
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
                        foto_estado_inicio=(
                            foto_estado_inicio
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
                    fecha_prestamo_confirmacion
                ),

                fecha_devolucion_prevista=(
                    fecha_prevista
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

            self.db.flush()
            self._nombrar_evidencias(prestamo)
            generar_pdf_prestamo(prestamo)

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

            if data.obra_id is not None:

                raise ValueError(
                    "Un préstamo interno "
                    "no debe tener una obra"
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

        elif data.tipo_prestamo == TipoPrestamoSchema.OBRA:

            if data.obra_id is None:
                raise ValueError(
                    "Un préstamo para obra debe indicar una obra"
                )

            if any([
                data.empresa_ruc,
                data.empresa_nombre,
                data.persona_dni,
                data.persona_nombres,
                data.persona_telefono,
            ]):
                raise ValueError(
                    "Un préstamo para obra no puede contener datos externos"
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
                == trabajador_id,
                AlmacenPrestamo.estado
                != EstadoPrestamo.PENDIENTE,
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
        devoluciones_schema = []
        fotos_fin_por_detalle = {}
        for devolucion in (getattr(prestamo, "devoluciones", []) or []):
            almacenero_devolucion = getattr(devolucion, "almacenero", None)
            devolucion_detalles = []
            for detalle_devolucion in (getattr(devolucion, "detalles", []) or []):
                foto_fin_url = public_asset_url(detalle_devolucion.foto_estado_devuelto)
                fotos_fin_por_detalle[detalle_devolucion.prestamo_detalle_id] = foto_fin_url
                devolucion_detalles.append({
                    "prestamo_detalle_id": detalle_devolucion.prestamo_detalle_id,
                    "cantidad_devuelta": detalle_devolucion.cantidad_devuelta,
                    "foto_estado_fin_url": foto_fin_url,
                })
            nombre_almacenero = " ".join(filter(None, [
                getattr(almacenero_devolucion, "nombre", None),
                getattr(almacenero_devolucion, "apellidos", None),
            ])) or None
            devoluciones_schema.append({
                "id": devolucion.id,
                "codigo_unico": devolucion.codigo_unico,
                "fecha_devolucion": devolucion.fecha_devolucion,
                "almacenero_id": devolucion.almacenero_id,
                "almacenero_nombre": nombre_almacenero,
                "firma_url": public_asset_url(devolucion.firma_base64),
                "detalles": devolucion_detalles,
            })

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

                    requiere_foto_devolucion=(
                        bool(articulo and articulo.es_activo_alto_valor)
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

                    foto_estado_inicio_url=(
                        public_asset_url(detalle.foto_estado_inicio)
                    ),
                    foto_estado_fin_url=fotos_fin_por_detalle.get(detalle.id),
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

            firma_url=(
                public_asset_url(prestamo.firma_base64)
            ),

            estado=(
                prestamo.estado.value
            ),

            registrado_por=(
                prestamo.registrado_por
            ),

            almacenero_id=prestamo.almacenero_id,

            almacenero_nombre=(
                " ".join(filter(None, [
                    getattr(prestamo.almacenero, "nombre", None),
                    getattr(prestamo.almacenero, "apellidos", None),
                ])) or None
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
            devoluciones=devoluciones_schema,
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
