"""Registra entrega parcial por ítem con cantidades."""

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
from app.application.use_cases.solicitudes_gestion.marcar_entrega_solicitud import (
    _resolver_email_solicitante,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    es_estado_entrega_abierta,
    normalizar_estado,
)

logger = logging.getLogger(__name__)


class RegistrarEntregaParcialSolicitud:
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
        productos_entrega: dict[int, Decimal],
        observacion: str = "",
        observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> tuple[SolicitudGestion, bool, list[str]]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar entregas parciales.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_estado_entrega_abierta(solicitud.estado):
            raise ValueError(
                "Sólo se pueden registrar entregas parciales en Tramitada OC "
                "o Entrega parcial en curso."
            )

        if not solicitud.tiene_tramite_oc_registrado:
            raise ValueError("Debes registrar el trámite OC antes de la entrega.")

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede registrar la entrega.")

        productos_por_id = {
            p.id: p for p in solicitud.productos if p.id is not None
        }
        nuevas_cantidades: dict[int, Decimal] = {}
        lineas: list[str] = []

        for producto_id, cantidad_raw in productos_entrega.items():
            cantidad_a_entregar = Decimal(str(cantidad_raw))
            if cantidad_a_entregar <= 0:
                continue

            producto = productos_por_id.get(int(producto_id))
            if producto is None:
                raise ValueError(f"No existe el ítem #{producto_id} en la solicitud.")

            if producto.estado_aprobacion == EstadoAprobacionProducto.NO_APROBADO:
                raise ValueError(
                    f"El ítem «{producto.descripcion}» no está aprobado y no puede entregarse."
                )

            pendiente = producto.cantidad_pendiente
            if cantidad_a_entregar > pendiente:
                raise ValueError(
                    f"La cantidad a entregar de «{producto.descripcion}» supera lo pendiente "
                    f"({pendiente})."
                )

            total_entregado = producto.cantidad_entregada + cantidad_a_entregar
            nuevas_cantidades[producto.id] = total_entregado
            lineas.append(
                f"{producto.descripcion}: +{cantidad_a_entregar} "
                f"(entregado {total_entregado} de {producto.cantidad})"
            )

        if not nuevas_cantidades:
            raise ValueError(
                "Selecciona al menos un ítem e indica la cantidad a entregar."
            )

        self._solicitudes.update_productos_cantidad_entregada(
            solicitud_id, nuevas_cantidades
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

        solicitud.estado = EstadoSolicitudGestion.ENTREGADO_PARCIAL
        self._solicitudes.update(solicitud)

        comentario = "Entrega parcial — " + "; ".join(lineas)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.ENTREGADO_PARCIAL,
            usuario_id=actor.id,
            comentario=comentario,
        )

        actualizada = self._solicitudes.get_by_id(solicitud_id)
        if actualizada is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")

        email_enviado = self._notificar_solicitante(actualizada, actor, lineas)
        return (actualizada, email_enviado, lineas)

    def _notificar_solicitante(
        self,
        solicitud: SolicitudGestion,
        actor: User,
        lineas: list[str],
    ) -> bool:
        destinatario = _resolver_email_solicitante(solicitud, self._users)
        if not destinatario:
            logger.warning(
                "Sin correo del solicitante para solicitud %s; omito notificación.",
                solicitud.codigo,
            )
            return False
        if not self._notifier.disponible:
            logger.warning("SMTP no disponible; omito notificación de entrega parcial.")
            return False

        from app.infrastructure.email.templates import (
            render_entrega_parcial_solicitud_html,
            render_entrega_parcial_solicitud_texto,
        )

        try:
            self._notifier.send(
                EmailMessage(
                    asunto=(
                        f"[JURICOM_BEEF] Solicitud {solicitud.codigo} — "
                        "Entrega parcial registrada"
                    ),
                    destinatarios=[destinatario],
                    cuerpo_html=render_entrega_parcial_solicitud_html(
                        solicitud, actor.username, lineas
                    ),
                    cuerpo_texto=render_entrega_parcial_solicitud_texto(
                        solicitud, actor.username, lineas
                    ),
                )
            )
            return True
        except Exception:
            logger.exception(
                "Error enviando correo de entrega parcial para solicitud %s",
                solicitud.codigo,
            )
            return False
