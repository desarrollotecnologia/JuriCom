"""Cierra una solicitud de servicios tras revisar la evidencia del solicitante."""

from datetime import datetime

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
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
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios


def _fecha_notificacion_evidencia(
    historial: list,
) -> datetime | None:
    fechas: list[datetime] = []
    for entrada in historial:
        if normalizar_estado(entrada.etapa) != EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE:
            continue
        if entrada.created_at:
            fechas.append(entrada.created_at)
    if not fechas:
        return None
    return max(fechas)


def _tiene_evidencia_solicitante_post_notificacion(solicitud: SolicitudGestion) -> bool:
    historial = solicitud.historial_estados or []
    if not historial:
        historial = []
    fecha_corte = _fecha_notificacion_evidencia(historial)
    if fecha_corte is None:
        return False
    for obs in solicitud.observaciones_trazabilidad or []:
        rol = (obs.autor_rol or "").lower()
        if "solicitante" not in rol:
            continue
        if obs.created_at is None:
            continue
        if obs.created_at >= fecha_corte:
            return True
    return False


class CerrarServicioSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage,
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage
        self._notificador = notificador

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
            raise UnauthorizedError("Sólo Compras o Admin pueden cerrar servicios.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_flujo_servicios(solicitud.tipo):
            raise ValueError("Esta acción solo aplica a solicitudes de servicios.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE:
            raise ValueError(
                "La solicitud debe estar pendiente de evidencia de cierre del solicitante."
            )

        if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
            raise UnauthorizedError("Sólo el gestor asignado puede cerrar este servicio.")

        solicitud.historial_estados = self._solicitudes.get_historial(solicitud_id)
        if not _tiene_evidencia_solicitante_post_notificacion(solicitud):
            raise ValueError(
                "El solicitante aún no ha registrado evidencia u observación de cierre. "
                "Espera su respuesta en Mis solicitudes."
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

        solicitud.estado = EstadoSolicitudGestion.ENTREGADO
        actualizada = self._solicitudes.update(solicitud)
        comentario = f"Servicio cerrado por {actor.username}"
        if nota_texto:
            comentario = f"{comentario} — {nota_texto[:400]}"
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.ENTREGADO,
            usuario_id=actor.id,
            comentario=comentario,
        )

        email_enviado = False
        if self._notificador:
            email_enviado = self._notificador.notificar_entrega(
                actualizada, actor, EstadoSolicitudGestion.ENTREGADO
            )

        refreshed = self._solicitudes.get_by_id(solicitud_id) or actualizada
        return refreshed, email_enviado
