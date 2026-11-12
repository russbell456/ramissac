from __future__ import annotations

from argon2 import PasswordHasher

ph = PasswordHasher()

class Hash:
    @staticmethod
    def get_password_hash(password: str):
        return ph.hash(password)

    @staticmethod
    def verify_password(plain_password, hashed_password):
        try:
            return ph.verify(hashed_password, plain_password)
        except:
            return False
