"""Cierra la solicitud como entregada dejando cantidades pendientes por entregar."""

import logging

from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.interfaces.user_repository import UserRepository
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.marcar_entrega_solicitud import (
    _resolver_email_solicitante,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion, SolicitudGestionProducto
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    es_estado_entrega_abierta,
)

logger = logging.getLogger(__name__)


def _lineas_pendientes_entrega(productos: list[SolicitudGestionProducto]) -> list[str]:
    lineas: list[str] = []
    for producto in productos:
        pendiente = producto.cantidad - producto.cantidad_entregada
        if pendiente <= 0:
            continue
        lineas.append(
            f"«{producto.descripcion}»: entregado {producto.cantidad_entregada} de "
            f"{producto.cantidad} (pendiente {pendiente})"
        )
    return lineas


class CerrarSolicitudConPendientes:
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
            raise UnauthorizedError("Sólo Compras o Admin pueden cerrar solicitudes.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_estado_entrega_abierta(solicitud.estado):
            raise ValueError(
                "Sólo se puede cerrar con pendientes en Recepción de Insumos "
                "o Entrega parcial realizada."
            )

        if not solicitud.es_salidas_almacen and not solicitud.tiene_tramite_oc_registrado:
            raise ValueError("Debes registrar el trámite OC antes de cerrar la solicitud.")

        if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
            raise UnauthorizedError("Sólo el gestor asignado puede cerrar la solicitud.")

        productos = solicitud.productos_para_entrega
        if not productos:
            raise ValueError("No hay ítems aprobados en la solicitud.")

        if not any(p.cantidad_entregada > 0 for p in productos):
            raise ValueError(
                "Debes registrar al menos una entrega parcial antes de cerrar con pendientes."
            )

        lineas_pendientes = _lineas_pendientes_entrega(productos)
        if not lineas_pendientes:
            raise ValueError(
                "No hay cantidades pendientes por entregar; usa Entrega total para cerrar."
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
        comentario = (
            "Cierre con ítems pendientes por entregar — "
            + "; ".join(_lineas_pendientes_entrega(solicitud.productos_para_entrega))
        )
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.ENTREGADO,
            usuario_id=actor.id,
            comentario=comentario,
        )

        email_enviado = self._notificar_solicitante(actualizada, actor, lineas_pendientes)
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return (refreshed or actualizada, email_enviado)

    def _notificar_solicitante(
        self,
        solicitud: SolicitudGestion,
        actor: User,
        lineas_pendientes: list[str],
    ) -> bool:
        destinatario = _resolver_email_solicitante(solicitud, self._users)
        if not destinatario:
            logger.warning(
                "Sin correo del solicitante para solicitud %s; omito notificación.",
                solicitud.codigo,
            )
            return False
        if not self._notifier.disponible:
            logger.warning("SMTP no disponible; omito notificación de cierre con pendientes.")
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
                        "Cerrada con ítems pendientes"
                    ),
                    destinatarios=[destinatario],
                    cuerpo_html=render_entrega_solicitud_html(
                        solicitud, EstadoSolicitudGestion.ENTREGADO, actor.username
                    ),
                    cuerpo_texto=(
                        render_entrega_solicitud_texto(
                            solicitud, EstadoSolicitudGestion.ENTREGADO, actor.username
                        )
                        + "\n\nÍtems que quedaron pendientes:\n"
                        + "\n".join(f"- {linea}" for linea in lineas_pendientes)
                    ),
                )
            )
            return True
        except Exception:
            logger.exception(
                "Error enviando correo de cierre con pendientes para solicitud %s",
                solicitud.codigo,
            )
            return False
