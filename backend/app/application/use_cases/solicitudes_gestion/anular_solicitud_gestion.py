"""Compras da por anulada (cancelada) una solicitud antes de registrar la OC."""

from html import escape

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    ETAPAS_ANULABLES_COMPRAS,
    EstadoSolicitudGestion,
    normalizar_estado,
)


class AnularSolicitudGestion:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._notificador = notificador

    def execute(self, actor: User, solicitud_id: int, motivo: str) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden anular solicitudes.")
        motivo = (motivo or "").strip()
        if not motivo:
            raise ValueError("Escribe el motivo de la anulación.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        estado = normalizar_estado(solicitud.estado)
        admin_sin_gestor = actor.is_admin() and estado == EstadoSolicitudGestion.PRIMERA_APROBACION
        if estado not in ETAPAS_ANULABLES_COMPRAS and not admin_sin_gestor:
            raise ValueError(
                "Sólo se puede anular antes de registrar la orden de compra "
                "(En gestión, Programar visita o Cotización)."
            )
        if not actor.is_admin() and solicitud.gestor_id != actor.id:
            raise UnauthorizedError("Sólo el gestor asignado o un Admin puede anular la solicitud.")

        AgregarObservacionSolicitud(self._solicitudes).execute(
            actor,
            solicitud_id,
            contenido=f"<p><strong>Anulada por Compras:</strong> {escape(motivo)}</p>",
            contenido_texto=f"Anulada por Compras: {motivo}",
            contexto_rol="gestor",
        )
        solicitud.estado = EstadoSolicitudGestion.CANCELADO
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.CANCELADO,
            usuario_id=actor.id,
            comentario=f"Anulada por Compras ({actor.username}): {motivo}",
        )
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador:
            self._notificador.notificar_anulacion(resultado, actor, motivo)
        return resultado
