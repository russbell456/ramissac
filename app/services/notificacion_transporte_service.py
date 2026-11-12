import logging
import os
from datetime import datetime

from app.models.notificacion_transporte import NotificacionTransporte, DispositivoPush

log = logging.getLogger(__name__)


def notificar(db, usuario_id, clave, titulo, mensaje, *, persistente=False, entidad=None, entidad_id=None):
    clave = f'{usuario_id}:{clave}'
    item = db.query(NotificacionTransporte).filter_by(clave=clave).first()
    if item:
        item.activa = True
        return item
    item = NotificacionTransporte(usuario_id=usuario_id, clave=clave, titulo=titulo,
        mensaje=mensaje, persistente=persistente, entidad=entidad, entidad_id=entidad_id)
    db.add(item)
    db.flush()
    return item


def enviar_push_pendientes(db):
    # Las credenciales se obtienen exclusivamente de GOOGLE_APPLICATION_CREDENTIALS.
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        return
    try:
        import firebase_admin
        from firebase_admin import messaging
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        for aviso in db.query(NotificacionTransporte).filter_by(push_enviado=False, activa=True).all():
            dispositivos = db.query(DispositivoPush).filter_by(usuario_id=aviso.usuario_id).all()
            if not dispositivos:
                continue
            enviado = True
            for dispositivo in dispositivos:
                try:
                    messaging.send(messaging.Message(token=dispositivo.token,
                        notification=messaging.Notification(title=aviso.titulo, body=aviso.mensaje),
                        data={'notificacion_id': str(aviso.id), 'entidad': aviso.entidad or '',
                              'entidad_id': str(aviso.entidad_id or '')}))
                except messaging.UnregisteredError:
                    db.delete(dispositivo)
                except Exception:
                    enviado = False
                    log.exception('No se pudo enviar notificación %s', aviso.id)
            aviso.push_enviado = enviado
        db.commit()
    except Exception:
        log.exception('Error de configuración o envío FCM; se reintentará')


def resolver_avisos(db, entidad, entidad_id):
    for aviso in db.query(NotificacionTransporte).filter_by(entidad=entidad, entidad_id=entidad_id, persistente=True).all():
        aviso.activa = False
