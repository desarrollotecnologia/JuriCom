"""Registra la recepción física de ítems y avanza a Recepción de Insumos."""

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
    es_estado_recepcion_abierta,
    normalizar_estado,
)

logger = logging.getLogger(__name__)


class RegistrarRecepcionInsumosSolicitud:
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
        productos_recepcion: dict[int, Decimal],
        observacion: str = "",
        observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> tuple[SolicitudGestion, bool, list[str]]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar recepciones.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_estado_recepcion_abierta(solicitud.estado):
            raise ValueError(
                "Sólo se puede registrar recepción en Ítems en camino, "
                "Recepción de Insumos o Entrega parcial realizada."
            )

        if not solicitud.tiene_tramite_oc_registrado:
            raise ValueError("Debes registrar el trámite OC antes de la recepción.")

        if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
            raise UnauthorizedError("Sólo el gestor asignado puede registrar la recepción.")

        productos_por_id = {
            p.id: p for p in solicitud.productos if p.id is not None
        }
        nuevas_cantidades: dict[int, Decimal] = {}
        lineas: list[str] = []

        for producto_id, cantidad_raw in productos_recepcion.items():
            cantidad_a_recibir = Decimal(str(cantidad_raw))
            if cantidad_a_recibir <= 0:
                continue

            producto = productos_por_id.get(int(producto_id))
            if producto is None:
                raise ValueError(f"No existe el ítem {producto_id} en esta solicitud.")

            if producto.estado_aprobacion == EstadoAprobacionProducto.NO_APROBADO:
                raise ValueError(
                    f"El ítem «{producto.descripcion}» no está aprobado y no puede recibirse."
                )

            pendiente = producto.cantidad_pendiente_recepcion
            if cantidad_a_recibir > pendiente:
                raise ValueError(
                    f"La cantidad recibida de «{producto.descripcion}» supera lo pendiente "
                    f"({pendiente})."
                )

            total_recibido = producto.cantidad_recibida + cantidad_a_recibir
            nuevas_cantidades[producto.id] = total_recibido
            lineas.append(
                producto.linea_historial_recepcion(cantidad_a_recibir, total_recibido)
            )

        if not nuevas_cantidades:
            raise ValueError(
                "Selecciona al menos un ítem e indica la cantidad recibida."
            )

        self._solicitudes.update_productos_cantidad_recibida(
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

        estado_actual = normalizar_estado(solicitud.estado)
        if estado_actual != EstadoSolicitudGestion.RECEPCION_INSUMOS:
            solicitud.estado = EstadoSolicitudGestion.RECEPCION_INSUMOS
            self._solicitudes.update(solicitud)
            comentario = "Recepción de insumos — " + "; ".join(lineas)
            self._solicitudes.registrar_historial(
                solicitud_id,
                EstadoSolicitudGestion.RECEPCION_INSUMOS,
                usuario_id=actor.id,
                comentario=comentario,
            )
        else:
            comentario = "Recepción adicional — " + "; ".join(lineas)
            self._solicitudes.registrar_historial(
                solicitud_id,
                EstadoSolicitudGestion.RECEPCION_INSUMOS,
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
            logger.warning("SMTP no disponible; omito notificación de recepción.")
            return False

        from app.infrastructure.email.templates import (
            render_recepcion_insumos_solicitud_html,
            render_recepcion_insumos_solicitud_texto,
        )

        try:
            self._notifier.send(
                EmailMessage(
                    asunto=(
                        f"[JURICOM_BEEF] Solicitud {solicitud.codigo} — "
                        "Insumos disponibles para reclamar"
                    ),
                    destinatarios=[destinatario],
                    cuerpo_html=render_recepcion_insumos_solicitud_html(
                        solicitud, actor.username, lineas
                    ),
                    cuerpo_texto=render_recepcion_insumos_solicitud_texto(
                        solicitud, actor.username, lineas
                    ),
                )
            )
            return True
        except Exception:
            logger.exception(
                "Error enviando correo de recepción para solicitud %s",
                solicitud.codigo,
            )
            return False
