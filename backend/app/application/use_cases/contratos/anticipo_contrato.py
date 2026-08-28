"""Sub-flujo del anticipo del contrato antes de activarlo.

Cuando un contrato tiene anticipo, antes de pasar a ACTIVO debe recorrer:
    Jurídica → Contabilidad → Tesorería → (vuelve a Jurídica) → Activo

Cada transición sólo cambia el estado del contrato; la trazabilidad
(observación + evidencia) y las notificaciones las maneja la capa de
presentación (endpoints), que sí tiene acceso a la SRV y al almacenamiento.
"""

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato

# Tras el pago de Tesorería el contrato pasa a ANTICIPO_PAGADO: el pago quedó hecho
# y se avisa a Jurídica, que continúa el flujo y lo activa cuando corresponda.
ESTADO_RETORNO_TRAS_PAGO = EstadoContrato.ANTICIPO_PAGADO

_ESTADOS_PREVIOS_ANTICIPO = {
    EstadoContrato.EN_PROCESO,
    EstadoContrato.ELABORANDO,
    EstadoContrato.REVISION_POLIZAS,
    EstadoContrato.SOLICITUD_FIRMAS,
}


class EnviarAnticipoContabilidad:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User, contrato_id: int) -> Contrato:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica o el Administrador pueden enviar el anticipo a Contabilidad."
            )
        contrato = self._get(contrato_id)
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )
        if not contrato.requiere_anticipo:
            raise ValueError("Este contrato no tiene anticipo.")
        if contrato.anticipo_pagado:
            raise ValueError("El anticipo de este contrato ya fue pagado.")
        if contrato.estado not in _ESTADOS_PREVIOS_ANTICIPO:
            raise ValueError(
                "El anticipo sólo se puede enviar a Contabilidad antes de activar el contrato."
            )
        # Jurídica primero gestiona la póliza y el contrato firmado; recién ahí
        # se habilita el anticipo.
        if not contrato.tiene_borrador():
            raise ValueError(
                "Adjunta primero el contrato firmado antes de enviar el anticipo a Contabilidad."
            )
        if contrato.requiere_poliza and not contrato.tiene_poliza():
            raise ValueError(
                "Adjunta primero la póliza antes de enviar el anticipo a Contabilidad."
            )
        contrato.estado = EstadoContrato.ANTICIPO_CONTABILIDAD
        return self._contratos.update(contrato)

    def _get(self, contrato_id: int) -> Contrato:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        return contrato


class GestionarAnticipoContabilidad:
    """Contabilidad gestiona y envía a Tesorería."""

    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User, contrato_id: int) -> Contrato:
        if not actor.puede_gestionar_anticipo_contabilidad():
            raise UnauthorizedError("Sólo Contabilidad puede gestionar este anticipo.")
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado != EstadoContrato.ANTICIPO_CONTABILIDAD:
            raise ValueError("El anticipo no está en gestión de Contabilidad.")
        contrato.estado = EstadoContrato.ANTICIPO_TESORERIA
        return self._contratos.update(contrato)


class ConfirmarPagoTesoreria:
    """Tesorería confirma el pago; el contrato vuelve a Jurídica para activarse."""

    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User, contrato_id: int) -> Contrato:
        if not actor.puede_gestionar_anticipo_tesoreria():
            raise UnauthorizedError("Sólo Tesorería puede confirmar el pago del anticipo.")
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado != EstadoContrato.ANTICIPO_TESORERIA:
            raise ValueError("El anticipo no está en revisión de Tesorería.")
        contrato.anticipo_pagado = True
        contrato.estado = ESTADO_RETORNO_TRAS_PAGO
        return self._contratos.update(contrato)
