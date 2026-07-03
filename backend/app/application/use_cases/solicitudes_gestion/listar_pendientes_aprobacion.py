"""Lista solicitudes de compra pendientes de aprobación."""

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import ETAPAS_PENDIENTES_APROBACION
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class ListarPendientesAprobacion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(self, actor: User) -> list[SolicitudGestion]:
        if not actor.puede_aprobar_solicitudes_gestion():
            raise UnauthorizedError(
                "No tienes permiso para consultar solicitudes pendientes de aprobación."
            )

        excluir_id = None
        items: list[SolicitudGestion] = []
        for tipo in (
            TipoSolicitudGestion.COMPRA,
            TipoSolicitudGestion.SALIDAS_ALMACEN,
        ):
            items.extend(
                self._solicitudes.list_all(
                    tipo=tipo,
                    estados=ETAPAS_PENDIENTES_APROBACION,
                    excluir_creador_id=excluir_id,
                )
            )

        if actor.is_lider_aprobador() and not actor.is_admin():
            items = [s for s in items if actor.solicitud_asignada_a_lider(s)]

        items.sort(key=lambda s: s.id or 0, reverse=True)
        return items
