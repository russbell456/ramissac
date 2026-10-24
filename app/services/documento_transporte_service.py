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
        actuales = {d.tipo: d for d in self.listar(entidad, entidad_id)}
        resultado = []
        for tipo, campo in CATALOGO[entidad].items():
            documento = actuales.get(tipo)
            fecha = documento.fecha_vencimiento if documento else (getattr(titular, campo) if campo and tipo != 'tarjeta_propiedad' else None)
            estado = estado_vigencia(fecha, local_time(datetime.utcnow()).date())
            if tipo == 'tarjeta_propiedad':
                estado = 'verde' if documento or titular.tarjeta_propiedad_url else 'pendiente'
            resultado.append({'tipo': tipo, 'fecha_vencimiento': fecha, 'estado': estado,
                'documento_id': documento.id if documento else None})
        return resultado
