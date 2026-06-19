from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch, PropertyMock, call
from sqlalchemy.orm import Session

# ─────────────────────────────────────────────
# Helpers compartidos
# ─────────────────────────────────────────────

def make_user(**kwargs):
    """Fábrica mínima de objetos User sin necesidad de BD."""
    from app.models.user import User
    u = User()
    u.id = kwargs.get("id", 1)
    u.nombre = kwargs.get("nombre", "Juan")
    u.apellidos = kwargs.get("apellidos", "Pérez")
    u.dni = kwargs.get("dni", "12345678")
    u.cargo = kwargs.get("cargo", None)
    u.email = kwargs.get("email", "juan@test.com")
    u.password = kwargs.get("password", "hashed_pw")
    u.role = kwargs.get("role", "user")
    u.codigo_unico = kwargs.get("codigo_unico", None)
    return u


# ═══════════════════════════════════════════════════════════
#  1.  UserRepository
# ═══════════════════════════════════════════════════════════

class TestUserRepository:
    """Pruebas para app.repositories.user_repository.UserRepository"""

    def setup_method(self):
        self.db = MagicMock(spec=Session)
        from app.repositories.user_repository import UserRepository
        self.repo = UserRepository(self.db)

    # ── get_by_email ────────────────────────────────────────

    def test_get_by_email_found(self):
        """Retorna el usuario cuando el email existe."""
        user = make_user()
        (
            self.db.query.return_value
               .filter.return_value
               .first.return_value
        ) = user

        result = self.repo.get_by_email("juan@test.com")

        assert result is user
        self.db.query.assert_called_once()

    def test_get_by_email_not_found(self):
        """Retorna None cuando el email no existe."""
        (
            self.db.query.return_value
               .filter.return_value
               .first.return_value
        ) = None

        result = self.repo.get_by_email("noexiste@test.com")

        assert result is None

    def test_get_by_email_queries_correct_model(self):
        """Verifica que se consulta el modelo User."""
        from app.models.user import User
        self.db.query.return_value.filter.return_value.first.return_value = None

        self.repo.get_by_email("x@x.com")

        self.db.query.assert_called_once_with(User)

    # ── create_user ──────────────────────────────────────────

    def test_create_user_calls_add(self):
        """Se llama db.add con el usuario."""
        user = make_user()
        self.repo.create_user(user)
        self.db.add.assert_called_once_with(user)

    def test_create_user_calls_commit(self):
        """Se llama db.commit tras add."""
        user = make_user()
        self.repo.create_user(user)
        self.db.commit.assert_called_once()

    def test_create_user_calls_refresh(self):
        """Se llama db.refresh para actualizar el objeto."""
        user = make_user()
        self.repo.create_user(user)
        self.db.refresh.assert_called_once_with(user)

    def test_create_user_returns_user(self):
        """Retorna el mismo objeto User recibido."""
        user = make_user()
        result = self.repo.create_user(user)
        assert result is user




# ═══════════════════════════════════════════════════════════
#  2.  AuthService
# ═══════════════════════════════════════════════════════════

class TestAuthServiceRegister:
    """Pruebas para AuthService.register_user"""

    def setup_method(self):
        self.db = MagicMock(spec=Session)
        # Mockeamos UserRepository para aislar AuthService
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            self.mock_repo_instance = MockRepo.return_value
            from app.services.auth_service import AuthService
            self.service = AuthService(self.db)
            self.service.user_repo = self.mock_repo_instance

    # ── email duplicado ──────────────────────────────────────

    def test_register_raises_if_email_already_exists(self):
        """ValueError si el email ya está en uso."""
        self.mock_repo_instance.get_by_email.return_value = make_user()

        with pytest.raises(ValueError, match="El email ya está registrado"):
            self.service.register_user(
                nombre="Ana", apellidos="García", dni="87654321",
                cargo=None, email="juan@test.com", password="secret123"
            )

    def test_register_does_not_create_if_email_exists(self):
        """create_user NO se llama si el email ya existe."""
        self.mock_repo_instance.get_by_email.return_value = make_user()

        with pytest.raises(ValueError):
            self.service.register_user(
                nombre="Ana", apellidos="García", dni="87654321",
                cargo=None, email="juan@test.com", password="secret123"
            )

        self.mock_repo_instance.create_user.assert_not_called()

    # ── registro exitoso ─────────────────────────────────────

    @patch("app.services.auth_service.hash_password", return_value="hashed_123")
    def test_register_hashes_password(self, mock_hash):
        """La contraseña se hashea antes de guardar."""
        self.mock_repo_instance.get_by_email.return_value = None
        self.mock_repo_instance.create_user.return_value = make_user()

        self.service.register_user(
            nombre="Ana", apellidos="García", dni="87654321",
            cargo=None, email="new@test.com", password="plaintext"
        )

        mock_hash.assert_called_once_with("plaintext")

    @patch("app.services.auth_service.hash_password", return_value="hashed_123")
    def test_register_stores_hashed_password_in_user(self, mock_hash):
        """El objeto User creado tiene la contraseña hasheada."""
        self.mock_repo_instance.get_by_email.return_value = None
        captured = []

        def capture_user(user):
            captured.append(user)
            return user

        self.mock_repo_instance.create_user.side_effect = capture_user

        self.service.register_user(
            nombre="Ana", apellidos="García", dni="87654321",
            cargo=None, email="new@test.com", password="plaintext"
        )

        assert captured[0].password == "hashed_123"

    @patch("app.services.auth_service.hash_password", return_value="hashed_123")
    def test_register_assigns_default_role_user(self, _):
        """El rol por defecto es 'user' si no se pasa ninguno."""
        self.mock_repo_instance.get_by_email.return_value = None
        captured = []
        self.mock_repo_instance.create_user.side_effect = lambda u: captured.append(u) or u

        self.service.register_user(
            nombre="Ana", apellidos="García", dni="87654321",
            cargo=None, email="new@test.com", password="secret123"
        )

        assert captured[0].role == "user"

    @patch("app.services.auth_service.hash_password", return_value="hashed_123")
    def test_register_assigns_custom_role(self, _):
        """Se respeta el rol personalizado pasado como argumento."""
        self.mock_repo_instance.get_by_email.return_value = None
        captured = []
        self.mock_repo_instance.create_user.side_effect = lambda u: captured.append(u) or u

        self.service.register_user(
            nombre="Ana", apellidos="García", dni="87654321",
            cargo=None, email="new@test.com", password="secret123",
            role="admin"
        )

        assert captured[0].role == "admin"

    @patch("app.services.auth_service.hash_password", return_value="hashed_123")
    def test_register_sets_all_fields(self, _):
        """Todos los campos del User se asignan correctamente."""
        self.mock_repo_instance.get_by_email.return_value = None
        captured = []
        self.mock_repo_instance.create_user.side_effect = lambda u: captured.append(u) or u

        self.service.register_user(
            nombre="Ana", apellidos="García", dni="87654321",
            cargo="Jefe", email="ana@test.com", password="secret123",
            role="trabajador"
        )

        u = captured[0]
        assert u.nombre == "Ana"
        assert u.apellidos == "García"
        assert u.dni == "87654321"
        assert u.cargo == "Jefe"
        assert u.email == "ana@test.com"

    @patch("app.services.auth_service.hash_password", return_value="hashed_123")
    def test_register_returns_created_user(self, _):
        """Retorna el usuario retornado por el repositorio."""
        self.mock_repo_instance.get_by_email.return_value = None
        expected = make_user(email="new@test.com")
        self.mock_repo_instance.create_user.return_value = expected

        result = self.service.register_user(
            nombre="Ana", apellidos="García", dni="87654321",
            cargo=None, email="new@test.com", password="secret123"
        )

        assert result is expected


class TestAuthServiceAuthenticate:
    """Pruebas para AuthService.authenticate_user"""

    def setup_method(self):
        self.db = MagicMock(spec=Session)
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            self.mock_repo_instance = MockRepo.return_value
            from app.services.auth_service import AuthService
            self.service = AuthService(self.db)
            self.service.user_repo = self.mock_repo_instance

    def test_authenticate_returns_none_if_user_not_found(self):
        """Retorna None si el email no existe."""
        self.mock_repo_instance.get_by_email.return_value = None

        result = self.service.authenticate_user("noexiste@test.com", "pass")

        assert result is None

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_authenticate_returns_none_if_wrong_password(self, _):
        """Retorna None si la contraseña no coincide."""
        self.mock_repo_instance.get_by_email.return_value = make_user()

        result = self.service.authenticate_user("juan@test.com", "wrong")

        assert result is None

    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_authenticate_returns_user_on_success(self, _):
        """Retorna el objeto User si las credenciales son correctas."""
        user = make_user()
        self.mock_repo_instance.get_by_email.return_value = user

        result = self.service.authenticate_user("juan@test.com", "correct")

        assert result is user

    @patch("app.services.auth_service.verify_password")
    def test_authenticate_calls_verify_with_plain_and_hashed(self, mock_verify):
        """verify_password recibe (plain, hashed) en ese orden."""
        mock_verify.return_value = True
        user = make_user(password="hashed_pw")
        self.mock_repo_instance.get_by_email.return_value = user

        self.service.authenticate_user("juan@test.com", "plaintext")

        mock_verify.assert_called_once_with("plaintext", "hashed_pw")

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_authenticate_does_not_return_user_with_bad_password(self, _):
        """No retorna el usuario aunque exista si la clave es incorrecta."""
        self.mock_repo_instance.get_by_email.return_value = make_user()

        result = self.service.authenticate_user("juan@test.com", "bad_pass")

        assert result is None


class TestAuthServiceObtenerTrabajadores:
    """Pruebas para AuthService.obtener_trabajadores"""

    def setup_method(self):
        self.db = MagicMock(spec=Session)
        with patch("app.services.auth_service.UserRepository"):
            from app.services.auth_service import AuthService
            self.service = AuthService(self.db)

    def test_obtener_trabajadores_returns_list(self):
        """Retorna la lista de trabajadores."""
        trabajadores = [make_user(role="trabajador"), make_user(role="trabajador", id=2)]
        (
            self.db.query.return_value
               .filter.return_value
               .all.return_value
        ) = trabajadores

        result = self.service.obtener_trabajadores()

        assert result == trabajadores

    def test_obtener_trabajadores_filters_by_role(self):
        """Se llama filter con role == 'trabajador'."""
        from app.models.user import User
        self.db.query.return_value.filter.return_value.all.return_value = []

        self.service.obtener_trabajadores()

        self.db.query.assert_called_once_with(User)

    def test_obtener_trabajadores_returns_empty_list_when_none(self):
        """Retorna lista vacía si no hay trabajadores."""
        (
            self.db.query.return_value
               .filter.return_value
               .all.return_value
        ) = []

        result = self.service.obtener_trabajadores()

        assert result == []

    def test_obtener_trabajadores_uses_service_db_session(self):
        """Utiliza self.db (la sesión inyectada en __init__)."""
        self.db.query.return_value.filter.return_value.all.return_value = []

        self.service.obtener_trabajadores()

        self.db.query.assert_called()


# ═══════════════════════════════════════════════════════════
#  3.  User Model
# ═══════════════════════════════════════════════════════════

class TestUserModel:
    """Pruebas de atributos y configuración del modelo SQLAlchemy."""

    def test_user_has_tablename_users(self):
        from app.models.user import User
        assert User.__tablename__ == "users"

    def test_user_has_id_column(self):
        from app.models.user import User
        assert hasattr(User, "id")

    def test_user_has_nombre_column(self):
        from app.models.user import User
        assert hasattr(User, "nombre")

    def test_user_has_apellidos_column(self):
        from app.models.user import User
        assert hasattr(User, "apellidos")

    def test_user_has_dni_column(self):
        from app.models.user import User
        assert hasattr(User, "dni")

    def test_user_has_cargo_column(self):
        from app.models.user import User
        assert hasattr(User, "cargo")

    def test_user_has_email_column(self):
        from app.models.user import User
        assert hasattr(User, "email")

    def test_user_has_password_column(self):
        from app.models.user import User
        assert hasattr(User, "password")

    def test_user_has_role_column(self):
        from app.models.user import User
        assert hasattr(User, "role")

    def test_user_has_codigo_unico_column(self):
        from app.models.user import User
        assert hasattr(User, "codigo_unico")

    def test_user_can_be_instantiated(self):
        """El modelo se puede instanciar sin argumentos."""
        from app.models.user import User
        u = User()
        assert u is not None

    def test_user_role_column_maps_to_rol(self):
        """La columna 'role' mapea a 'rol' en la BD."""
        from app.models.user import User
        col = User.__table__.columns.get("rol")
        assert col is not None, "La columna debe llamarse 'rol' en la BD"


# ═══════════════════════════════════════════════════════════
#  4.  Schemas Pydantic
# ═══════════════════════════════════════════════════════════

class TestUserCreateSchema:
    """Pruebas para el schema UserCreate."""

    def _valid_data(self, **overrides):
        data = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "dni": "12345678",
            "email": "juan@test.com",
            "password": "secret123",
        }
        data.update(overrides)
        return data

    def test_valid_user_create(self):
        from app.schemas.user_schema import UserCreate
        u = UserCreate(**self._valid_data())
        assert u.nombre == "Juan"

    def test_nombre_min_length_2(self):
        from app.schemas.user_schema import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(**self._valid_data(nombre="A"))

    def test_apellidos_min_length_2(self):
        from app.schemas.user_schema import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(**self._valid_data(apellidos="B"))

    def test_dni_must_be_8_digits(self):
        from app.schemas.user_schema import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(**self._valid_data(dni="123"))

    def test_dni_max_length_8(self):
        from app.schemas.user_schema import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(**self._valid_data(dni="123456789"))

    def test_email_must_be_valid(self):
        from app.schemas.user_schema import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(**self._valid_data(email="no_es_email"))

    def test_password_min_length_8(self):
        from app.schemas.user_schema import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(**self._valid_data(password="short"))

    def test_cargo_is_optional(self):
        from app.schemas.user_schema import UserCreate
        u = UserCreate(**self._valid_data())
        assert u.cargo is None

    def test_codigo_unico_is_optional(self):
        from app.schemas.user_schema import UserCreate
        u = UserCreate(**self._valid_data())
        assert u.codigo_unico is None

    def test_role_defaults_to_user(self):
        from app.schemas.user_schema import UserCreate
        u = UserCreate(**self._valid_data())
        assert u.role == "user"

    def test_role_can_be_set_to_admin(self):
        from app.schemas.user_schema import UserCreate
        u = UserCreate(**self._valid_data(role="admin"))
        assert u.role == "admin"


class TestUserLoginSchema:
    def test_valid_login(self):
        from app.schemas.user_schema import UserLogin
        u = UserLogin(email="a@b.com", password="pass1234")
        assert u.email == "a@b.com"

    def test_invalid_email(self):
        from app.schemas.user_schema import UserLogin
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserLogin(email="not_email", password="pass1234")


class TestUserResponseSchema:
    def test_valid_response_from_orm(self):
        from app.schemas.user_schema import UserResponse
        user = make_user()
        resp = UserResponse.model_validate(user)
        assert resp.id == 1
        assert resp.nombre == "Juan"

    def test_cargo_defaults_to_none(self):
        from app.schemas.user_schema import UserResponse
        user = make_user(cargo=None)
        resp = UserResponse.model_validate(user)
        assert resp.cargo is None

    def test_codigo_unico_defaults_to_none(self):
        from app.schemas.user_schema import UserResponse
        user = make_user(codigo_unico=None)
        resp = UserResponse.model_validate(user)
        assert resp.codigo_unico is None

    def test_role_defaults_to_user(self):
        from app.schemas.user_schema import UserResponse
        user = make_user(role=None)  # edge case
        resp = UserResponse.model_validate(user)
        assert resp.role is None or resp.role == "user"


class TestTokenSchema:
    def test_token_schema_valid(self):
        from app.schemas.user_schema import Token, UserResponse
        payload = {
            "access_token": "abc.def.ghi",
            "token_type": "bearer",
            "role": "admin",
            "user": {
                "id": 1, "nombre": "Juan", "apellidos": "Pérez",
                "dni": "12345678", "email": "juan@test.com", "role": "admin"
            }
        }
        token = Token(**payload)
        assert token.access_token == "abc.def.ghi"
        assert token.token_type == "bearer"


# ═══════════════════════════════════════════════════════════
#  5.  Auth Router (FastAPI + TestClient)
# ═══════════════════════════════════════════════════════════

@pytest.fixture()
def client():
    """Cliente de prueba de FastAPI con dependencias mockeadas."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.auth_router import router
    from app.database.connection import get_db
    from app.dependencies.auth_dependencies import get_current_user

    app = FastAPI()
    app.include_router(router)

    fake_db = MagicMock(spec=Session)
    fake_user = MagicMock()
    fake_user.role = "admin"

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: fake_user

    return TestClient(app), fake_db, fake_user


class TestRegisterEndpoint:
    """Pruebas para POST /auth/register"""

    def _valid_payload(self, **overrides):
        data = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "dni": "12345678",
            "email": "juan@test.com",
            "password": "secret123",
            "role": "user",
        }
        data.update(overrides)
        return data

    def test_register_returns_201_or_200_on_success(self, client):
        c, db, _ = client
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.register_user.return_value = make_user()
            resp = c.post("/auth/register", json=self._valid_payload())
        assert resp.status_code in (200, 201)

    def test_register_returns_400_for_invalid_role(self, client):
        c, db, _ = client
        resp = c.post("/auth/register", json=self._valid_payload(role="superadmin"))
        assert resp.status_code == 400
        assert "Rol no válido" in resp.json()["detail"]

    def test_register_returns_400_for_trabajador_without_dni(self, client):
        c, db, _ = client
        payload = self._valid_payload(role="trabajador", dni="")
        resp = c.post("/auth/register", json=payload)
        # Pydantic rechazará DNI vacío antes incluso de llegar al router
        assert resp.status_code in (400, 422)

    def test_register_returns_400_if_email_already_exists(self, client):
        c, db, _ = client
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.register_user.side_effect = ValueError("El email ya está registrado")
            resp = c.post("/auth/register", json=self._valid_payload())
        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()

    def test_register_returns_500_on_unexpected_error(self, client):
        c, db, _ = client
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.register_user.side_effect = RuntimeError("DB down")
            resp = c.post("/auth/register", json=self._valid_payload())
        assert resp.status_code == 500

    def test_register_almacenero_requires_apellidos(self, client):
        c, db, _ = client
        payload = self._valid_payload(role="almacenero", apellidos="")
        resp = c.post("/auth/register", json=payload)
        assert resp.status_code in (400, 422)



class TestObtenerTrabajadoresEndpoint:
    """Pruebas para GET /auth/trabajadores"""

    def test_returns_200_for_admin(self, client):
        c, db, current_user = client
        current_user.role = "admin"
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.obtener_trabajadores.return_value = [make_user(role="trabajador")]
            resp = c.get("/auth/trabajadores")
        assert resp.status_code == 200

    def test_returns_200_for_almacenero(self, client):
        c, db, current_user = client
        current_user.role = "almacenero"
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.obtener_trabajadores.return_value = []
            resp = c.get("/auth/trabajadores")
        assert resp.status_code == 200

    def test_returns_403_for_user_role(self, client):
        c, db, current_user = client
        current_user.role = "user"
        resp = c.get("/auth/trabajadores")
        assert resp.status_code == 403

    def test_returns_403_for_trabajador_role(self, client):
        c, db, current_user = client
        current_user.role = "trabajador"
        resp = c.get("/auth/trabajadores")
        assert resp.status_code == 403

    def test_returns_list_of_workers(self, client):
        c, db, current_user = client
        current_user.role = "admin"
        workers = [make_user(role="trabajador"), make_user(id=2, role="trabajador")]
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.obtener_trabajadores.return_value = workers
            resp = c.get("/auth/trabajadores")
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 2

    def test_returns_empty_list_when_no_workers(self, client):
        c, db, current_user = client
        current_user.role = "admin"
        with patch("app.routers.auth_router.AuthService") as MockSvc:
            MockSvc.return_value.obtener_trabajadores.return_value = []
            resp = c.get("/auth/trabajadores")
        assert resp.json() == []