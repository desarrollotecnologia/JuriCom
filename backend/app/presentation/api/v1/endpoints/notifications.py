"""Endpoints para disparar notificaciones manualmente desde el sistema."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.application.use_cases.notifications import NotificarPendientes
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
    get_email_notifier,
)
from app.presentation.api.v1.schemas import NotificacionResponse


router = APIRouter(prefix="/notifications", tags=["notifications"])


def _dias_para_vencer(c) -> int | None:
    if not c.fecha_fin:
        return None
    return (c.fecha_fin - date.today()).days


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

    activos = contratos.search(estado=EstadoContrato.ACTIVO, solo_aprobados=True)
    por_vencer = []
    for contrato in activos:
        if (
            contrato.fecha_proxima_notificacion
            and contrato.fecha_proxima_notificacion <= date.today()
        ):
            dias = _dias_para_vencer(contrato)
            por_vencer.append((contrato, dias))

    if not notifier.disponible:
        return NotificacionResponse(
            enviado=False,
            cantidad_contratos=len(por_vencer),
            destinatarios=destinatarios,
            mensaje="SMTP no disponible; no se pudo enviar.",
        )

    filas = "".join(
        f"<tr><td>{c.codigo}</td><td>{c.proveedor_contratista}</td>"
        f"<td>{c.fecha_proxima_notificacion}</td><td>{c.fecha_fin or 'Sin definir'}</td>"
        f"<td>{dias if dias is not None else 'Sin definir'}</td>"
        f"<td>{'Sí' if c.renovacion_automatica else 'No'}</td></tr>"
        for c, dias in por_vencer
    )
    cuerpo_html = f"""
        <h2>Recordatorios de contratos programados por Jurídica</h2>
        <p>
            Estos contratos tienen fecha de nueva notificación para hoy o una
            fecha anterior. Revisa con el líder del proceso y Jurídica si se van
            a renovar, modificar o dejar vencer.
        </p>
        <table border="1" cellpadding="8" cellspacing="0">
            <thead>
                <tr>
                    <th>Código</th><th>Proveedor</th><th>Fecha notificación</th>
                    <th>Fecha fin</th><th>Días restantes</th>
                    <th>Renovación automática</th>
                </tr>
            </thead>
            <tbody>{filas or '<tr><td colspan="6">No hay contratos con notificación programada para hoy.</td></tr>'}</tbody>
        </table>
    """
    cuerpo_texto = "\n".join(
        [
            "JURICOM_BEEF - Recordatorios de contratos programados por Jurídica",
            "",
            *[
                f"- {c.codigo} | {c.proveedor_contratista} | notificar {c.fecha_proxima_notificacion} | vence {c.fecha_fin or 'sin definir'} | faltan {dias if dias is not None else 'sin definir'} día(s)"
                for c, dias in por_vencer
            ],
        ]
    )

    try:
        notifier.send(
            EmailMessage(
                asunto=f"[JURICOM_BEEF] {len(por_vencer)} recordatorio(s) de contrato",
                destinatarios=destinatarios,
                cuerpo_html=cuerpo_html,
                cuerpo_texto=cuerpo_texto,
            )
        )
        enviado = True
    except Exception:
        enviado = False

    return NotificacionResponse(
        enviado=enviado,
        cantidad_contratos=len(por_vencer),
        destinatarios=destinatarios,
        mensaje=(
            f"Correo de vencimientos enviado con {len(por_vencer)} contrato(s)."
            if enviado
            else "No se pudo enviar el correo de recordatorios."
        ),
    )
