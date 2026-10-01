from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.vehiculo import Vehiculo
from app.models.transportes_enums import EstadoVehiculo
from app.models.averia import Averia


class LifecycleService:
    """Centraliza las reglas críticas de transición de estado del vehículo.

    Todas las transiciones de estado deben pasar por aquí para evitar que
    cada servicio (ruta, mantenimiento, avería, inspección) implemente su
    propia versión incompatible del ciclo de vida.

    Ciclo de vida:
        disponible -> asignado
        asignado -> en_ruta            (solo con inspección SALIDA aprobada)
        en_ruta  -> en_mantenimiento   (cuando la ruta requiere mantenimiento)
        en_mantenimiento -> observado  (al completarse el mantenimiento)
        observado -> disponible        (solo con inspección POST_MANTENIMIENTO aprobada)
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _validar(estado: str) -> None:
        valores = {e.value for e in EstadoVehiculo}
        if estado not in valores:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado de vehículo inválido: {estado}.",
            )

    def cambiar_estado(
        self,
        vehiculo: Vehiculo,
        nuevo_estado: str,
        *,
        fuerza: bool = False,
    ) -> None:
        """Cambia el estado del vehículo validando la transición.

        Si ``fuerza`` es True, se permite cualquier transición (uso interno
        para casos de emergencia/administrativos) respetando los estados válidos.
        """
        self._validar(nuevo_estado)
        if not fuerza:
            self._validar_transicion(vehiculo.estado, nuevo_estado)
        vehiculo.estado = nuevo_estado

    @staticmethod
    def _validar_transicion(actual: str, nuevo: str) -> None:
        reglas = {
            "disponible": {"asignado", "en_mantenimiento", "inactivo", "bloqueado"},
            "asignado": {"en_ruta", "disponible", "inactivo", "bloqueado"},
            "en_ruta": {"en_mantenimiento", "disponible", "inactivo", "bloqueado"},
            "en_mantenimiento": {"observado", "inactivo", "bloqueado"},
            "observado": {"disponible", "inactivo", "bloqueado", "en_mantenimiento"},
            "bloqueado": {"observado", "disponible", "inactivo", "en_mantenimiento"},
            "inactivo": set(),
        }
        permitidos = reglas.get(actual, set())
        if nuevo not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Transición de estado de vehículo no permitida: "
                    f"{actual} -> {nuevo}."
                ),
            )

    def asignar(self, vehiculo: Vehiculo) -> None:
        self.cambiar_estado(vehiculo, EstadoVehiculo.ASIGNADO.value)

    def iniciar_ruta(self, vehiculo: Vehiculo) -> None:
        self.cambiar_estado(vehiculo, EstadoVehiculo.EN_RUTA.value)

    def enviar_a_mantenimiento(self, vehiculo: Vehiculo) -> None:
        self.cambiar_estado(vehiculo, EstadoVehiculo.EN_MANTENIMIENTO.value)

    def completar_mantenimiento(self, vehiculo: Vehiculo) -> None:
        """Al completarse el mantenimiento el vehículo pasa a OBSERVADO.

        NO pasa directamente a disponible; se requiere una inspección
        POST_MANTENIMIENTO aprobada para liberarlo.
        """
        self.cambiar_estado(vehiculo, EstadoVehiculo.OBSERVADO.value)

    def liberar_post_mantenimiento(self, vehiculo: Vehiculo) -> None:
        """Libera el vehículo a disponible tras inspección POST_MANTENIMIENTO aprobada."""
        self.cambiar_estado(vehiculo, EstadoVehiculo.DISPONIBLE.value)

    def liberar_ruta_normal(self, vehiculo: Vehiculo) -> None:
        """Libera el vehículo a disponible al finalizar una ruta sin fallas."""
        self.cambiar_estado(vehiculo, EstadoVehiculo.DISPONIBLE.value)

    def liberar_cancelacion(self, vehiculo: Vehiculo) -> None:
        """Devuelve un vehículo a disponible al cancelar una ruta pendiente."""
        self.cambiar_estado(vehiculo, EstadoVehiculo.DISPONIBLE.value)

    def bloquear(self, vehiculo: Vehiculo) -> None:
        # Idempotente: si ya está bloqueado, no reintentar la transición.
        if vehiculo.estado == EstadoVehiculo.BLOQUEADO.value:
            return
        self.cambiar_estado(vehiculo, EstadoVehiculo.BLOQUEADO.value)

    # ------------------------------------------------------------------
    # Reglas de avería crítica
    # ------------------------------------------------------------------
    def hay_averia_critica_activa(self, vehiculo_id: int) -> bool:
        """Indica si el vehículo tiene una avería crítica activa."""
        activos = {"reportada", "en_evaluacion", "programada", "en_reparacion"}
        averia = (
            self.db.query(Averia)
            .filter(
                Averia.vehiculo_id == vehiculo_id,
                Averia.criticidad == "critica",
                Averia.estado.in_(activos),
            )
            .first()
        )
        return averia is not None

    def asegurar_vehiculo_operativo(self, vehiculo: Vehiculo) -> None:
        """Bloquea el vehículo si tiene una avería crítica activa.

        Al resolver una avería crítica no debe asumirse disponible si queda
        otra avería crítica activa.
        """
        if self.hay_averia_critica_activa(vehiculo.id):
            self.bloquear(vehiculo)
