"""Implementación de PasswordHasher usando bcrypt directamente.

Usamos `bcrypt` (no `passlib`) porque `passlib` no ha tenido nuevos
releases en años y rompe con Python ≥ 3.13. `bcrypt` es la librería
oficial mantenida por la PyCA.
"""

import bcrypt

from app.application.interfaces.password_hasher import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    """Hash bcrypt con cost factor 12 (estándar OWASP 2024+)."""

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, plain: str) -> str:
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
