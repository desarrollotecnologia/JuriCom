"""Caso de uso: buscar contratos con filtros.

- Admin y Jurídica ven sólo contratos aprobados por líder y gerencia.
- Compras sólo ve los suyos, incluso si siguen en aprobación.
- El supervisor (rol solicitante) sólo ve los contratos aprobados donde está
  asignado como supervisor encargado (para poder finalizarlos).
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
        eliminados: bool = False,
    ) -> list[Contrato]:
        creador_id: Optional[int] = None
        supervisor_id: Optional[int] = None
        if actor.is_compras():
            creador_id = actor.id
        if actor.is_solicitante():
            supervisor_id = actor.id

        solo_aprobados = (
            actor.is_admin()
            or actor.is_juridica()
            or actor.is_solicitante()
            or actor.is_contabilidad()
            or actor.is_tesoreria()
        )

        # Contabilidad y Tesorería ven los contratos en su etapa, tanto del anticipo
        # (antes de activar) como del cierre final (tras informe/acta).
        estados_rol: Optional[list[EstadoContrato]] = None
        if actor.is_contabilidad():
            estados_rol = [
                EstadoContrato.ANTICIPO_CONTABILIDAD,
                EstadoContrato.CIERRE_CONTABILIDAD,
            ]
        elif actor.is_tesoreria():
            estados_rol = [
                EstadoContrato.ANTICIPO_TESORERIA,
                EstadoContrato.CIERRE_TESORERIA,
            ]

        if estados_rol is not None:
            vistos: dict[int, Contrato] = {}
            for est in estados_rol:
                for c in self._contratos.search(
                    query=query,
                    estado=est,
                    solo_aprobados=solo_aprobados,
                    incluir_eliminados=eliminados,
                ):
                    vistos[c.id] = c
            return sorted(vistos.values(), key=lambda c: c.id or 0, reverse=True)

        return self._contratos.search(
            query=query,
            estado=estado,
            creador_id=creador_id,
            supervisor_id=supervisor_id,
            solo_aprobados=solo_aprobados,
            incluir_eliminados=eliminados,
        )
