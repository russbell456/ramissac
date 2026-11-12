from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.models.jornada_transporte import JornadaTransporte, IncidenciaRuta
from app.models.auditoria_sistema import AuditoriaSistema
from app.models.averia import Averia
from app.models.mantenimiento import Mantenimiento
from app.models.notificacion_transporte import NotificacionTransporte, DispositivoPush
from app.schemas.transportes_v3_schema import (
    DocumentoCrear, DocumentoResponse, DispositivoCrear, FirmaActualizar,
    ResolverObservacion, ConductorRapido, ConductorAcceso, DocumentoRevision,
)
from app.schemas.jornada_transporte_schema import KilometrajeCorregir
from app.schemas.vehiculo_schema import VehiculoCreate
from app.services.documento_transporte_service import DocumentoTransporteService
from app.services.jornada_transporte_service import JornadaTransporteService
from app.utils.transport_time import utc_naive

router = APIRouter(prefix='/api/transportes', tags=['Transportes V3'])
Db = Annotated[Session, Depends(get_db)]
Usuario = Annotated[User, Depends(get_current_user)]


def admin(usuario: Usuario):
    if usuario.role != 'admin':
        raise HTTPException(403, 'Acción exclusiva del administrador.')
    return usuario


Admin = Annotated[User, Depends(admin)]


def lector(usuario, entidad=None, entidad_id=None):
    if usuario.role == 'admin':
        return
    if usuario.role != 'conductor' or (entidad == 'conductor' and entidad_id != usuario.id):
        raise HTTPException(403, 'No autorizado.')


@router.get('/documentos/{entidad}/{entidad_id}', response_model=list[DocumentoResponse])
def documentos(entidad: str, entidad_id: int, db: Db, usuario: Usuario, historial: bool = False):
    lector(usuario, entidad, entidad_id)
    return DocumentoTransporteService(db).listar(entidad, entidad_id, historial)


@router.get('/documentos/{entidad}/{entidad_id}/vigencias')
def vigencias(entidad: str, entidad_id: int, db: Db, usuario: Usuario):
    lector(usuario, entidad, entidad_id)
    return DocumentoTransporteService(db).vigencias(entidad, entidad_id)


@router.post('/documentos/{documento_id}/revisar', response_model=DocumentoResponse)
def revisar_documento(documento_id: int, data: DocumentoRevision, db: Db, usuario: Admin):
    return DocumentoTransporteService(db).revisar(documento_id, data.estado, data.motivo, usuario)


@router.post('/documentos/{entidad}/{entidad_id}', response_model=DocumentoResponse, status_code=201,
    openapi_extra={'requestBody': {'content': {'multipart/form-data': {'schema': {
        'type': 'object', 'required': ['tipo', 'file', 'solicitud_id'], 'properties': {
            'tipo': {'type': 'string'}, 'fecha_vencimiento': {'type': 'string', 'format': 'date'},
            'licencia_categoria': {'type': 'string'}, 'solicitud_id': {'type': 'string'},
            'file': {'type': 'string', 'format': 'binary'}}}},
        'application/json': {'schema': DocumentoCrear.model_json_schema()}}}})
async def renovar(entidad: str, entidad_id: int, request: Request, db: Db, usuario: Usuario):
    lector(usuario, entidad, entidad_id)
    service = DocumentoTransporteService(db)
    service.titular(entidad, entidad_id)
    if request.headers.get('content-type', '').startswith('application/json'):
        if usuario.role != 'admin':
            raise HTTPException(403, 'El conductor debe adjuntar el archivo para revisión.')
        try:
            data = DocumentoCrear.model_validate(await request.json())
        except (ValidationError, ValueError) as error:
            raise HTTPException(422, str(error))
        return service.renovar(entidad, entidad_id, data, usuario)
    form = await request.form()
    archivo = form.get('file')
    solicitud_id = str(form.get('solicitud_id', '')).strip()
    if not archivo or not hasattr(archivo, 'read') or not 16 <= len(solicitud_id) <= 80:
        raise HTTPException(422, 'Adjunte un archivo e identificador de solicitud válido.')
    contenido = await archivo.read(10 * 1024 * 1024 + 1)
    if not contenido or len(contenido) > 10 * 1024 * 1024:
        raise HTTPException(413, 'El archivo debe tener contenido y no superar 10 MB.')
    if contenido.startswith(b'%PDF-') and b'%%EOF' in contenido[-2048:]:
        extension = 'pdf'
    else:
        from io import BytesIO
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(BytesIO(contenido)) as imagen:
                extension = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}.get(imagen.format)
                if not extension or imagen.width * imagen.height > 25000000:
                    raise HTTPException(400, 'Use una imagen JPG, PNG o WEBP válida.')
                imagen.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(400, 'Adjunte una imagen o PDF válido.')
    carpeta = Path('uploads/transportes')
    nombre = uuid4().hex + '.' + extension
    try:
        data = DocumentoCrear(tipo=str(form.get('tipo', '')), archivo_url='/uploads/transportes/' + nombre,
            fecha_vencimiento=form.get('fecha_vencimiento') or None,
            licencia_categoria=form.get('licencia_categoria') or None)
    except ValidationError as error:
        raise HTTPException(422, str(error))
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    destino.write_bytes(contenido)
    try:
        documento = service.cargar(entidad, entidad_id, data, usuario, solicitud_id)
        if documento.archivo_url != data.archivo_url:
            destino.unlink(missing_ok=True)
        return documento
    except Exception:
        destino.unlink(missing_ok=True)
        raise


@router.get('/notificaciones')
def notificaciones(db: Db, usuario: Usuario):
    lector(usuario)
    items = db.query(NotificacionTransporte).filter_by(usuario_id=usuario.id, activa=True).order_by(NotificacionTransporte.id.desc()).all()
    return [{'id': n.id, 'titulo': n.titulo, 'mensaje': n.mensaje, 'persistente': n.persistente,
        'leida': n.leida, 'fecha': n.fecha, 'entidad': n.entidad, 'entidad_id': n.entidad_id}
        for n in items if n.persistente or not n.leida]


@router.post('/notificaciones/{id}/leer')
def leer(id: int, db: Db, usuario: Usuario):
    item = db.query(NotificacionTransporte).filter_by(id=id, usuario_id=usuario.id).first()
    if not item:
        raise HTTPException(404, 'Notificación no encontrada.')
    item.leida = True
    db.commit()
    return {'id': id, 'persistente': item.persistente}


@router.post('/dispositivos')
def dispositivo(data: DispositivoCrear, db: Db, usuario: Usuario):
    lector(usuario)
    item = db.query(DispositivoPush).filter_by(token=data.token).first()
    if item:
        item.usuario_id = usuario.id
    else:
        db.add(DispositivoPush(usuario_id=usuario.id, token=data.token))
    db.commit()
    return {'registrado': True}


@router.delete('/dispositivos')
def quitar_dispositivo(data: DispositivoCrear, db: Db, usuario: Usuario):
    item = db.query(DispositivoPush).filter_by(token=data.token, usuario_id=usuario.id).first()
    if item:
        db.delete(item)
        db.commit()
    return {'registrado': False}


@router.put('/firma')
def firma(data: FirmaActualizar, db: Db, usuario: Admin):
    usuario.firma_url = data.firma_url
    db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='usuario', registro_id=usuario.id,
        accion='actualizacion_firma', valores_nuevos={'firma_url': data.firma_url}))
    db.commit()
    return {'firma_url': usuario.firma_url}


@router.post('/archivos', status_code=201)
async def archivo(usuario: Admin, file: UploadFile = File(...)):
    contenido = await file.read(10 * 1024 * 1024 + 1)
    if len(contenido) > 10 * 1024 * 1024:
        raise HTTPException(413, 'El archivo no puede superar 10 MB.')
    if not contenido.startswith(b'%PDF-') or b'%%EOF' not in contenido[-2048:]:
        raise HTTPException(400, 'Adjunte un informe PDF válido.')
    carpeta = Path('uploads/transportes')
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = uuid4().hex + '.pdf'
    (carpeta / nombre).write_bytes(contenido)
    return {'url': '/uploads/transportes/' + nombre}


@router.get('/resumen-diario/{conductor_id}')
def resumen(conductor_id: int, fecha: date, db: Db, usuario: Usuario):
    lector(usuario, 'conductor', conductor_id)
    resultado = JornadaTransporteService(db).consolidar_horas(conductor_id, fecha)
    db.rollback()  # Consulta: no persiste nuevos cálculos.
    return resultado


@router.get('/inactivos')
def inactivos(db: Db, usuario: Admin):
    return [{'id': v.id, 'placa': v.placa, 'estado': v.estado, 'fecha_baja': v.fecha_baja}
        for v in db.query(Vehiculo).filter_by(estado='inactivo').all()]


@router.get('/auditoria')
def auditoria(db: Db, usuario: Admin, entidad: str | None = None, registro_id: int | None = None, limite: int = 100):
    consulta = db.query(AuditoriaSistema)
    if entidad:
        consulta = consulta.filter_by(entidad=entidad)
    if registro_id is not None:
        consulta = consulta.filter_by(registro_id=registro_id)
    return consulta.order_by(AuditoriaSistema.id.desc()).limit(max(1, min(limite, 500))).all()


@router.post('/jornadas/{id}/corregir-kilometraje')
def corregir(id: int, data: KilometrajeCorregir, db: Db, usuario: Admin):
    jornada = db.query(JornadaTransporte).filter_by(id=id).with_for_update().first()
    if not jornada or not jornada.fecha_fin:
        raise HTTPException(404, 'Jornada cerrada no encontrada.')
    from datetime import timedelta
    if datetime.utcnow() - utc_naive(jornada.fecha_fin) > timedelta(hours=72):
        raise HTTPException(409, 'El plazo de 72 horas venció.')
    if data.kilometraje < (jornada.km_inicial or 0):
        raise HTTPException(400, 'El kilometraje final no puede ser menor al inicial.')
    anterior = jornada.km_final
    jornada.km_final = data.kilometraje
    vehiculo = db.query(Vehiculo).filter_by(id=jornada.vehiculo_id).with_for_update().first()
    posterior = db.query(JornadaTransporte).filter(JornadaTransporte.vehiculo_id == vehiculo.id,
        JornadaTransporte.id != id, JornadaTransporte.fecha_inicio > jornada.fecha_fin).first()
    if not posterior:
        vehiculo.kilometraje_actual = data.kilometraje
    db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='jornada_transporte', registro_id=id,
        accion='correccion_kilometraje', valores_anteriores={'km_final': anterior},
        valores_nuevos={'km_final': data.kilometraje}, motivo=data.motivo))
    db.commit()
    return {'id': id, 'km_final': jornada.km_final}


@router.post('/observaciones/{origen}/{id}/resolver')
def resolver(origen: str, id: int, data: ResolverObservacion, db: Db, usuario: Admin):
    if origen not in {'jornada', 'incidencia'}:
        raise HTTPException(400, 'Origen inválido.')
    modelo = JornadaTransporte if origen == 'jornada' else IncidenciaRuta
    item = db.query(modelo).filter_by(id=id).first()
    if not item:
        raise HTTPException(404, 'Observación no encontrada.')
    vehiculo_id = item.vehiculo_id if origen == 'jornada' else item.jornada.vehiculo_id
    if origen == 'jornada':
        item.observacion_resuelta = True
        padre = item if item.jornada_padre_id is None else db.query(JornadaTransporte).filter_by(id=item.jornada_padre_id).first()
    else:
        item.resuelta = True
        padre = item.jornada
    descripcion_original = item.observaciones if origen == 'jornada' else item.descripcion
    if padre and padre.observaciones == descripcion_original and padre.severidad == item.severidad:
        padre.observacion_resuelta = True
    db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='observacion', registro_id=id,
        accion='resolucion', valores_nuevos={'origen': origen, 'foto': data.foto_url}, motivo=data.descripcion))
    db.flush()
    for averia in db.query(Averia).filter(Averia.vehiculo_id == vehiculo_id,
        Averia.descripcion == descripcion_original,
        Averia.estado.in_(['reportada', 'en_evaluacion', 'programada', 'en_reparacion'])).all():
        anterior = averia.estado
        averia.estado = 'resuelta'
        db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='averia', registro_id=averia.id,
            accion='reparacion_aprobada', valores_anteriores={'estado': anterior},
            valores_nuevos={'estado': 'resuelta'}, motivo=data.descripcion))
    db.flush()
    pendientes = db.query(JornadaTransporte).filter_by(vehiculo_id=vehiculo_id, observacion_resuelta=False).all()
    incidencias = db.query(IncidenciaRuta).join(JornadaTransporte).filter(
        JornadaTransporte.vehiculo_id == vehiculo_id, IncidenciaRuta.resuelta.is_(False)).all()
    orden = {'leve': 0, 'moderada': 1, 'critica': 2}
    nivel = max([orden.get(x.severidad, 0) for x in pendientes + incidencias] or [0])
    if db.query(Averia).filter(Averia.vehiculo_id == vehiculo_id, Averia.criticidad == 'critica',
        Averia.estado.in_(['reportada', 'en_evaluacion', 'programada', 'en_reparacion'])).first():
        nivel = 2
    vehiculo = db.query(Vehiculo).filter_by(id=vehiculo_id).first()
    vehiculo.estado_semaforo = ['verde', 'amarillo', 'rojo'][nivel]
    en_taller = db.query(Mantenimiento).filter_by(vehiculo_id=vehiculo_id, estado='en_taller').first()
    if nivel < 2 and not en_taller and vehiculo.estado == 'en_mantenimiento':
        en_ruta = db.query(JornadaTransporte).filter_by(vehiculo_id=vehiculo_id, estado='en_curso', jornada_padre_id=None).first()
        vehiculo.estado = 'en_ruta' if en_ruta else 'disponible'
    db.commit()
    return {'resuelta': True, 'estado_semaforo': vehiculo.estado_semaforo}


@router.get('/observaciones')
def observaciones(db: Db, usuario: Usuario, vehiculo_id: int):
    lector(usuario)
    jornadas = db.query(JornadaTransporte).filter_by(vehiculo_id=vehiculo_id, tiene_observaciones=True).all()
    incidencias = db.query(IncidenciaRuta).join(JornadaTransporte).filter(JornadaTransporte.vehiculo_id == vehiculo_id,
        IncidenciaRuta.severidad.isnot(None)).all()
    return [dict(origen='jornada', id=j.id, descripcion=j.observaciones, severidad=j.severidad,
        resuelta=j.observacion_resuelta, fotos=j.fotos_observacion or ([j.foto_observacion] if j.foto_observacion else [])) for j in jornadas] + [
        dict(origen='incidencia', id=i.id, descripcion=i.descripcion, severidad=i.severidad,
            resuelta=i.resuelta, fotos=i.fotos or ([i.foto_incidencia] if i.foto_incidencia else [])) for i in incidencias]


@router.post('/conductores/alta-rapida', status_code=201)
def alta_conductor(data: ConductorRapido, db: Db, usuario: Admin):
    if db.query(User).filter_by(dni=data.dni).first():
        raise HTTPException(409, 'El DNI ya está registrado.')
    from app.security.hashing import Hash
    item = User(nombre=data.nombre, apellidos=data.apellidos, dni=data.dni,
        email=f'{data.dni}@pendiente.ramis.com', password=Hash.get_password_hash(uuid4().hex), role='conductor')
    db.add(item)
    db.flush()
    db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='usuario', registro_id=item.id,
        accion='alta_rapida', motivo='Documentación y acceso pendientes de completar.'))
    db.commit()
    return {'id': item.id, 'nombre': item.nombre, 'dni': item.dni, 'documentacion': 'pendiente'}


@router.put('/conductores/{id}/acceso')
def configurar_acceso(id: int, data: ConductorAcceso, db: Db, usuario: Admin):
    item = db.query(User).filter_by(id=id, role='conductor').first()
    if not item:
        raise HTTPException(404, 'Conductor no encontrado.')
    if db.query(User).filter(User.email == data.email, User.id != id).first():
        raise HTTPException(409, 'El correo ya está registrado.')
    from app.core.security import hash_password
    anterior = item.email
    item.email = data.email
    item.password = hash_password(data.password)
    db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='usuario', registro_id=id,
        accion='configuracion_acceso', valores_anteriores={'email': anterior}, valores_nuevos={'email': item.email}))
    db.commit()
    return {'id': id, 'email': item.email}


@router.get('/conductores')
def conductores(db: Db, usuario: Admin):
    service = DocumentoTransporteService(db)
    return [{'id': c.id, 'nombre': c.nombre, 'apellidos': c.apellidos, 'dni': c.dni, 'email': c.email,
        'documentos': service.vigencias('conductor', c.id)} for c in db.query(User).filter_by(role='conductor').order_by(User.nombre).all()]


@router.get('/vehiculos')
def flota_v3(db: Db, usuario: Usuario):
    lector(usuario)
    from app.schemas.vehiculo_schema import VehiculoResponse
    return [VehiculoResponse.model_validate(v) for v in db.query(Vehiculo).filter(Vehiculo.estado != 'inactivo').all()]


@router.post('/vehiculos', status_code=201)
def vehiculo_alta(data: VehiculoCreate, db: Db, usuario: Admin):
    from app.services.vehiculo_service import VehiculoService
    from app.schemas.vehiculo_schema import VehiculoResponse
    return VehiculoResponse.model_validate(VehiculoService(db).create_vehiculo(data))


@router.get('/vehiculos/{id}/reporte-pdf')
def vehiculo_pdf(id: int, db: Db, usuario: Usuario, estado: str = 'pendientes', desde: date | None = None, hasta: date | None = None):
    lector(usuario)
    if estado not in {'pendientes', 'todas'}:
        raise HTTPException(422, 'Filtro inválido.')
    from app.routers.vehiculo_router import reporte_pdf
    return reporte_pdf(id, db, usuario, estado, desde, hasta)
