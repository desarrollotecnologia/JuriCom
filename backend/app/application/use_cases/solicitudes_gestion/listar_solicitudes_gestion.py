"""Lista solicitudes del módulo Gestión de Solicitudes."""

from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class ListarSolicitudesGestion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        *,
        tipo: Optional[TipoSolicitudGestion] = None,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        creador_id: Optional[int] = None
        if actor.is_compras():
            creador_id = actor.id
        return self._solicitudes.list_all(
            creador_id=creador_id,
            tipo=tipo,
            query=query,
        )
