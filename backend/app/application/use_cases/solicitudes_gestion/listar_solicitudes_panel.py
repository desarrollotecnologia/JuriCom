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
    ETAPAS_PANEL_REALIZADAS,
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import (
    TipoSolicitudGestion,
    es_flujo_servicios,
)

VISTA_PANEL_GESTION = "gestion"
VISTA_PANEL_EN_PROCESO = "en_proceso"
VISTA_PANEL_REALIZADAS = "realizadas"


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
        elif vista_norm == VISTA_PANEL_REALIZADAS:
            estados = ETAPAS_PANEL_REALIZADAS
        else:
            estados = ETAPAS_PANEL_GESTION

        items = self._solicitudes.list_all(
            tipo=tipo,
            estados=estados,
            query=query,
        )

        # Comité técnico: mientras Proyectos revisa o programa su propia visita, no
        # debe aparecer en el panel de Compras. La 2.ª visita (visita_proyectos_hecha)
        # sí la agenda Compras, así que esa sí se muestra.
        def _oculto_para_compras(s) -> bool:
            if not (
                es_flujo_servicios(s.tipo)
                and bool(getattr(s, "requiere_comite_tecnico", False))
            ):
                return False
            estado = normalizar_estado(s.estado)
            if estado == EstadoSolicitudGestion.REVISION_PROYECTOS:
                return True
            if estado == EstadoSolicitudGestion.PROGRAMACION_VISITA:
                return not bool(getattr(s, "visita_proyectos_hecha", False))
            return False

        items = [s for s in items if not _oculto_para_compras(s)]

        if vista_norm in (VISTA_PANEL_EN_PROCESO, VISTA_PANEL_REALIZADAS):
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
