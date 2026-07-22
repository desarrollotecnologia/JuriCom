"""Lista solicitudes aprobadas visibles en el panel de gestión."""

from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    ETAPAS_PANEL_EN_PROCESO,
    ETAPAS_PANEL_GESTION,
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

VISTA_PANEL_GESTION = "gestion"
VISTA_PANEL_EN_PROCESO = "en_proceso"


class ListarSolicitudesPanelGestion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        *,
        tipo: Optional[TipoSolicitudGestion] = None,
        query: Optional[str] = None,
        vista: str = VISTA_PANEL_GESTION,
    ) -> list[SolicitudGestion]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden consultar el panel de solicitudes."
            )

        vista_norm = (vista or VISTA_PANEL_GESTION).strip().lower()
        if vista_norm == VISTA_PANEL_EN_PROCESO:
            estados = ETAPAS_PANEL_EN_PROCESO
        else:
            estados = ETAPAS_PANEL_GESTION

        items = self._solicitudes.list_all(
            tipo=tipo,
            estados=estados,
            query=query,
        )

        if vista_norm == VISTA_PANEL_EN_PROCESO:
            return sorted(items, key=lambda s: -(s.id or 0))

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
