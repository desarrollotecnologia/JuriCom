"""Caso de uso: obtener un contrato por id."""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion


class GetContrato:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User, contrato_id: int) -> Contrato:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")

        if actor.is_compras() and contrato.creado_por_id != actor.id:
            raise UnauthorizedError("No puedes ver contratos que no creaste.")
        if actor.is_juridica() and contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )

        return contrato
