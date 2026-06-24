"""Caso de uso: editar usuario (cambiar username, rol, activo) — sólo admin."""

from typing import Optional

from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import (
    UnauthorizedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.domain.value_objects.roles import Role


class UpdateUser:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(
        self,
        actor: User,
        target_user_id: int,
        new_username: Optional[str] = None,
        new_role: Optional[Role] = None,
        new_is_active: Optional[bool] = None,
        new_email: Optional[str] = None,
    ) -> User:
        if not actor.can_manage_users():
            raise UnauthorizedError("Sólo el administrador puede editar usuarios.")

        target = self._users.get_by_id(target_user_id)
        if target is None:
            raise UserNotFoundError(f"No existe el usuario con id {target_user_id}.")

        if new_username is not None:
            new_username = new_username.strip()
            if new_username != target.username:
                existing = self._users.get_by_username(new_username)
                if existing is not None and existing.id != target.id:
                    raise UserAlreadyExistsError(
                        f"Ya existe un usuario con username '{new_username}'."
                    )
                target.username = new_username

        if new_role is not None:
            target.role = new_role

        if new_is_active is not None:
            # Evitar que el admin se desactive a sí mismo y se quede fuera.
            if target.id == actor.id and not new_is_active:
                raise UnauthorizedError("No puedes desactivar tu propia cuenta.")
            target.is_active = new_is_active

        if new_email is not None:
            target.email = new_email.strip()

        return self._users.update(target)
