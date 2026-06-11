"""Caso de uso: buscar contratos con filtros.

- Admin y Jurídica ven todos.
- Compras sólo ve los suyos (se filtra forzando creador_id = actor.id).
"""

from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.value_objects.estado_contrato import EstadoContrato


class BuscarContratos:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(
        self,
        actor: User,
        query: Optional[str] = None,
        estado: Optional[EstadoContrato] = None,
    ) -> list[Contrato]:
        creador_id: Optional[int] = None
        if actor.is_compras():
            creador_id = actor.id
        return self._contratos.search(
            query=query,
            estado=estado,
            creador_id=creador_id,
            solo_aprobados=actor.is_juridica(),
        )
