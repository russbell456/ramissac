"""Sincroniza los indicadores de foto con el valor alto del artículo.

Ejecutar una vez en despliegues existentes:
    python scripts/migrar_reglas_fotografia_alto_valor.py
"""

from sqlalchemy import create_engine, text

from app.core.config import DATABASE_URL


def main() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            if engine.dialect.name != "postgresql":
                raise RuntimeError(
                    "Esta migración está preparada para PostgreSQL"
                )

            result = connection.execute(
                text(
                    "UPDATE almacen_articulos "
                    "SET requiere_foto_prestamo = es_activo_alto_valor, "
                    "    requiere_foto_devolucion = es_activo_alto_valor "
                    "WHERE requiere_foto_prestamo IS DISTINCT FROM "
                    "      es_activo_alto_valor "
                    "   OR requiere_foto_devolucion IS DISTINCT FROM "
                    "      es_activo_alto_valor"
                )
            )
    finally:
        engine.dispose()

    print(
        "Reglas de fotografía sincronizadas para "
        f"{result.rowcount or 0} artículos."
    )


if __name__ == "__main__":
    main()
