from __future__ import annotations
import jwt
from datetime import datetime, timedelta

SECRET = "MISECRETO"
ALGORITHM = "HS256"

class JWTManager:

    @staticmethod
    def create_token(data: dict):
        to_encode = data.copy()
        to_encode["exp"] = datetime.utcnow() + timedelta(hours=8)
        return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)
