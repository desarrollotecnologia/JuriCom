"""Interfaz para emisión/validación de tokens (JWT u otro)."""

from abc import ABC, abstractmethod
from typing import Optional


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, subject: str, extra_claims: Optional[dict] = None) -> str: ...

    @abstractmethod
    def decode_token(self, token: str) -> dict: ...
