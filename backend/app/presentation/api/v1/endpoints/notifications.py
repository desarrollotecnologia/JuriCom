"""Endpoints para disparar notificaciones manualmente desde el sistema."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import EmailNotifier
from app.application.services.contrato_vencimiento_notificaciones import (
    enviar_notificaciones_vencimiento,
)
from app.application.use_cases.notifications import NotificarPendientes
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
    get_email_notifier,
)
from app.presentation.api.v1.schemas import NotificacionResponse


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/pendientes", response_model=NotificacionResponse)
def notificar_pendientes(
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> NotificacionResponse:
    """Envía un correo de advertencia con todos los contratos en proceso.

    Sólo Jurídica o Admin pueden dispararlo.
    """
    destinatarios = settings.juridica_emails_list + settings.compras_emails_list
    if not destinatarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay destinatarios configurados (JURIDICA_EMAILS vacío).",
        )

    try:
        resultado = NotificarPendientes(contratos, notifier).execute(
            actor=current, destinatarios=destinatarios
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    msg = (
        f"Correo enviado a {len(resultado.destinatarios)} destinatario(s) con "
        f"{resultado.cantidad_contratos} contrato(s) pendientes."
        if resultado.enviado
        else "No se pudo enviar el correo (revisa los logs y la configuración SMTP)."
    )
    return NotificacionResponse(
        enviado=resultado.enviado,
        cantidad_contratos=resultado.cantidad_contratos,
        destinatarios=resultado.destinatarios,
        mensaje=msg,
    )


@router.post("/vencimientos", response_model=NotificacionResponse)
def notificar_vencimientos(
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> NotificacionResponse:
    """Notifica contratos activos cuando Jurídica programó recordatorio.

    Regla:
    - Jurídica/Admin define `fecha_proxima_notificacion` en la edición del contrato.
    - El contrato se notifica cuando esa fecha es hoy o ya pasó.
    """
    if not (current.is_admin() or current.is_juridica()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo Jurídica o Admin pueden disparar esta notificación.",
        )

    destinatarios = settings.juridica_emails_list + settings.compras_emails_list
    if not destinatarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay destinatarios configurados.",
        )

    try:
        resultado = enviar_notificaciones_vencimiento(
            contratos,
            notifier,
            destinatarios,
        )
    except Exception:
        return NotificacionResponse(
            enviado=False,
            cantidad_contratos=0,
            destinatarios=destinatarios,
            mensaje="No se pudo enviar el correo de recordatorios.",
        )

    return NotificacionResponse(
        enviado=resultado.enviado,
        cantidad_contratos=resultado.cantidad_contratos,
        destinatarios=resultado.destinatarios,
        mensaje=resultado.mensaje,
    )
