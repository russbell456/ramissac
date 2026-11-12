import pytest
from app.services.auditoria_service import AuditoriaService
from app.models.almacen_auditoria import AlmacenAuditoria

def test_registrar_auditoria_exitoso(db_session):
    service = AuditoriaService(db_session)
    
    # Registrar un evento de auditoría
    service.registrar(
        usuario_id=123,
        accion="PRUEBA_ACCION",
        entidad="PRUEBA_ENTIDAD",
        entidad_id=456,
        descripcion="Descripción de prueba de auditoría"
    )

    # Verificar que el registro se guardó en la base de datos
    registro = db_session.query(AlmacenAuditoria).filter(
        AlmacenAuditoria.usuario_id == 123,
        AlmacenAuditoria.accion == "PRUEBA_ACCION"
    ).first()

    assert registro is not None
    assert registro.entidad == "PRUEBA_ENTIDAD"
    assert registro.entidad_id == 456
    assert registro.descripcion == "Descripción de prueba de auditoría"
    assert registro.fecha is not None
