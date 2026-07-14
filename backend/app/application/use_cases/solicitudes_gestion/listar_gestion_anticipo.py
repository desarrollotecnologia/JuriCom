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
        if not actor.puede_operar_anticipos():
            raise UnauthorizedError("Sólo Anticipos o Admin pueden gestionar anticipos.")

        tipos = (TipoSolicitudGestion.COMPRA, TipoSolicitudGestion.INSUMOS_SERVICIOS)
        items: list[SolicitudGestion] = []
        for tipo in tipos:
            if actor.is_admin() or actor.is_anticipos():
                items.extend(
                    self._solicitudes.list_all(
                        tipo=tipo,
                        estados=ETAPAS_GESTION_ANTICIPO,
                        query=query,
                    )
                )
            else:
                items.extend(
                    self._solicitudes.list_all(
                        tipo=tipo,
                        estados=ETAPAS_GESTION_ANTICIPO,
                        gestor_anticipo_id=actor.id,
                        query=query,
                    )
                )
        return items
