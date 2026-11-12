
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import DATABASE_URL

# Crear engine
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Crear sesión
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Dependency para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
