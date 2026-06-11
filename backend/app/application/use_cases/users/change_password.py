"""Caso de uso: cambiar contraseña de un usuario.

- Un admin puede cambiar la de cualquiera.
- Un usuario común sólo puede cambiar la suya.
"""

from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError, UserNotFoundError


class ChangePassword:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    def execute(self, actor: User, target_user_id: int, new_password: str) -> User:
        if actor.id != target_user_id and not actor.can_manage_users():
            raise UnauthorizedError("No tienes permisos para cambiar esta contraseña.")

        if len(new_password) < 4:
            raise ValueError("La contraseña debe tener al menos 4 caracteres.")

        target = self._users.get_by_id(target_user_id)
        if target is None:
            raise UserNotFoundError(f"No existe el usuario con id {target_user_id}.")

        target.password_hash = self._hasher.hash(new_password)
        return self._users.update(target)
