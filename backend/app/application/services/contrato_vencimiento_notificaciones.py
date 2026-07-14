"""Notificaciones automáticas de vencimiento de contratos."""

from dataclasses import dataclass
from datetime import datetime, time

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.domain.value_objects.estado_contrato import EstadoContrato


HORA_NOTIFICACION_DEFAULT = time(0, 10)


@dataclass
class ResultadoNotificacionVencimientos:
    enviado: bool
    cantidad_contratos: int
    destinatarios: list[str]
    mensaje: str


def dias_para_vencer(contrato) -> int | None:
    if not contrato.fecha_fin:
        return None
    return (contrato.fecha_fin - datetime.now().date()).days


def fecha_hora_programada(contrato) -> datetime | None:
    if not contrato.fecha_proxima_notificacion:
        return None
    return datetime.combine(
        contrato.fecha_proxima_notificacion,
        contrato.hora_proxima_notificacion or HORA_NOTIFICACION_DEFAULT,
    )


def debe_notificar_vencimiento(contrato, ahora: datetime | None = None) -> bool:
    programada = fecha_hora_programada(contrato)
    if programada is None:
        return False
    ahora = ahora or datetime.now()
    if programada > ahora:
        return False
    ultima = contrato.fecha_ultima_notificacion_vencimiento
    return ultima is None or ultima < programada


def enviar_notificaciones_vencimiento(
    contratos: ContratoRepository,
    notifier: EmailNotifier,
    destinatarios: list[str],
) -> ResultadoNotificacionVencimientos:
    if not destinatarios:
        return ResultadoNotificacionVencimientos(
            enviado=False,
            cantidad_contratos=0,
            destinatarios=[],
            mensaje="No hay destinatarios configurados.",
        )

    activos = contratos.search(estado=EstadoContrato.ACTIVO, solo_aprobados=True)
    ahora = datetime.now()
    por_vencer = [
        (contrato, dias_para_vencer(contrato))
        for contrato in activos
        if debe_notificar_vencimiento(contrato, ahora)
    ]

    if not por_vencer:
        return ResultadoNotificacionVencimientos(
            enviado=True,
            cantidad_contratos=0,
            destinatarios=destinatarios,
            mensaje="No hay contratos con notificación pendiente.",
        )
    if not notifier.disponible:
        return ResultadoNotificacionVencimientos(
            enviado=False,
            cantidad_contratos=len(por_vencer),
            destinatarios=destinatarios,
            mensaje="SMTP no disponible; no se pudo enviar.",
        )

    filas = "".join(
        f"<tr><td>{c.codigo}</td><td>{c.proveedor_contratista}</td>"
        f"<td>{c.fecha_proxima_notificacion} {(c.hora_proxima_notificacion or HORA_NOTIFICACION_DEFAULT).strftime('%H:%M')}</td>"
        f"<td>{c.fecha_fin or 'Sin definir'}</td>"
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
            <tbody>{filas}</tbody>
        </table>
    """
    cuerpo_texto = "\n".join(
        [
            "JURICOM_BEEF - Recordatorios de contratos programados por Jurídica",
            "",
            *[
                f"- {c.codigo} | {c.proveedor_contratista} | notificar {c.fecha_proxima_notificacion} {(c.hora_proxima_notificacion or HORA_NOTIFICACION_DEFAULT).strftime('%H:%M')} | vence {c.fecha_fin or 'sin definir'} | faltan {dias if dias is not None else 'sin definir'} día(s)"
                for c, dias in por_vencer
            ],
        ]
    )

    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] {len(por_vencer)} recordatorio(s) de contrato",
            destinatarios=destinatarios,
            cuerpo_html=cuerpo_html,
            cuerpo_texto=cuerpo_texto,
        )
    )

    enviado_at = datetime.now()
    for contrato, _ in por_vencer:
        contrato.fecha_ultima_notificacion_vencimiento = enviado_at
        contratos.update(contrato)

    return ResultadoNotificacionVencimientos(
        enviado=True,
        cantidad_contratos=len(por_vencer),
        destinatarios=destinatarios,
        mensaje=f"Correo de vencimientos enviado con {len(por_vencer)} contrato(s).",
    )
