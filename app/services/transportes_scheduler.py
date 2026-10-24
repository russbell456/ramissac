import asyncio
import logging
from datetime import datetime
from sqlalchemy import text

from app.database.connection import SessionLocal, engine
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.models.jornada_transporte import JornadaTransporte
from app.models.mantenimiento import Mantenimiento
from app.models.notificacion_transporte import NotificacionTransporte
from app.services.documento_transporte_service import DocumentoTransporteService
from app.services.jornada_transporte_service import JornadaTransporteService
from app.services.notificacion_transporte_service import notificar, enviar_push_pendientes
from app.utils.transport_time import local_time

log = logging.getLogger(__name__)


def ejecutar_ciclo(db, ahora=None):
    ahora = ahora or datetime.utcnow()
    local = local_time(ahora)
    admins = db.query(User).filter_by(role='admin').all()
    # Reconciliar avisos de condición activa en cada ciclo.
    for aviso in db.query(NotificacionTransporte).filter_by(persistente=True, activa=True).all():
        aviso.activa = False
    jornadas = db.query(JornadaTransporte).filter(
        JornadaTransporte.jornada_padre_id.is_(None),
        JornadaTransporte.estado.in_(['en_curso', 'pendiente_de_cierre', 'cerrada_por_sistema']),
    ).all()
    for jornada in jornadas:
        if jornada.estado != 'en_curso':
            for usuario_id in [jornada.conductor_id] + [a.id for a in admins]:
                notificar(db, usuario_id, f'pendiente:{jornada.id}', 'Odómetro pendiente',
                    'Regularice el cierre de la jornada.', persistente=True, entidad='jornada', entidad_id=jornada.id)
        if jornada.estado in {'en_curso', 'pendiente_de_cierre'} and local_time(jornada.fecha_inicio).date() <= local.date():
            for hora in (19, 21):
                if local.hour >= hora:
                    for usuario_id in [jornada.conductor_id] + [a.id for a in admins]:
                        notificar(db, usuario_id, f'nocturna:{jornada.id}:{local.date()}:{hora}',
                            'Recuerde cerrar su jornada', f'La jornada sigue abierta a las {hora}:00.',
                            entidad='jornada', entidad_id=jornada.id)
    documentos = DocumentoTransporteService(db)
    for entidad, titulares in [('vehiculo', db.query(Vehiculo).filter(Vehiculo.estado != 'inactivo').all()),
                              ('conductor', db.query(User).filter_by(role='conductor').all())]:
        for titular in titulares:
            for doc in documentos.vigencias(entidad, titular.id):
                if doc['estado'] != 'verde':
                    for admin in admins:
                        notificar(db, admin.id, f'doc:{entidad}:{titular.id}:{doc["tipo"]}:{doc["estado"]}',
                            'Documentación por completar o renovar',
                            f'{entidad} {titular.id}: {doc["tipo"]} — {doc["estado"]}',
                            persistente=True, entidad='documento', entidad_id=titular.id)
    for vehiculo in db.query(Vehiculo).filter(Vehiculo.estado != 'inactivo').all():
        if vehiculo.estado_semaforo == 'rojo':
            for admin in admins:
                notificar(db, admin.id, f'rojo:{vehiculo.id}', 'Unidad inoperativa',
                    f'{vehiculo.placa} requiere revisión mecánica.', persistente=True, entidad='vehiculo', entidad_id=vehiculo.id)
        ultimo = db.query(Mantenimiento).filter(
            Mantenimiento.vehiculo_id == vehiculo.id,
            Mantenimiento.proximo_kilometraje_mantenimiento.isnot(None),
            Mantenimiento.estado != 'inactivo',
        ).order_by(Mantenimiento.id.desc()).first()
        if ultimo:
            restantes = ultimo.proximo_kilometraje_mantenimiento - vehiculo.kilometraje_actual
            if restantes <= 500:
                for admin in admins:
                    notificar(db, admin.id, f'mantenimiento:{ultimo.id}:{"rojo" if restantes <= 0 else "amarillo"}',
                        'Mantenimiento vencido' if restantes <= 0 else 'Mantenimiento próximo',
                        f'{vehiculo.placa}: {max(0, restantes):.0f} km restantes.',
                        persistente=True, entidad='mantenimiento', entidad_id=ultimo.id)
    JornadaTransporteService(db).cerrar_jornadas_vencidas(ahora)
    db.commit()
    enviar_push_pendientes(db)


def tick():
    # Conexión dedicada: los commit del servicio no devuelven la conexión que
    # posee el lock al pool ni permiten desbloquear accidentalmente otra sesión.
    with engine.connect() as lock:
        postgres = engine.dialect.name == 'postgresql'
        if postgres and not lock.execute(text('SELECT pg_try_advisory_lock(740007)')).scalar():
            return
        try:
            with SessionLocal() as db:
                try:
                    ejecutar_ciclo(db)
                except Exception:
                    db.rollback()
                    log.exception('Falló el ciclo de transportes')
        finally:
            if postgres:
                lock.execute(text('SELECT pg_advisory_unlock(740007)'))


async def ejecutar_scheduler():
    while True:
        await asyncio.to_thread(tick)
        await asyncio.sleep(30)
