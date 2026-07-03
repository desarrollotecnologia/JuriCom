"""Caso de uso: crear un nuevo usuario (sólo admin)."""

from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import (
    UnauthorizedError,
    UserAlreadyExistsError,
)
from app.domain.value_objects.roles import Role


def _validar_lider_catalog_id(role: Role, lider_catalog_id: str) -> str:
    lid = (lider_catalog_id or "").strip()
    if role == Role.LIDER_APROBADOR and not lid:
        raise ValueError(
            "Debes seleccionar el líder del catálogo para el rol Líder Aprobador."
        )
    return lid if role == Role.LIDER_APROBADOR else ""


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
        email: str = "",
        lider_catalog_id: str = "",
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
            email=(email or "").strip(),
            lider_catalog_id=_validar_lider_catalog_id(role, lider_catalog_id),
            is_active=True,
            created_by_id=actor.id,
        )
        return self._users.create(new_user)
