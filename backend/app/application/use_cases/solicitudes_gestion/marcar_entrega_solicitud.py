"""Marca una solicitud como entregada (cierre del flujo) y notifica al solicitante."""

import logging
from decimal import Decimal

from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.interfaces.user_repository import UserRepository
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    es_estado_entrega_abierta,
)

logger = logging.getLogger(__name__)


def _resolver_email_solicitante(
    solicitud: SolicitudGestion,
    users: UserRepository,
) -> str:
    if (solicitud.creado_por_email or "").strip():
        return solicitud.creado_por_email.strip()

    user = users.get_by_id(solicitud.creado_por_id)
    if user and (user.email or "").strip():
        return user.email.strip()
    return ""


class MarcarEntregaSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        users: UserRepository,
        notifier: EmailNotifier,
        storage: FileStorage,
    ) -> None:
        self._solicitudes = solicitudes
        self._users = users
        self._notifier = notifier
        self._storage = storage

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> tuple[SolicitudGestion, bool]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar la entrega.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_estado_entrega_abierta(solicitud.estado):
            raise ValueError(
                "La solicitud debe estar en Tramitada OC o Entrega parcial en curso."
            )

        if not solicitud.tiene_tramite_oc_registrado:
            raise ValueError(
                "Debes registrar el trámite OC antes de marcar la entrega."
            )

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede registrar la entrega.")

        if solicitud.tiene_entrega_pendiente:
            pendientes = [
                f"«{p.descripcion}» (pendiente {p.cantidad_pendiente})"
                for p in solicitud.productos_para_entrega
                if p.cantidad_pendiente > 0
            ]
            raise ValueError(
                "Aún hay ítems pendientes de entrega. Registra las entregas parciales "
                "o completa las cantidades antes de cerrar. Pendientes: "
                + ", ".join(pendientes)
            )

        cantidades_finales: dict[int, Decimal] = {}
        for producto in solicitud.productos_para_entrega:
            if producto.id is None:
                continue
            cantidades_finales[producto.id] = producto.cantidad

        if cantidades_finales:
            self._solicitudes.update_productos_cantidad_entregada(
                solicitud_id, cantidades_finales
            )

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or adjuntos_obs:
            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="gestor",
                archivos=adjuntos_obs,
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")

        solicitud.estado = EstadoSolicitudGestion.ENTREGADO
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.ENTREGADO,
            usuario_id=actor.id,
            comentario=f"Entrega total registrada por {actor.username}",
        )

        email_enviado = self._notificar_solicitante(
            actualizada, EstadoSolicitudGestion.ENTREGADO, actor
        )

        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return (refreshed or actualizada, email_enviado)

    def _notificar_solicitante(
        self,
        solicitud: SolicitudGestion,
        estado: EstadoSolicitudGestion,
        actor: User,
    ) -> bool:
        destinatario = _resolver_email_solicitante(solicitud, self._users)
        if not destinatario:
            logger.warning(
                "Sin correo del solicitante para solicitud %s; omito notificación.",
                solicitud.codigo,
            )
            return False
        if not self._notifier.disponible:
            logger.warning("SMTP no disponible; omito notificación de entrega.")
            return False

        from app.infrastructure.email.templates import (
            render_entrega_solicitud_html,
            render_entrega_solicitud_texto,
        )

        try:
            self._notifier.send(
                EmailMessage(
                    asunto=(
                        f"[JURICOM_BEEF] Solicitud {solicitud.codigo} — "
                        f"{estado.label}"
                    ),
                    destinatarios=[destinatario],
                    cuerpo_html=render_entrega_solicitud_html(
                        solicitud, estado, actor.username
                    ),
                    cuerpo_texto=render_entrega_solicitud_texto(
                        solicitud, estado, actor.username
                    ),
                )
            )
            return True
        except Exception:
            logger.exception(
                "Error enviando correo de entrega para solicitud %s",
                solicitud.codigo,
            )
            return False
