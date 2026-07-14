"""Caso de uso: cambiar el estado de un contrato.

Sólo Jurídica y Admin pueden hacerlo.
Reglas de negocio:
- No se puede pasar a ACTIVO si requiere póliza y aún no se ha adjuntado.
- FINALIZADO es estado terminal (se puede volver a abrir si fuese necesario,
  pero la operación normal es de un solo paso).
"""

from datetime import date, time, timedelta

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.use_cases.contratos.radicar_solicitud import calcular_fecha_fin
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
        if nuevo_estado == EstadoContrato.ACTIVO:
            self._asegurar_fechas_vigencia(contrato)
        return self._contratos.update(contrato)

    @staticmethod
    def _asegurar_fechas_vigencia(contrato: Contrato) -> None:
        if contrato.fecha_inicio is None:
            contrato.fecha_inicio = date.today()
        if contrato.fecha_fin is None:
            contrato.fecha_fin = calcular_fecha_fin(
                contrato.fecha_inicio,
                contrato.plazo_cantidad,
                contrato.plazo_unidad,
            )
        if contrato.fecha_proxima_notificacion is None:
            contrato.fecha_proxima_notificacion = max(
                contrato.fecha_inicio,
                contrato.fecha_fin - timedelta(days=30),
            )
        if contrato.hora_proxima_notificacion is None:
            contrato.hora_proxima_notificacion = time(0, 10)
