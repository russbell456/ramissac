"""Migra PostgreSQL para el flujo de préstamos y devoluciones.

Ejecutar una vez antes de desplegar la aplicación:
    python scripts/migrar_prestamo_tipo_obra_fotos.py
"""

from sqlalchemy import create_engine, inspect, text

from app.core.config import DATABASE_URL


def main() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.begin() as connection:
        if engine.dialect.name != "postgresql":
            raise RuntimeError(
                "Esta migración está preparada para PostgreSQL"
            )

        connection.execute(
            text(
                "ALTER TYPE tipoprestamo "
                "ADD VALUE IF NOT EXISTS 'OBRA'"
            )
        )
        connection.execute(
            text(
                "ALTER TYPE estadoprestamo "
                "ADD VALUE IF NOT EXISTS 'PENDIENTE'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE almacen_prestamos "
                "ALTER COLUMN firma_base64 DROP NOT NULL"
            )
        )

        columns = {
            column["name"]
            for column in inspect(connection).get_columns(
                "almacen_prestamo_detalles"
            )
        }
        if "foto_estado_inicio" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE almacen_prestamo_detalles "
                    "ADD COLUMN foto_estado_inicio TEXT"
                )
            )

        columnas_devolucion = {
            column["name"]
            for column in inspect(connection).get_columns(
                "almacen_devolucion_detalles"
            )
        }
        if "foto_estado_devuelto" not in columnas_devolucion:
            connection.execute(
                text(
                    "ALTER TABLE almacen_devolucion_detalles "
                    "ADD COLUMN foto_estado_devuelto TEXT"
                )
            )

        columnas_calculo = {
            "minutos_efectivos": "INTEGER NOT NULL DEFAULT 0",
            "dias_tarifa": "INTEGER NOT NULL DEFAULT 0",
            "minutos_residuales": "INTEGER NOT NULL DEFAULT 0",
            "costo_hora_aplicado": "NUMERIC(10, 2)",
            "costo_dia_aplicado": "NUMERIC(10, 2)",
            "importe_informativo": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
        }
        for nombre_columna, tipo_columna in columnas_calculo.items():
            if nombre_columna not in columnas_devolucion:
                connection.execute(
                    text(
                        "ALTER TABLE almacen_devolucion_detalles "
                        f"ADD COLUMN {nombre_columna} {tipo_columna}"
                    )
                )

    engine.dispose()
    print("Migración de préstamos completada.")


if __name__ == "__main__":
    main()
