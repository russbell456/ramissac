"""Verificación aislada de 006/007: nunca utiliza DATABASE_URL del proyecto."""
import os
os.environ['TESTING'] = '1'
from pathlib import Path
from sqlalchemy import create_engine, MetaData, inspect, text
import app.models
from app.database.base import Base

URL = 'postgresql+psycopg2://codex_test@127.0.0.1:55437/codex_v3_verify'
NUEVAS_TABLAS = {'auditoria_sistema', 'documentos_transporte', 'notificaciones_transporte', 'dispositivos_push'}
COLUMNAS = {
    'jornadas_transporte': {'motivo_cancelacion', 'cancelado_por_id', 'odometro_evidencia_url', 'odometro_motivo',
        'odometro_requiere_revision', 'cerrado_por_sistema', 'fin_operativo', 'solicitud_id', 'fotos_observacion', 'observacion_resuelta'},
    'incidencias_ruta': {'fotos', 'resuelta', 'solicitud_id'},
    'users': {'licencia_vencimiento', 'licencia_categoria', 'emo_vencimiento', 'pase_minero_vencimiento', 'firma_url'},
    'vehiculos': {'soat_vencimiento', 'rt_vencimiento', 'tarjeta_propiedad_url', 'poliza_vencimiento', 'pase_minero_vencimiento'},
    'mantenimientos': {'informe_url', 'firma_admin_url', 'foto_cierre_url', 'aprobado_por_id', 'alcance', 'fotos_cierre'},
}


def main():
    engine = create_engine(URL)
    esquema = MetaData()
    for nombre, tabla in Base.metadata.tables.items():
        if nombre not in NUEVAS_TABLAS:
            copia = tabla.to_metadata(esquema)
            for campo in COLUMNAS.get(nombre, set()):
                columna = copia.c.get(campo)
                if columna is not None:
                    for constraint in list(copia.constraints):
                        if hasattr(constraint, 'columns') and campo in constraint.columns:
                            copia.constraints.discard(constraint)
                    for indice in list(copia.indexes):
                        if campo in indice.columns:
                            copia.indexes.remove(indice)
                    for fk in list(columna.foreign_keys):
                        copia.foreign_key_constraints.discard(fk.constraint)
                        copia.constraints.discard(fk.constraint)
                    copia._columns.remove(columna)
    esquema.create_all(engine)
    for archivo in ['006_mejoras_v2.sql', '007_mejoras_v3_decisiones.sql', '007_mejoras_v3_decisiones.sql']:
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
            connection.execute(text((Path(__file__).parent / 'migrations' / archivo).read_text(encoding='utf-8')))
    inspector = inspect(engine)
    for nombre, tabla in Base.metadata.tables.items():
        reales = {c['name'] for c in inspector.get_columns(nombre)}
        faltantes = set(tabla.columns.keys()) - reales
        # User.role tiene nombre físico rol.
        if faltantes:
            raise AssertionError(f'{nombre}: columnas faltantes {faltantes}')
    print('PostgreSQL: migraciones 006 + 007 + 007 aplicadas; esquema ORM completo y ejecución idempotente.')


if __name__ == '__main__':
    main()
