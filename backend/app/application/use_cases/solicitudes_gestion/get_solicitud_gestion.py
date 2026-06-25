"""Obtiene el detalle de una solicitud de gestión."""

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    ETAPAS_GESTION_ANTICIPO,
    ETAPAS_PENDIENTES_APROBACION_ANTICIPO,
    es_estado_terminal,
    es_pendiente_aprobacion,
    es_visible_en_panel,
    normalizar_estado,
)


class GetSolicitudGestion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")
        if actor.is_compras() and not actor.is_admin() and solicitud.creado_por_id != actor.id:
            estado = normalizar_estado(solicitud.estado)
            if es_visible_en_panel(estado) or es_pendiente_aprobacion(estado):
                return solicitud
            if estado in ETAPAS_GESTION_ANTICIPO or estado in ETAPAS_PENDIENTES_APROBACION_ANTICIPO:
                return solicitud
            if solicitud.gestor_anticipo_id == actor.id:
                return solicitud
            if es_estado_terminal(estado):
                raise UnauthorizedError("No tienes permiso para ver esta solicitud.")
            raise UnauthorizedError("No tienes permiso para ver esta solicitud.")
        return solicitud

    def get_historial(self, actor: User, solicitud_id: int):
        self.execute(actor, solicitud_id)
        return self._solicitudes.get_historial(solicitud_id)
