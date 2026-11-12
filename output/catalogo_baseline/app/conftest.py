import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base
from app.database.connection import get_db  
from app.main import app  
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_db():
    """Mock puro para pruebas unitarias de services y routers"""
    return MagicMock()

@pytest.fixture
def client():
    """TestClient con override de get_db"""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def mock_current_user_almacenero():
    user = MagicMock()
    user.id = 999
    user.role = "almacenero"
    return user

@pytest.fixture
def mock_current_user_trabajador():
    user = MagicMock()
    user.id = 100
    user.role = "trabajador"
    return user