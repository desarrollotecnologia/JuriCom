"""Toma una solicitud en el panel y avanza a cotización."""

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


class GestionarSolicitudPanel:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden gestionar solicitudes.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        estado = normalizar_estado(solicitud.estado)
        if estado == EstadoSolicitudGestion.COTIZACION:
            if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado != EstadoSolicitudGestion.PRIMERA_APROBACION:
            raise ValueError(
                "Sólo se pueden gestionar solicitudes en Primera Aprobación o Cotización."
            )

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Esta solicitud ya fue tomada por otro gestor.")

        solicitud.gestor_id = actor.id
        solicitud.estado = EstadoSolicitudGestion.COTIZACION
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.COTIZACION,
            usuario_id=actor.id,
            comentario=f"Gestión iniciada por {actor.username}",
        )
        return actualizada
