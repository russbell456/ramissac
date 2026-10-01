from __future__ import annotations

import enum


class EstadoVehiculo(enum.Enum):
    """Estados válidos del ciclo de vida de un vehículo.

    La columna ``vehiculos.estado`` se mantiene como ``String`` en la BD para
    minimizar el riesgo de migración. Los valores válidos se centralizan aquí
    en Python y se validan en las capas de servicio.
    """
    DISPONIBLE = "disponible"
    ASIGNADO = "asignado"
    EN_RUTA = "en_ruta"
    EN_MANTENIMIENTO = "en_mantenimiento"
    BLOQUEADO = "bloqueado"
    OBSERVADO = "observado"
    INACTIVO = "inactivo"


class EstadoRuta(enum.Enum):
    """Estados del ciclo de vida de una asignación de ruta."""
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    INACTIVO = "inactivo"


class TipoInspeccion(enum.Enum):
    """Tipos de inspección de vehículo."""
    SALIDA = "SALIDA"
    LLEGADA = "LLEGADA"
    EXTRAORDINARIA = "EXTRAORDINARIA"
    POST_ACCIDENTE = "POST_ACCIDENTE"
    POST_MANTENIMIENTO = "POST_MANTENIMIENTO"


class EstadoInspeccion(enum.Enum):
    """Resultados globales de una inspección."""
    APROBADA = "APROBADA"
    APROBADA_CON_OBSERVACIONES = "APROBADA_CON_OBSERVACIONES"
    RECHAZADA = "RECHAZADA"


class ResultadoChecklist(enum.Enum):
    """Resultado de cada ítem de detalle de inspección."""
    CONFORME = "conforme"
    OBSERVADO = "observado"
    NO_CONFORME = "no_conforme"
    NO_APLICA = "no_aplica"


class CriticidadItem(enum.Enum):
    """Criticidad de un ítem del checklist."""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class TipoMantenimiento(enum.Enum):
    """Tipo de mantenimiento de vehículo."""
    PREVENTIVO = "PREVENTIVO"
    CORRECTIVO = "CORRECTIVO"


class EstadoMantenimiento(enum.Enum):
    """Estados del ciclo de vida de un mantenimiento."""
    EN_TALLER = "en_taller"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"
    INACTIVO = "inactivo"


class TipoControlMantenimiento(enum.Enum):
    """Tipo de control del mantenimiento preventivo."""
    KILOMETRAJE = "kilometraje"
    FECHA = "fecha"
    HORAS = "horas"
    MIXTO = "mixto"


class EstadoControl(enum.Enum):
    """Estado de control de un plan de mantenimiento preventivo."""
    NORMAL = "NORMAL"
    PROXIMO = "PROXIMO"
    VENCIDO = "VENCIDO"


class EstadoAveria(enum.Enum):
    """Ciclo de vida de una avería."""
    REPORTADA = "reportada"
    EN_EVALUACION = "en_evaluacion"
    PROGRAMADA = "programada"
    EN_REPARACION = "en_reparacion"
    RESUELTA = "resuelta"
    CERRADA = "cerrada"


class CriticidadAveria(enum.Enum):
    """Criticidad de una avería."""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class EstadoIncidente(enum.Enum):
    """Ciclo de vida de un incidente."""
    REPORTADO = "reportado"
    EN_EVALUACION = "en_evaluacion"
    CERRADO = "cerrado"


class TipoIncidente(enum.Enum):
    """Naturaleza de un incidente de operación."""
    ACCIDENTE = "accidente"
    INCIDENTE = "incidente"
    NOVEDAD = "novedad"


class EstadoJornada(enum.Enum):
    """Estados del ciclo de una jornada de transporte."""

    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"
    CANCELADA_POR_AVERIA = "cancelada_por_averia"


class TipoChecklistJornada(enum.Enum):
    INICIAL = "inicial"
    FINAL = "final"


class TipoIncidenciaRuta(enum.Enum):
    FALLA = "falla"
    ACCIDENTE = "accidente"
    COMBUSTIBLE = "combustible"
