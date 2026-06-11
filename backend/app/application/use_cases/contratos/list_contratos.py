"""Caso de uso: listar contratos.

- Admin y Jurídica ven todos.
- Compras ve sólo los suyos.
"""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User


class ListContratos:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User) -> list[Contrato]:
        if actor.is_admin() or actor.is_juridica():
            return self._contratos.list_all()
        return self._contratos.list_by_creador(actor.id)
