"""Sub-flujo de cierre del contrato tras el informe final / acta de liquidación.

Cuando el supervisor finaliza (o Jurídica carga el acta en contratos > umbral), el
contrato no queda finalizado de inmediato: recorre el pago final:

    (informe/acta) → Cierre en Contabilidad → Cierre en Tesorería → Completado

Al igual que el anticipo, cada transición sólo cambia el estado del contrato; la
trazabilidad (observación + evidencia) y las notificaciones las maneja la capa de
presentación (endpoints), que tiene acceso a la SRV y al almacenamiento.
"""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_contrato import EstadoContrato


class GestionarCierreContabilidad:
    """Contabilidad recibe el cierre, adjunta el comentario+archivo y envía a Tesorería."""

    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User, contrato_id: int) -> Contrato:
        if not actor.puede_gestionar_anticipo_contabilidad():
            raise UnauthorizedError("Sólo Contabilidad puede gestionar el cierre.")
        contrato = self._get(contrato_id)
        if contrato.estado != EstadoContrato.CIERRE_CONTABILIDAD:
            raise ValueError("El cierre no está en gestión de Contabilidad.")
        contrato.estado = EstadoContrato.CIERRE_TESORERIA
        return self._contratos.update(contrato)

    def _get(self, contrato_id: int) -> Contrato:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        return contrato


class ConfirmarCierreTesoreria:
    """Tesorería realiza el pago final, adjunta la evidencia y completa el contrato."""

    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User, contrato_id: int) -> Contrato:
        if not actor.puede_gestionar_anticipo_tesoreria():
            raise UnauthorizedError("Sólo Tesorería puede confirmar el pago del cierre.")
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado != EstadoContrato.CIERRE_TESORERIA:
            raise ValueError("El cierre no está en revisión de Tesorería.")
        contrato.estado = EstadoContrato.COMPLETADO
        return self._contratos.update(contrato)
