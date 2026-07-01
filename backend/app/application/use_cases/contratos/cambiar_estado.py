"""Caso de uso: cambiar el estado de un contrato.

Sólo Jurídica y Admin pueden hacerlo.
Reglas de negocio:
- No se puede pasar a ACTIVO si requiere póliza y aún no se ha adjuntado.
- FINALIZADO es estado terminal (se puede volver a abrir si fuese necesario,
  pero la operación normal es de un solo paso).
"""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato


class CambiarEstadoContrato:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(
        self, actor: User, contrato_id: int, nuevo_estado: EstadoContrato
    ) -> Contrato:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica o el Administrador pueden cambiar el estado."
            )

        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )

        if (
            nuevo_estado == EstadoContrato.ACTIVO
            and contrato.requiere_poliza_y_no_la_tiene()
        ):
            raise ValueError(
                "No se puede marcar como ACTIVO: este contrato requiere "
                "póliza y todavía no ha sido adjuntada."
            )

        contrato.estado = nuevo_estado
        return self._contratos.update(contrato)
