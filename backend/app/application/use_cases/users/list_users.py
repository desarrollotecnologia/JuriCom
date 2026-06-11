"""Caso de uso: listar usuarios (sólo admin)."""

from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError


class ListUsers:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(self, actor: User) -> list[User]:
        if not actor.can_manage_users():
            raise UnauthorizedError("Sólo el administrador puede listar usuarios.")
        return self._users.list_all()
