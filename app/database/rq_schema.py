from sqlalchemy import inspect, text


def actualizar_esquema_rq(engine):
    # Compatibilidad con la primera versión del seguimiento ya instalada.
    columnas = {c['name'] for c in inspect(engine).get_columns('rq_campo_item_seguimiento')}
    if 'detalle' not in columnas:
        with engine.begin() as conexion:
            conexion.execute(text('ALTER TABLE rq_campo_item_seguimiento ADD COLUMN detalle TEXT'))
