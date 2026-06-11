"""Caso de uso: crear un nuevo usuario (sólo admin)."""

from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import (
    UnauthorizedError,
    UserAlreadyExistsError,
)
from app.domain.value_objects.roles import Role


class CreateUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    def execute(
        self,
        actor: User,
        username: str,
        password: str,
        role: Role,
    ) -> User:
        if not actor.can_manage_users():
            raise UnauthorizedError("Sólo el administrador puede crear usuarios.")

        username = username.strip()
        if not username:
            raise ValueError("El username no puede estar vacío.")
        if len(password) < 4:
            raise ValueError("La contraseña debe tener al menos 4 caracteres.")

        if self._users.get_by_username(username) is not None:
            raise UserAlreadyExistsError(f"Ya existe un usuario con username '{username}'.")

        new_user = User(
            username=username,
            password_hash=self._hasher.hash(password),
            role=role,
            is_active=True,
            created_by_id=actor.id,
        )
        return self._users.create(new_user)
