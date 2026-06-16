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
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden consultar solicitudes pendientes de aprobación."
            )

        excluir_id = actor.id if actor.is_compras() and not actor.is_admin() else None
        return self._solicitudes.list_all(
            tipo=TipoSolicitudGestion.COMPRA,
            estados=ETAPAS_PENDIENTES_APROBACION,
            excluir_creador_id=excluir_id,
        )
