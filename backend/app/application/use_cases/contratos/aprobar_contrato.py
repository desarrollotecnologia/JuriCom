"""Aprobación secuencial de contratos: Líder de proceso -> Gerencia."""

from datetime import datetime

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.exceptions import ContratoNotFoundError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion


class AprobarContrato:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def aprobar_lider(self, contrato_id: int) -> Contrato:
        contrato = self._get(contrato_id)
        if contrato.estado_aprobacion != EstadoAprobacion.PENDIENTE_LIDER:
            raise ValueError(
                "Esta solicitud no está pendiente de aprobación del líder."
            )
        contrato.estado_aprobacion = EstadoAprobacion.PENDIENTE_GERENCIA
        contrato.aprobado_lider_at = datetime.now()
        return self._contratos.update(contrato)

    def aprobar_gerencia(self, contrato_id: int) -> Contrato:
        contrato = self._get(contrato_id)
        if contrato.estado_aprobacion != EstadoAprobacion.PENDIENTE_GERENCIA:
            raise ValueError("Esta solicitud no está pendiente de aprobación gerencia.")
        contrato.estado_aprobacion = EstadoAprobacion.APROBADO
        contrato.aprobado_gerencia_at = datetime.now()
        return self._contratos.update(contrato)

    def rechazar(self, contrato_id: int, paso: str) -> Contrato:
        contrato = self._get(contrato_id)
        if paso == "lider" and contrato.estado_aprobacion != EstadoAprobacion.PENDIENTE_LIDER:
            raise ValueError("Esta solicitud no está pendiente del líder.")
        if (
            paso == "gerencia"
            and contrato.estado_aprobacion != EstadoAprobacion.PENDIENTE_GERENCIA
        ):
            raise ValueError("Esta solicitud no está pendiente de gerencia.")
        contrato.estado_aprobacion = EstadoAprobacion.RECHAZADO
        return self._contratos.update(contrato)

    def _get(self, contrato_id: int) -> Contrato:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        return contrato
