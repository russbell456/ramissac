from __future__ import annotations

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("DATABASE_PUBLIC_URL")
)

if not DATABASE_URL:
    raise RuntimeError("❌ NO HAY DATABASE_URL NI DATABASE_PUBLIC_URL")

SECRET_KEY = os.getenv("SECRET_KEY", "dev")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
BASE_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "ordenes_compra")
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)