import pytest
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.almacen_auditoria import AlmacenAuditoria


def test_actualizar_usuario_exitoso(db_session):
    # Arrange: Crear usuario inicial
    usuario = User(
        id=50,
        nombre="José",
        apellidos="García",
        dni="88888888",
        cargo="Operario",
        email="jose.garcia@test.com",
        password="hashed_pwd",
        role="trabajador"
    )
    db_session.add(usuario)
    db_session.commit()

    service = AuthService(db_session)

    # Act: Actualizar los campos del usuario
    updated_user = service.actualizar_usuario(
        user_id=50,
        nombre="José María",
        apellidos="García Pérez",
        dni="88888889",
        cargo="Supervisor",
        email="jose.garcia.nuevo@test.com",
        usuario_auditoria=999
    )

    # Assert: Verificar cambios en BD
    assert updated_user.nombre == "José María"
    assert updated_user.apellidos == "García Pérez"
    assert updated_user.dni == "88888889"
    assert updated_user.cargo == "Supervisor"
    assert updated_user.email == "jose.garcia.nuevo@test.com"

    # Verificar que se registró la auditoría
    audit = db_session.query(AlmacenAuditoria).filter(
        AlmacenAuditoria.usuario_id == 999,
        AlmacenAuditoria.accion == "EDITAR_USUARIO",
        AlmacenAuditoria.entidad == "users",
        AlmacenAuditoria.entidad_id == 50
    ).first()
    assert audit is not None
    assert "jose.garcia.nuevo@test.com" in audit.descripcion


def test_actualizar_usuario_inexistente(db_session):
    service = AuthService(db_session)
    
    with pytest.raises(ValueError, match="Usuario no encontrado"):
        service.actualizar_usuario(
            user_id=9999,  # No existe
            nombre="José",
            apellidos="García",
            dni="88888888",
            cargo="Operario",
            email="jose@test.com",
            usuario_auditoria=999
        )
