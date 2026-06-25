"""Lista solicitudes en gestión de anticipo (módulo Gestionar anticipo)."""

from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import ETAPAS_GESTION_ANTICIPO
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class ListarGestionAnticipo:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        *,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden gestionar anticipos.")

        if actor.is_admin():
            return self._solicitudes.list_all(
                tipo=TipoSolicitudGestion.COMPRA,
                estados=ETAPAS_GESTION_ANTICIPO,
                query=query,
            )

        return self._solicitudes.list_all(
            tipo=TipoSolicitudGestion.COMPRA,
            estados=ETAPAS_GESTION_ANTICIPO,
            gestor_anticipo_id=actor.id,
            query=query,
        )
