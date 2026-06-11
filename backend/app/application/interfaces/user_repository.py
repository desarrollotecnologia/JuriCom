"""Contrato (interfaz) que cualquier repositorio de usuarios debe cumplir.

Esto permite intercambiar la implementación (MySQL, Postgres, memoria
para tests) sin tocar los casos de uso.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    def list_all(self) -> list[User]: ...

    @abstractmethod
    def create(self, user: User) -> User: ...

    @abstractmethod
    def update(self, user: User) -> User: ...

    @abstractmethod
    def delete(self, user_id: int) -> None: ...
