"""Caso de uso: notificar al líder cuando se radica un contrato."""

import logging

from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.domain.entities.contrato import Contrato


logger = logging.getLogger(__name__)


class NotificarRadicacion:
    def __init__(self, notifier: EmailNotifier) -> None:
        self._notifier = notifier

    def execute(
        self,
        contrato: Contrato,
        radicado_por: str,
        destinatarios: list[str],
        token_aprobacion: str,
    ) -> bool:
        """Devuelve True si el envío fue exitoso, False si se omitió/falló."""
        if not destinatarios:
            logger.warning("No hay líder configurado; omito envío.")
            return False
        if not self._notifier.disponible:
            logger.warning("SMTP no disponible; omito envío de radicación.")
            return False

        from app.infrastructure.email.templates import (
            render_aprobacion_lider_html,
            render_aprobacion_lider_texto,
        )

        try:
            self._notifier.send(
                EmailMessage(
                    asunto=(
                        f"[JURICOM_BEEF] Aprobar solicitud de contrato — "
                        f"{contrato.codigo}"
                    ),
                    destinatarios=destinatarios,
                    cuerpo_html=render_aprobacion_lider_html(
                        contrato, radicado_por, token_aprobacion
                    ),
                    cuerpo_texto=render_aprobacion_lider_texto(
                        contrato, radicado_por, token_aprobacion
                    ),
                )
            )
            return True
        except Exception:
            return False
