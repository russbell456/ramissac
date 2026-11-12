from datetime import datetime
from fastapi import HTTPException
from app.models.documento_transporte import DocumentoTransporte
from app.models.auditoria_sistema import AuditoriaSistema
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.utils.vehiculo_report import estado_vigencia
from app.utils.transport_time import local_time

CATALOGO = {
    'vehiculo': {'soat': 'soat_vencimiento', 'revision_tecnica': 'rt_vencimiento',
        'tarjeta_propiedad': 'tarjeta_propiedad_url', 'seguro_sctr': 'poliza_vencimiento', 'pase_minero': 'pase_minero_vencimiento'},
    'conductor': {'licencia': 'licencia_vencimiento', 'dni': None, 'emo': 'emo_vencimiento', 'pase_minero': 'pase_minero_vencimiento'},
}


class DocumentoTransporteService:
    def __init__(self, db):
        self.db = db

    def titular(self, entidad, entidad_id):
        if entidad not in CATALOGO:
            raise HTTPException(400, 'Entidad documental inválida.')
        modelo = Vehiculo if entidad == 'vehiculo' else User
        item = self.db.query(modelo).filter(modelo.id == entidad_id).with_for_update().first()
        if not item or (entidad == 'conductor' and item.role != 'conductor'):
            raise HTTPException(404, 'Titular no encontrado.')
        return item

    def listar(self, entidad, entidad_id, historial=False):
        self.titular(entidad, entidad_id)
        consulta = self.db.query(DocumentoTransporte).filter_by(entidad=entidad, entidad_id=entidad_id)
        if not historial:
            consulta = consulta.filter_by(archivado=False)
        return consulta.order_by(DocumentoTransporte.id.desc()).all()

    def renovar(self, entidad, entidad_id, data, admin):
        titular = self.titular(entidad, entidad_id)
        if data.tipo not in CATALOGO[entidad]:
            raise HTTPException(400, 'Tipo de documento no incluido en el catálogo.')
        if data.tipo != 'tarjeta_propiedad' and data.fecha_vencimiento is None:
            raise HTTPException(400, 'Indique la fecha de vencimiento.')
        anteriores = self.db.query(DocumentoTransporte).filter_by(
            entidad=entidad, entidad_id=entidad_id, tipo=data.tipo, archivado=False).all()
        version = 1
        for anterior in anteriores:
            anterior.archivado = True
            version = max(version, anterior.version + 1)
        item = DocumentoTransporte(entidad=entidad, entidad_id=entidad_id, tipo=data.tipo,
            archivo_url=data.archivo_url, fecha_vencimiento=data.fecha_vencimiento,
            estado='aprobado', aprobado_por_id=admin.id, fecha_aprobacion=datetime.utcnow(), version=version)
        self.db.add(item)
        campo = CATALOGO[entidad][data.tipo]
        if campo:
            setattr(titular, campo, data.archivo_url if data.tipo == 'tarjeta_propiedad' else data.fecha_vencimiento)
        if entidad == 'conductor' and data.tipo == 'licencia' and data.licencia_categoria:
            titular.licencia_categoria = data.licencia_categoria
        self.db.flush()
        self.db.add(AuditoriaSistema(usuario_id=admin.id, entidad='documento_transporte',
            registro_id=item.id, accion='renovacion_documental',
            valores_anteriores={'versiones': [d.id for d in anteriores]},
            valores_nuevos={'tipo': item.tipo, 'version': version, 'archivo_url': item.archivo_url},
            motivo='Documento aprobado por administrador.'))
        self.db.commit()
        return item

    def vigencias(self, entidad, entidad_id):
        titular = self.titular(entidad, entidad_id)
        # La lista viene descendente: conservar la solicitud más reciente.
        actuales = {}
        for documento in self.listar(entidad, entidad_id):
            actuales.setdefault(documento.tipo, documento)
        resultado = []
        for tipo, campo in CATALOGO[entidad].items():
            documento = actuales.get(tipo)
            fecha = documento.fecha_vencimiento if documento else (getattr(titular, campo) if campo and tipo != 'tarjeta_propiedad' else None)
            estado = estado_vigencia(fecha, local_time(datetime.utcnow()).date())
            if tipo == 'tarjeta_propiedad':
                estado = 'verde' if documento or titular.tarjeta_propiedad_url else 'pendiente'
            auditoria = self.db.query(AuditoriaSistema).filter_by(entidad='documento_transporte',
                registro_id=documento.id).order_by(AuditoriaSistema.id.desc()).all() if documento else []
            carga = next((a for a in auditoria if a.accion == 'carga_documental'), None)
            rechazo = next((a for a in auditoria if a.accion == 'documento_rechazado'), None)
            resultado.append({'tipo': tipo, 'fecha_vencimiento': fecha, 'estado': estado,
                'semaforo': estado, 'dias_restantes': (fecha-local_time(datetime.utcnow()).date()).days if fecha else None,
                'estado_documento': documento.estado if documento else 'pendiente',
                'archivo_url': documento.archivo_url if documento else None,
                'licencia_categoria': ((carga.valores_nuevos or {}).get('licencia_categoria') if carga else getattr(titular, 'licencia_categoria', None)) if tipo == 'licencia' else None,
                'motivo_rechazo': rechazo.motivo if rechazo and documento.estado == 'rechazado' else None,
                'documento_id': documento.id if documento else None})
        return resultado

    def cargar(self, entidad, entidad_id, data, usuario, solicitud_id):
        titular = self.titular(entidad, entidad_id)
        if data.tipo not in CATALOGO[entidad]:
            raise HTTPException(400, 'Tipo de documento inválido.')
        if data.tipo != 'tarjeta_propiedad' and not data.fecha_vencimiento:
            raise HTTPException(400, 'Indique el vencimiento.')
        previas = self.db.query(AuditoriaSistema).filter_by(usuario_id=usuario.id,
            entidad='documento_transporte', accion='carga_documental').all()
        for previa in previas:
            if (previa.valores_nuevos or {}).get('solicitud_id') == solicitud_id:
                item = self.db.query(DocumentoTransporte).filter_by(id=previa.registro_id).first()
                if item and item.entidad == entidad and item.entidad_id == entidad_id:
                    return item
                raise HTTPException(409, 'Identificador ya utilizado.')
        documentos = self.db.query(DocumentoTransporte).filter_by(entidad=entidad,
            entidad_id=entidad_id, tipo=data.tipo).all()
        for anterior in documentos:
            if anterior.estado != 'aprobado':
                anterior.archivado = True
        item = DocumentoTransporte(entidad=entidad, entidad_id=entidad_id, tipo=data.tipo,
            archivo_url=data.archivo_url, fecha_vencimiento=data.fecha_vencimiento, estado='pendiente',
            version=max([d.version for d in documentos] or [0])+1)
        self.db.add(item)
        self.db.flush()
        self.db.add(AuditoriaSistema(usuario_id=usuario.id, entidad='documento_transporte', registro_id=item.id,
            accion='carga_documental', valores_nuevos={'solicitud_id': solicitud_id,
                'licencia_categoria': data.licencia_categoria}, motivo='Solicitud de revisión documental.'))
        self.db.commit()
        if usuario.role == 'admin':
            return self.revisar(item.id, 'aprobado', '', usuario)
        return item

    def revisar(self, documento_id, estado, motivo, administrador):
        item = self.db.query(DocumentoTransporte).filter_by(id=documento_id).first()
        if not item:
            raise HTTPException(404, 'Documento no encontrado.')
        titular = self.titular(item.entidad, item.entidad_id)
        self.db.refresh(item)
        if item.archivado or item.estado != 'pendiente':
            raise HTTPException(409, 'Solo puede revisar la solicitud pendiente más reciente.')
        if estado == 'rechazado' and len(motivo.strip()) < 10:
            raise HTTPException(400, 'Indique el motivo del rechazo (mínimo 10 caracteres).')
        item.estado = estado
        item.aprobado_por_id = administrador.id
        item.fecha_aprobacion = datetime.utcnow()
        if estado == 'aprobado':
            for anterior in self.db.query(DocumentoTransporte).filter_by(entidad=item.entidad,
                entidad_id=item.entidad_id, tipo=item.tipo, archivado=False).all():
                if anterior.id != item.id:
                    anterior.archivado = True
            campo = CATALOGO[item.entidad][item.tipo]
            if campo:
                setattr(titular, campo, item.archivo_url if item.tipo == 'tarjeta_propiedad' else item.fecha_vencimiento)
            carga = self.db.query(AuditoriaSistema).filter_by(entidad='documento_transporte', registro_id=item.id,
                accion='carga_documental').first()
            if item.tipo == 'licencia' and carga and (carga.valores_nuevos or {}).get('licencia_categoria'):
                titular.licencia_categoria = carga.valores_nuevos['licencia_categoria']
        self.db.add(AuditoriaSistema(usuario_id=administrador.id, entidad='documento_transporte',
            registro_id=item.id, accion='documento_' + estado, valores_nuevos={'estado': estado}, motivo=motivo.strip()))
        self.db.commit()
        return item
