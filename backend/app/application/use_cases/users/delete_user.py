"""Caso de uso: eliminar usuario (sólo admin)."""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import (
    UnauthorizedError,
    UserInUseError,
    UserNotFoundError,
)


class DeleteUser:
    def __init__(
        self,
        users: UserRepository,
        contratos: ContratoRepository,
    ) -> None:
        self._users = users
        self._contratos = contratos

    def execute(self, actor: User, target_user_id: int) -> None:
        if not actor.can_manage_users():
            raise UnauthorizedError("Sólo el administrador puede eliminar usuarios.")
        if actor.id == target_user_id:
            raise UnauthorizedError("No puedes eliminar tu propia cuenta.")

        target = self._users.get_by_id(target_user_id)
        if target is None:
            raise UserNotFoundError(f"No existe el usuario con id {target_user_id}.")

        if self._contratos.user_has_related_records(target_user_id):
            raise UserInUseError(
                "No se puede eliminar este usuario porque tiene contratos u otrosíes "
                "asociados. Desactívalo en su lugar."
            )

        self._users.delete(target_user_id)
