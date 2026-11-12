from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo


class PrestamoCalculoService:
    """Calcula tiempo efectivo y costo informativo de artículos devueltos."""

    JORNADA_MINUTOS = 11 * 60
    ZONA_HORARIA = ZoneInfo("America/Lima")
    INTERVALOS_JORNADA = ((time(6, 0), time(12, 0)), (time(13, 0), time(18, 0)))

    @classmethod
    def calcular_minutos_efectivos(
        cls,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> int:
        inicio_utc = cls._a_utc(fecha_inicio)
        fin_utc = cls._a_utc(fecha_fin)
        if fin_utc <= inicio_utc:
            raise ValueError("La devolución debe ser posterior al préstamo")

        inicio_local = inicio_utc.astimezone(cls.ZONA_HORARIA)
        fin_local = fin_utc.astimezone(cls.ZONA_HORARIA)
        segundos_efectivos = 0.0
        dia = inicio_local.date()

        while dia <= fin_local.date():
            for hora_inicio, hora_fin in cls.INTERVALOS_JORNADA:
                ventana_inicio = datetime.combine(
                    dia,
                    hora_inicio,
                    tzinfo=cls.ZONA_HORARIA,
                )
                ventana_fin = datetime.combine(
                    dia,
                    hora_fin,
                    tzinfo=cls.ZONA_HORARIA,
                )
                tramo_inicio = max(inicio_local, ventana_inicio)
                tramo_fin = min(fin_local, ventana_fin)
                if tramo_fin > tramo_inicio:
                    segundos_efectivos += (
                        tramo_fin - tramo_inicio
                    ).total_seconds()
            dia += timedelta(days=1)

        return int(segundos_efectivos // 60)

    @classmethod
    def calcular_importe(
        cls,
        minutos_efectivos: int,
        cantidad: int,
        costo_hora: Decimal | float | int | None,
        costo_dia: Decimal | float | int | None,
    ) -> dict:
        dias_tarifa, minutos_residuales = divmod(
            minutos_efectivos,
            cls.JORNADA_MINUTOS,
        )
        tarifa_hora = cls._decimal(costo_hora)
        tarifa_dia = cls._decimal(costo_dia)
        importe_unitario = (
            tarifa_dia * dias_tarifa
            + tarifa_hora * Decimal(minutos_residuales) / Decimal(60)
        )
        importe_total = (importe_unitario * cantidad).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return {
            "dias_tarifa": dias_tarifa,
            "minutos_residuales": minutos_residuales,
            "costo_hora_aplicado": tarifa_hora,
            "costo_dia_aplicado": tarifa_dia,
            "importe_informativo": importe_total,
        }

    @staticmethod
    def _a_utc(fecha: datetime) -> datetime:
        if fecha.tzinfo is None:
            return fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(timezone.utc)

    @staticmethod
    def _decimal(valor: Decimal | float | int | None) -> Decimal:
        if valor is None:
            return Decimal("0")
        return Decimal(str(valor))
