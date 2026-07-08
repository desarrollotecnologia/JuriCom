"""Notificaciones por correo del flujo Gestión de Solicitudes."""

from __future__ import annotations

import logging
from typing import Optional

from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.application.interfaces.user_repository import UserRepository
from app.application.services.lideres_colbeef import email_lider_catalogo
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen
from app.infrastructure.config import settings
from app.infrastructure.email import templates as tpl

logger = logging.getLogger(__name__)


def resolver_email_solicitante(
    solicitud: SolicitudGestion,
    users: UserRepository,
) -> str:
    if (solicitud.creado_por_email or "").strip():
        return solicitud.creado_por_email.strip()
    if solicitud.creado_por_id:
        user = users.get_by_id(solicitud.creado_por_id)
        if user and (user.email or "").strip():
            return user.email.strip()
    return ""


def _tipo_legible(solicitud: SolicitudGestion) -> str:
    if es_flujo_salidas_almacen(solicitud.tipo):
        return "solicitud de pedido"
    return "solicitud de compra"


class NotificadorSolicitudGestion:
    def __init__(
        self,
        users: UserRepository,
        notifier: EmailNotifier,
    ) -> None:
        self._users = users
        self._notifier = notifier

    def _dedupe(self, emails: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for e in emails:
            key = e.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(e.strip())
        return out

    def _emails_rol(
        self,
        role: Role,
        *,
        exclude_user_id: Optional[int] = None,
    ) -> list[str]:
        emails: list[str] = []
        for user in self._users.list_all():
            if not user.is_active or user.role != role:
                continue
            if exclude_user_id and user.id == exclude_user_id:
                continue
            if (user.email or "").strip():
                emails.append(user.email.strip())
        catalog_email = email_lider_catalogo(lid)
        if catalog_email:
            emails.append(catalog_email)
        return self._dedupe(emails)

    def _emails_lider_catalogo(
        self,
        catalog_id: str,
        *,
        exclude_user_id: Optional[int] = None,
    ) -> list[str]:
        lid = (catalog_id or "").strip()
        if not lid:
            return []
        emails: list[str] = []
        for user in self._users.list_all():
            if not user.is_active or user.role != Role.LIDER_APROBADOR:
                continue
            if (user.lider_catalog_id or "").strip() != lid:
                continue
            if exclude_user_id and user.id == exclude_user_id:
                continue
            if (user.email or "").strip():
                emails.append(user.email.strip())
        return self._dedupe(emails)

    def _send(
        self,
        destinatarios: list[str],
        asunto: str,
        cuerpo_html: str,
        cuerpo_texto: str,
    ) -> bool:
        destinatarios = self._dedupe(destinatarios)
        if not destinatarios:
            return False
        if not self._notifier.disponible:
            logger.warning("SMTP no disponible; omito: %s", asunto)
            return False
        try:
            self._notifier.send(
                EmailMessage(
                    asunto=asunto,
                    destinatarios=destinatarios,
                    cuerpo_html=cuerpo_html,
                    cuerpo_texto=cuerpo_texto,
                )
            )
            return True
        except Exception:
            logger.exception("Error enviando correo: %s", asunto)
            return False

    def _enviar_evento(
        self,
        solicitud: SolicitudGestion,
        *,
        asunto: str,
        titulo: str,
        mensaje: str,
        url: str,
        boton: str,
        destinatarios: list[str],
    ) -> bool:
        html = tpl.render_solicitud_gestion_evento_html(
            solicitud,
            titulo=titulo,
            mensaje=mensaje,
            url=url,
            boton=boton,
        )
        texto = tpl.render_solicitud_gestion_evento_texto(
            solicitud,
            titulo=titulo,
            mensaje=mensaje,
            url=url,
        )
        return self._send(destinatarios, asunto, html, texto)

    def _url_mis_solicitudes(self) -> str:
        return f"{settings.public_url.rstrip('/')}/app/compras/gestion-mis-solicitudes.html"

    def _url_aprobar(self) -> str:
        return f"{settings.public_url.rstrip('/')}/app/compras/gestion-aprobar-solicitudes.html"

    def _url_panel(self) -> str:
        return f"{settings.public_url.rstrip('/')}/app/compras/gestion-panel-solicitudes.html"

    def _url_anticipos(self) -> str:
        return f"{settings.public_url.rstrip('/')}/app/compras/gestion-anticipo.html"

    def notificar_solicitud_creada(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        tipo = _tipo_legible(solicitud)
        codigo = solicitud.codigo or ""
        asunto_base = f"[JURICOM_BEEF] {codigo} — Solicitud registrada"

        sol = resolver_email_solicitante(solicitud, self._users)
        if sol:
            self._enviar_evento(
                solicitud,
                asunto=asunto_base,
                titulo="Solicitud registrada",
                mensaje=(
                    f"Se creó tu nueva {tipo} con consecutivo "
                    f"<strong>{codigo}</strong>. Queda pendiente de aprobación del líder."
                ),
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )

        lideres = self._emails_lider_catalogo(solicitud.lider_area_id)
        if lideres:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Pendiente de aprobación",
                titulo="Nueva solicitud pendiente",
                mensaje=(
                    f"Tienes una nueva solicitud <strong>{codigo}</strong> "
                    f"({tipo}) pendiente de primera aprobación."
                ),
                url=self._url_aprobar(),
                boton="Aprobar solicitudes",
                destinatarios=lideres,
            )

    def notificar_primera_aprobacion(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Primera aprobación",
                titulo="Primera aprobación",
                mensaje=(
                    f"Su líder aprobó la primera aprobación de la solicitud "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Solicitud aprobada",
                titulo="Nueva solicitud aprobada",
                mensaje=(
                    f"La solicitud <strong>{codigo}</strong> fue aprobada en primera "
                    f"instancia y está lista para gestión en el panel."
                ),
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )

    def notificar_segunda_aprobacion(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Segunda aprobación",
                titulo="Segunda aprobación",
                mensaje=(
                    f"Su líder aprobó la segunda aprobación de la solicitud "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Segunda aprobación registrada",
                titulo="Segunda aprobación",
                mensaje=(
                    f"La solicitud <strong>{codigo}</strong> completó la segunda "
                    f"aprobación y puede continuar el trámite de compra."
                ),
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )

    def notificar_rechazo(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Solicitud rechazada",
                titulo="Solicitud rechazada",
                mensaje=(
                    f"El líder aprobador rechazó o canceló la solicitud "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Solicitud rechazada",
                titulo="Solicitud rechazada",
                mensaje=(
                    f"La solicitud <strong>{codigo}</strong> fue rechazada o cancelada "
                    f"en etapa de aprobación."
                ),
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )

    def notificar_cotizacion_enviada(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        lideres = self._emails_lider_catalogo(
            solicitud.lider_segunda_aprobacion_id,
            exclude_user_id=actor.id,
        )

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Cotizaciones enviadas",
                titulo="Seguimiento de solicitud",
                mensaje=(
                    f"Compras adjuntó cotizaciones para la solicitud "
                    f"<strong>{codigo}</strong> y la envió a segunda aprobación."
                ),
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Cotizaciones registradas",
                titulo="Cotizaciones enviadas",
                mensaje=(
                    f"Se registró el envío de cotizaciones de la solicitud "
                    f"<strong>{codigo}</strong> hacia segunda aprobación."
                ),
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )
        if lideres:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Pendiente segunda aprobación",
                titulo="Segunda aprobación pendiente",
                mensaje=(
                    f"Compras adjuntó cotizaciones para la solicitud "
                    f"<strong>{codigo}</strong>. Tiene pendiente su segunda aprobación."
                ),
                url=self._url_aprobar(),
                boton="Aprobar solicitudes",
                destinatarios=lideres,
            )

    def notificar_recotizacion(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        lideres = self._emails_lider_catalogo(
            solicitud.lider_segunda_aprobacion_id,
            exclude_user_id=actor.id,
        )

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Recotización solicitada",
                titulo="Seguimiento de solicitud",
                mensaje=(
                    f"Se solicitó una nueva cotización para la solicitud "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Nueva recotización",
                titulo="Recotización solicitada",
                mensaje=(
                    f"Hay una nueva solicitud de recotización para "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )
        if lideres:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Recotización solicitada",
                titulo="Recotización",
                mensaje=(
                    f"Se solicitó recotización para la solicitud "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_aprobar(),
                boton="Aprobar solicitudes",
                destinatarios=lideres,
            )

    def notificar_tramite_oc(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        oc = (solicitud.numero_tramite_oc or "").strip()
        extra = f" Trámite OC: <strong>{oc}</strong>." if oc else ""

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Trámite OC registrado",
                titulo="Trámite OC",
                mensaje=f"Compras registró el trámite OC de su solicitud <strong>{codigo}</strong>.{extra}",
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Trámite OC registrado",
                titulo="Trámite OC registrado",
                mensaje=f"Se registró trámite OC para la solicitud <strong>{codigo}</strong>.{extra}",
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )

    def notificar_anticipo_aprobado(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        anticipos = self._emails_rol(Role.ANTICIPOS, exclude_user_id=actor.id)

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo aprobado",
                titulo="Anticipo aprobado",
                mensaje=f"El anticipo de la solicitud <strong>{codigo}</strong> fue aprobado.",
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo aprobado",
                titulo="Anticipo aprobado",
                mensaje=f"Anticipo aprobado para la solicitud <strong>{codigo}</strong>.",
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )
        if anticipos:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo para gestionar",
                titulo="Nuevo anticipo",
                mensaje=(
                    f"Hay un anticipo aprobado pendiente de gestión para "
                    f"<strong>{codigo}</strong>."
                ),
                url=self._url_anticipos(),
                boton="Gestión de anticipos",
                destinatarios=anticipos,
            )
        lideres = self._emails_lider_catalogo(
            solicitud.lider_anticipo_id,
            exclude_user_id=actor.id,
        )
        if lideres:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo aprobado",
                titulo="Anticipo aprobado",
                mensaje=f"El anticipo de la solicitud <strong>{codigo}</strong> fue aprobado.",
                url=self._url_aprobar(),
                boton="Ver solicitudes",
                destinatarios=lideres,
            )

    def notificar_anticipo_gestionado(
        self,
        solicitud: SolicitudGestion,
        actor: User,
    ) -> None:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        anticipos = self._emails_rol(Role.ANTICIPOS, exclude_user_id=actor.id)
        lideres = self._emails_lider_catalogo(
            solicitud.lider_anticipo_id,
            exclude_user_id=actor.id,
        )

        if sol:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo gestionado",
                titulo="Anticipo gestionado",
                mensaje=f"El anticipo de la solicitud <strong>{codigo}</strong> fue gestionado.",
                url=self._url_mis_solicitudes(),
                boton="Ver mis solicitudes",
                destinatarios=[sol],
            )
        if compras:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo gestionado",
                titulo="Anticipo gestionado",
                mensaje=f"Gestión de anticipo completada para <strong>{codigo}</strong>.",
                url=self._url_panel(),
                boton="Panel de solicitudes",
                destinatarios=compras,
            )
        if anticipos:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo gestionado",
                titulo="Anticipo gestionado",
                mensaje=f"Se completó la gestión del anticipo de <strong>{codigo}</strong>.",
                url=self._url_anticipos(),
                boton="Gestión de anticipos",
                destinatarios=anticipos,
            )
        if lideres:
            self._enviar_evento(
                solicitud,
                asunto=f"[JURICOM_BEEF] {codigo} — Anticipo gestionado",
                titulo="Anticipo gestionado",
                mensaje=f"El anticipo de <strong>{codigo}</strong> fue gestionado por Anticipos.",
                url=self._url_aprobar(),
                boton="Ver solicitudes",
                destinatarios=lideres,
            )

    def notificar_entrega(
        self,
        solicitud: SolicitudGestion,
        actor: User,
        estado: EstadoSolicitudGestion,
    ) -> bool:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        enviado = False

        if sol:
            enviado = (
                self._send(
                    [sol],
                    f"[JURICOM_BEEF] Solicitud {codigo} — {estado.label}",
                    tpl.render_entrega_solicitud_html(solicitud, estado, actor.username),
                    tpl.render_entrega_solicitud_texto(solicitud, estado, actor.username),
                )
                or enviado
            )
        if compras:
            enviado = (
                self._enviar_evento(
                    solicitud,
                    asunto=f"[JURICOM_BEEF] {codigo} — Entrega registrada",
                    titulo="Entrega registrada",
                    mensaje=(
                        f"Se registró entrega para la solicitud "
                        f"<strong>{codigo}</strong> ({estado.label})."
                    ),
                    url=self._url_panel(),
                    boton="Panel de solicitudes",
                    destinatarios=compras,
                )
                or enviado
            )
        return enviado

    def notificar_entrega_parcial(
        self,
        solicitud: SolicitudGestion,
        actor: User,
        lineas: list[str],
    ) -> bool:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        enviado = False

        if sol:
            enviado = (
                self._send(
                    [sol],
                    f"[JURICOM_BEEF] Solicitud {codigo} — Entrega parcial",
                    tpl.render_entrega_parcial_solicitud_html(
                        solicitud, actor.username, lineas
                    ),
                    tpl.render_entrega_parcial_solicitud_texto(
                        solicitud, actor.username, lineas
                    ),
                )
                or enviado
            )
        if compras:
            enviado = (
                self._enviar_evento(
                    solicitud,
                    asunto=f"[JURICOM_BEEF] {codigo} — Entrega parcial",
                    titulo="Entrega parcial",
                    mensaje=f"Entrega parcial registrada para <strong>{codigo}</strong>.",
                    url=self._url_panel(),
                    boton="Panel de solicitudes",
                    destinatarios=compras,
                )
                or enviado
            )
        return enviado

    def notificar_recepcion_insumos(
        self,
        solicitud: SolicitudGestion,
        actor: User,
        lineas: list[str],
    ) -> bool:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        enviado = False

        if sol:
            enviado = (
                self._send(
                    [sol],
                    f"[JURICOM_BEEF] Solicitud {codigo} — Recepción de insumos",
                    tpl.render_recepcion_insumos_solicitud_html(
                        solicitud, actor.username, lineas
                    ),
                    tpl.render_recepcion_insumos_solicitud_texto(
                        solicitud, actor.username, lineas
                    ),
                )
                or enviado
            )
        if compras:
            enviado = (
                self._enviar_evento(
                    solicitud,
                    asunto=f"[JURICOM_BEEF] {codigo} — Recepción de insumos",
                    titulo="Recepción registrada",
                    mensaje=f"Recepción de insumos registrada para <strong>{codigo}</strong>.",
                    url=self._url_panel(),
                    boton="Panel de solicitudes",
                    destinatarios=compras,
                )
                or enviado
            )
        return enviado

    def notificar_cierre_con_pendientes(
        self,
        solicitud: SolicitudGestion,
        actor: User,
        lineas_pendientes: list[str],
    ) -> bool:
        codigo = solicitud.codigo or ""
        sol = resolver_email_solicitante(solicitud, self._users)
        compras = self._emails_rol(Role.COMPRAS, exclude_user_id=actor.id)
        enviado = False

        if sol:
            texto_extra = "\n\nÍtems pendientes:\n" + "\n".join(
                f"- {l}" for l in lineas_pendientes
            )
            enviado = (
                self._send(
                    [sol],
                    f"[JURICOM_BEEF] Solicitud {codigo} — Cerrada con pendientes",
                    tpl.render_entrega_solicitud_html(
                        solicitud, EstadoSolicitudGestion.ENTREGADO, actor.username
                    ),
                    tpl.render_entrega_solicitud_texto(
                        solicitud, EstadoSolicitudGestion.ENTREGADO, actor.username
                    )
                    + texto_extra,
                )
                or enviado
            )
        if compras:
            enviado = (
                self._enviar_evento(
                    solicitud,
                    asunto=f"[JURICOM_BEEF] {codigo} — Cerrada con pendientes",
                    titulo="Cierre con pendientes",
                    mensaje=(
                        f"La solicitud <strong>{codigo}</strong> se cerró con ítems pendientes."
                    ),
                    url=self._url_panel(),
                    boton="Panel de solicitudes",
                    destinatarios=compras,
                )
                or enviado
            )
        return enviado
