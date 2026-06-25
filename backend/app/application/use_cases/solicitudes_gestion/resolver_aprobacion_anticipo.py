"""Aprueba o rechaza un anticipo pendiente de aprobación por líder."""

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.application.use_cases.solicitudes_gestion.avanzar_flujo_post_oc import (
    avanzar_a_items_en_camino,
)
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


class ResolverAprobacionAnticipo:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def aprobar(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
    ) -> SolicitudGestion:
        solicitud = self._get_pendiente(actor, solicitud_id)
        nota = (observacion_texto or observacion or "").strip()
        if nota:
            from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
                AgregarObservacionSolicitud,
            )

            AgregarObservacionSolicitud(self._solicitudes).execute(
                actor,
                solicitud_id,
                contenido=observacion or f"<p>{nota}</p>",
                contenido_texto=nota,
                contexto_rol="aprobador_anticipo",
            )

        solicitud.estado = EstadoSolicitudGestion.GESTION_ANTICIPO
        solicitud.gestor_anticipo_id = actor.id
        actualizada = self._solicitudes.update(solicitud)
        pct = solicitud.porcentaje_anticipo
        monto = solicitud.monto_anticipo
        detalle = f"Anticipo aprobado — {pct}%"
        if monto is not None:
            detalle += f" (monto: {monto:,.2f})"
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.GESTION_ANTICIPO,
            usuario_id=actor.id,
            comentario=detalle,
        )
        return self._solicitudes.get_by_id(solicitud_id) or actualizada

    def rechazar(
        self,
        actor: User,
        solicitud_id: int,
        motivo: str = "",
    ) -> SolicitudGestion:
        solicitud = self._get_pendiente(actor, solicitud_id)
        motivo = (motivo or "").strip()
        if motivo:
            from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
                AgregarObservacionSolicitud,
            )

            AgregarObservacionSolicitud(self._solicitudes).execute(
                actor,
                solicitud_id,
                contenido=f"<p><strong>Anticipo rechazado:</strong> {motivo}</p>",
                contenido_texto=f"Anticipo rechazado: {motivo}",
                contexto_rol="aprobador_anticipo",
            )

        solicitud.estado = EstadoSolicitudGestion.TRAMITADA_OC
        solicitud.requiere_anticipo = False
        actualizada = self._solicitudes.update(solicitud)
        motivo_hist = motivo or "Anticipo rechazado — continúa sin anticipo"
        refreshed = avanzar_a_items_en_camino(
            self._solicitudes,
            solicitud_id,
            actor.id,
            comentario_tramitada=motivo_hist,
        )
        return refreshed or actualizada

    def _get_pendiente(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden aprobar anticipos.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.APROBACION_ANTICIPO:
            raise ValueError("Esta solicitud no está pendiente de aprobación de anticipo.")

        if not solicitud.requiere_anticipo:
            raise ValueError("Esta solicitud no tiene anticipo registrado.")

        if actor.is_compras() and not actor.is_admin() and solicitud.creado_por_id == actor.id:
            raise UnauthorizedError("No puedes aprobar el anticipo de tu propia solicitud.")

        return solicitud
