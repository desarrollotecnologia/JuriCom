"""Panel del rol Proyectos: SRV con comité técnico en cotización o comité."""

from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import (
    TipoSolicitudGestion,
    es_flujo_servicios,
)

ETAPAS_PANEL_PROYECTOS = [
    EstadoSolicitudGestion.REVISION_PROYECTOS,
    EstadoSolicitudGestion.PROGRAMACION_VISITA,
    EstadoSolicitudGestion.COTIZACION_PROYECTOS,
    EstadoSolicitudGestion.COMITE,
]


class ListarPanelProyectos:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        *,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        if not actor.puede_cotizar_proyectos():
            raise UnauthorizedError("Sólo el rol Proyectos o Admin ven este panel.")

        items = self._solicitudes.list_all(
            tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
            estados=ETAPAS_PANEL_PROYECTOS,
            query=query,
        )
        items = [
            s
            for s in items
            if es_flujo_servicios(s.tipo)
            and bool(getattr(s, "requiere_comite_tecnico", False))
            and normalizar_estado(s.estado) in ETAPAS_PANEL_PROYECTOS
            # La 2.ª visita (tras la cotización de Proyectos) la agenda Compras,
            # así que no debe aparecer en el panel de Proyectos.
            and not (
                normalizar_estado(s.estado) == EstadoSolicitudGestion.PROGRAMACION_VISITA
                and bool(getattr(s, "visita_proyectos_hecha", False))
            )
        ]
        return sorted(items, key=lambda s: -(s.id or 0))
