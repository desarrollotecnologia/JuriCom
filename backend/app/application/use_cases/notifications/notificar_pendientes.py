"""Caso de uso: enviar un resumen de contratos pendientes (en proceso)."""

import logging
from dataclasses import dataclass

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_contrato import EstadoContrato


logger = logging.getLogger(__name__)


@dataclass
class ResultadoNotificacion:
    enviado: bool
    cantidad_contratos: int
    destinatarios: list[str]


class NotificarPendientes:
    def __init__(
        self, contratos: ContratoRepository, notifier: EmailNotifier
    ) -> None:
        self._contratos = contratos
        self._notifier = notifier

    def execute(self, actor: User, destinatarios: list[str]) -> ResultadoNotificacion:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica o el Administrador pueden disparar esta notificación."
            )
        if not destinatarios:
            return ResultadoNotificacion(False, 0, [])
        if not self._notifier.disponible:
            logger.warning("SMTP no disponible; omito envío de pendientes.")
            return ResultadoNotificacion(False, 0, destinatarios)

        pendientes = self._contratos.search(
            estado=EstadoContrato.EN_PROCESO, solo_aprobados=True
        )

        from app.infrastructure.email.templates import (
            render_pendientes_html,
            render_pendientes_texto,
        )

        asunto = (
            f"[JURICOM_BEEF] {len(pendientes)} contrato(s) en proceso pendientes"
            if pendientes
            else "[JURICOM_BEEF] Sin contratos pendientes"
        )
        try:
            self._notifier.send(
                EmailMessage(
                    asunto=asunto,
                    destinatarios=destinatarios,
                    cuerpo_html=render_pendientes_html(pendientes),
                    cuerpo_texto=render_pendientes_texto(pendientes),
                )
            )
            return ResultadoNotificacion(True, len(pendientes), destinatarios)
        except Exception:
            return ResultadoNotificacion(False, len(pendientes), destinatarios)
