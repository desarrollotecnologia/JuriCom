"""Tareas automáticas mientras el servidor está encendido."""

import asyncio
import logging

from app.application.services.contrato_vencimiento_notificaciones import (
    enviar_notificaciones_vencimiento,
)
from app.infrastructure.config import settings
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.email import SmtpEmailNotifier
from app.infrastructure.repositories import SqlAlchemyContratoRepository


logger = logging.getLogger(__name__)


async def vencimientos_scheduler(stop_event: asyncio.Event) -> None:
    """Revisa recordatorios programados sin depender de un botón manual."""
    logger.info("Scheduler de vencimientos iniciado.")
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(_run_vencimientos_once)
        except Exception:
            logger.exception("Error ejecutando scheduler de vencimientos.")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
    logger.info("Scheduler de vencimientos detenido.")


def _run_vencimientos_once() -> None:
    destinatarios = settings.juridica_emails_list + settings.compras_emails_list
    if not destinatarios:
        return
    db = SessionLocal()
    try:
        resultado = enviar_notificaciones_vencimiento(
            SqlAlchemyContratoRepository(db),
            SmtpEmailNotifier(),
            destinatarios,
        )
        if resultado.cantidad_contratos:
            logger.info(
                "Scheduler vencimientos: %s contrato(s), enviado=%s.",
                resultado.cantidad_contratos,
                resultado.enviado,
            )
    finally:
        db.close()
