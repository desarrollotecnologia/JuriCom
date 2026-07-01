"""Caso de uso: listar contratos.

- Admin y Jurídica ven sólo contratos aprobados por líder y gerencia.
- Compras ve sólo los suyos.
"""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion


class ListContratos:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User) -> list[Contrato]:
        if actor.is_admin() or actor.is_juridica():
            return [
                contrato
                for contrato in self._contratos.list_all()
                if contrato.estado_aprobacion == EstadoAprobacion.APROBADO
            ]
        return self._contratos.list_by_creador(actor.id)
