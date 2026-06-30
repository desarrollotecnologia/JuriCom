"""Lista solicitudes aprobadas visibles en el panel de gestión."""

from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    ETAPAS_PANEL_GESTION,
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class ListarSolicitudesPanelGestion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        *,
        tipo: Optional[TipoSolicitudGestion] = None,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden consultar el panel de solicitudes."
            )

        items = self._solicitudes.list_all(
            tipo=tipo,
            estados=ETAPAS_PANEL_GESTION,
            query=query,
        )
        return sorted(
            items,
            key=lambda s: (
                1
                if (
                    s.factura_registrada_at
                    or normalizar_estado(s.estado) == EstadoSolicitudGestion.FACTURADA
                )
                else 0,
                s.factura_registrada_at.timestamp()
                if s.factura_registrada_at
                else 0,
                -(s.id or 0),
            ),
        )
